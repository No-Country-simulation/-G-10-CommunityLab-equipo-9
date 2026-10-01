package com.insightedulab.backend_java.controller;

import com.insightedulab.backend_java.dto.*;
import com.insightedulab.backend_java.model.PackageResult;
import com.insightedulab.backend_java.service.CommunityService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;

@RestController
@RequestMapping("/api/v1/community")
public class CommunityController {
    private final CommunityService communityService;
    public CommunityController(CommunityService communityService) {
        this.communityService = communityService;
    }

    /**
     * Endpoint oficial para recibir y validar el lote de mensajes de Discord.
     */
    @PostMapping("/process")
    public ResponseEntity<CommunityProcessResponseDto> processBatch(@RequestBody CommunityProcessRequestDto request) {
        // 1. Validación de entrada
        if (request == null || request.getInteracciones() == null || request.getInteracciones().isEmpty()) {
            CommunityProcessResponseDto errorResponse = CommunityProcessResponseDto.builder()
                    .status("error")
                    .mensaje("El lote recibido no contiene interacciones válidas para procesar")
                    .loteId(request != null ? request.getLoteId() : null)
                    .totalMensajesRecibidos(0)
                    .build();
            return ResponseEntity.badRequest().body(errorResponse);
        }

        int total = request.getInteracciones().size();

        communityService.processBatch(request);

        // 2. Respuesta formal tipada para Discord
        CommunityProcessResponseDto response = CommunityProcessResponseDto.builder()
                .status("exitoso")
                .mensaje("Lote recibido y validado correctamente")
                .loteId(request.getLoteId())
                .totalMensajesRecibidos(total)
                .recibidoEn(Instant.now())
                .build();

        return ResponseEntity.ok(response);
    }

    @PutMapping("/curation/{id}")
    public ResponseEntity<PackageResultResponseDto> updateCuration(
            @PathVariable Long id,
            @RequestBody CurationRequestDto dto) {
        PackageResult updated = communityService.updateCuration(id, dto);

        // Mapeamos la entidad actualizada a su respectivo DTO de respuesta
        PackageResultResponseDto responseDto = mapToPackageResultResponseDto(updated);
        return ResponseEntity.ok(responseDto);
    }

    @PostMapping({"/upload-report/{packageId}", "/oci/upload-report/{packageId}"})
    public ResponseEntity<OciUploadResponseDto> uploadReport(@PathVariable Long packageId) {
        OciUploadResponseDto response = communityService.uploadReportToOci(packageId);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/packages")
    public ResponseEntity<List<PackageResultResponseDto>> getAllPackages() {
        List<PackageResult> packages = communityService.getAllPackages();

        // Mapeamos la lista de entidades a una lista de DTOs
        List<PackageResultResponseDto> responseDtos = packages.stream()
                .map(this::mapToPackageResultResponseDto)
                .toList();

        return ResponseEntity.ok(responseDtos);
    }

    @GetMapping("/packages/{id}")
    public ResponseEntity<PackageResultResponseDto> getPackageById(@PathVariable Long id) {
        PackageResult pkg = communityService.getPackageById(id);

        // Mapeamos la entidad individual a su DTO de respuesta
        PackageResultResponseDto responseDto = mapToPackageResultResponseDto(pkg);
        return ResponseEntity.ok(responseDto);
    }

    /**
     * Método auxiliar de mapeo de Entidad a DTO (Puedes moverlo a un Mapper dedicado si prefieres)
     */
    private PackageResultResponseDto mapToPackageResultResponseDto(PackageResult pkg) {
        if (pkg == null) {
            return null;
        }

        List<InteractionResponseDto> interactionDtos = null;
        if (pkg.getInteracciones() != null) {
            interactionDtos = pkg.getInteracciones().stream()
                    .map(i -> InteractionResponseDto.builder()
                            .id(i.getId())
                            .discordId(i.getDiscordId())
                            .channelId(i.getChannelId())
                            .authorId(i.getAuthorId())
                            .authorUsername(i.getAuthorUsername())
                            .autorNombre(i.getAutorNombre())
                            .autorRol(i.getAutorRol())
                            .textoMensaje(i.getTextoMensaje())
                            .tipoAutor(i.getTipoAutor())
                            .clasificacionSentimiento(i.getClasificacionSentimiento())
                            .timestampMensaje(i.getTimestampMensaje())
                            .build())
                    .toList();
        }

        return PackageResultResponseDto.builder()
                .id(pkg.getId())
                .logId(pkg.getLogId())
                .loteId(pkg.getLoteId())
                .tipoServidor(pkg.getTipoServidor())
                .interacciones(interactionDtos)
                .tipoAutorRespuesta(pkg.getTipoAutorRespuesta())
                .clasificacionSentimiento(pkg.getClasificacionSentimiento())
                .respuestaAi(pkg.getRespuestaAi())
                .postLinkedin(pkg.getPostLinkedin())
                .temaFaq(pkg.getTemaFaq())
                .preguntaFaq(pkg.getPreguntaFaq())
                .respuestaFaq(pkg.getRespuestaFaq())
                .tokensIn(pkg.getTokensIn())
                .tokensOut(pkg.getTokensOut())
                .similitudPromedio(pkg.getSimilitudPromedio())
                .fueEditadoPorHumano(pkg.getFueEditadoPorHumano())
                .tiempoCuraduriaSeg(pkg.getTiempoCuraduriaSeg())
                .timestampInicio(pkg.getTimestampInicio())
                .timestampFin(pkg.getTimestampFin())
                .statusOci(pkg.getStatusOci())
                .build();
    }
}