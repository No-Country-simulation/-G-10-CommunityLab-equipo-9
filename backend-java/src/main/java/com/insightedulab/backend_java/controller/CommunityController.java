package com.insightedulab.backend_java.controller;

import com.insightedulab.backend_java.dto.CommunityProcessRequestDto;
import com.insightedulab.backend_java.dto.CommunityProcessResponseDto;
import com.insightedulab.backend_java.dto.CurationRequestDto;
import com.insightedulab.backend_java.dto.OciUploadResponseDto;
import com.insightedulab.backend_java.model.PackageResult;
import com.insightedulab.backend_java.service.CommunityService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;

@RestController
@RequestMapping("/api/v1/community")
@CrossOrigin(origins = "*")
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

        
        PackageResult pkg = communityService.processBatch(request);


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
    public ResponseEntity<PackageResult> updateCuration(
            @PathVariable Long id,
            @RequestBody CurationRequestDto dto) {
        PackageResult updated = communityService.updateCuration(id, dto);
        return ResponseEntity.ok(updated);
    }
    @PostMapping({"/upload-report/{packageId}", "/oci/upload-report/{packageId}"})
    public ResponseEntity<OciUploadResponseDto> uploadReport(@PathVariable Long packageId) {
        OciUploadResponseDto response = communityService.uploadReportToOci(packageId);
        return ResponseEntity.ok(response);
    }
    @GetMapping("/packages")
    public ResponseEntity<List<PackageResult>> getAllPackages() {
        return ResponseEntity.ok(communityService.getAllPackages());
    }
    @GetMapping("/packages/{id}")
    public ResponseEntity<PackageResult> getPackageById(@PathVariable Long id) {
        return ResponseEntity.ok(communityService.getPackageById(id));
    }  
    
}


