package com.insightedulab.backend_java.service;

import com.insightedulab.backend_java.dto.CommunityProcessRequestDto;
import com.insightedulab.backend_java.dto.CurationRequestDto;
import com.insightedulab.backend_java.dto.InteractionInputDto;
import com.insightedulab.backend_java.dto.OciUploadResponseDto;
import com.insightedulab.backend_java.model.Interaction;
import com.insightedulab.backend_java.model.PackageResult;
import com.insightedulab.backend_java.model.enums.TipoAutor;
import com.insightedulab.backend_java.repository.InteractionRepository;
import com.insightedulab.backend_java.repository.PackageResultRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class CommunityService {

    private final PackageResultRepository packageResultRepository;
    private final InteractionRepository interactionRepository;
    private final RestTemplate restTemplate;

    @Value("${OCI_PAR_URL}")
    private String parUrlBase;

    public CommunityService(PackageResultRepository packageResultRepository,
                            InteractionRepository interactionRepository) {
        this.packageResultRepository = packageResultRepository;
        this.interactionRepository = interactionRepository;
        org.springframework.http.client.SimpleClientHttpRequestFactory factory = new org.springframework.http.client.SimpleClientHttpRequestFactory();
        this.restTemplate = new RestTemplate(factory);
    }

    @Transactional
    public PackageResult processBatch(CommunityProcessRequestDto request) {
        PackageResult pkg = PackageResult.builder()
                .loteId(request.getLoteId())
                .tipoServidor(request.getTipoServidor())
                .tipoAutorRespuesta(TipoAutor.AI)
                .fueEditadoPorHumano(false)
                .tiempoCuraduriaSeg(0)
                .timestampInicio(Instant.now())
                .timestampFin(Instant.now())
                .statusOci("PENDIENTE")
                .interacciones(new ArrayList<>())
                .build();

        PackageResult savedPkg = packageResultRepository.save(pkg);

        if (request.getInteracciones() != null) {
            for (InteractionInputDto dto : request.getInteracciones()) {
                Interaction interaction = Interaction.builder()
                        .packageResult(savedPkg)
                        .loteId(request.getLoteId())
                        .tipoServidor(request.getTipoServidor())
                        .discordId(dto.getDiscordId())
                        .channelId(dto.getChannelId())
                        .authorId(dto.getAuthorId())
                        .authorUsername(dto.getAuthorUsername())
                        .authorNombre(dto.getAutorNombre())
                        .authorRol(dto.getAutorRol())
                        .textoMensaje(dto.getTextoMensaje())
                        .tipoAutor(dto.getTipoAutor())
                        .clasificacionSentimiento(dto.getClasificacionSentimiento())
                        .timestampMensaje(dto.getTimestampMensaje() != null ? dto.getTimestampMensaje() : Instant.now())
                        .build();

                savedPkg.getInteracciones().add(interaction);
            }
            packageResultRepository.save(savedPkg);
        }

        return savedPkg;
    }

    @Transactional
    public PackageResult updateCuration(Long id, CurationRequestDto dto) {
        PackageResult pkg = packageResultRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("PackageResult no encontrado con id: " + id));

        if (dto.getPostLinkedin() != null) pkg.setPostLinkedin(dto.getPostLinkedin());
        if (dto.getTemaFaq() != null) pkg.setTemaFaq(dto.getTemaFaq());
        if (dto.getPreguntaFaq() != null) pkg.setPreguntaFaq(dto.getPreguntaFaq());
        if (dto.getRespuestaFaq() != null) pkg.setRespuestaFaq(dto.getRespuestaFaq());
        if (dto.getTipoAutorRespuesta() != null) pkg.setTipoAutorRespuesta(dto.getTipoAutorRespuesta());
        if (dto.getFueEditadoPorHumano() != null) pkg.setFueEditadoPorHumano(dto.getFueEditadoPorHumano());
        if (dto.getTiempoCuraduriaSeg() != null) pkg.setTiempoCuraduriaSeg(dto.getTiempoCuraduriaSeg());

        return packageResultRepository.save(pkg);
    }

    public OciUploadResponseDto uploadReportToOci(Long packageId) {
        PackageResult pkg = packageResultRepository.findById(packageId)
                .orElseThrow(() -> new RuntimeException("Paquete no encontrado id: " + packageId));

        String targetUrl = parUrlBase + "package_" + packageId + ".json";

        String jsonPayload = String.format(
                "{\"id\":%d,\"loteId\":\"%s\",\"tipoServidor\":\"%s\",\"postLinkedin\":%s,\"preguntaFaq\":%s,\"respuestaFaq\":%s,\"fueEditadoPorHumano\":%b,\"timestampFin\":%s,\"almacenamiento_oci\":{\"bucket\":\"dato\",\"ruta_objeto\":\"package_%d.json\",\"status\":\"guardado_con_exito\"}}",
                pkg.getId(),
                pkg.getLoteId() != null ? pkg.getLoteId() : "",
                pkg.getTipoServidor() != null ? pkg.getTipoServidor() : "",
                pkg.getPostLinkedin() != null ? "\"" + pkg.getPostLinkedin() + "\"" : "null",
                pkg.getPreguntaFaq() != null ? "\"" + pkg.getPreguntaFaq() + "\"" : "null",
                pkg.getRespuestaFaq() != null ? "\"" + pkg.getRespuestaFaq() + "\"" : "null",
                pkg.getFueEditadoPorHumano() != null ? pkg.getFueEditadoPorHumano() : false,
                pkg.getTimestampFin() != null ? "\"" + pkg.getTimestampFin().toString() + "\"" : "null",
                packageId
        );

        try {
            byte[] rawData = jsonPayload.getBytes(java.nio.charset.StandardCharsets.UTF_8);
            java.net.URL url = new java.net.URI(targetUrl).toURL();
            java.net.HttpURLConnection conn = (java.net.HttpURLConnection) url.openConnection();
            conn.setRequestMethod("PUT");
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setFixedLengthStreamingMode(rawData.length);

            try (java.io.OutputStream os = conn.getOutputStream()) {
                os.write(rawData);
                os.flush();
            }

            int responseCode = conn.getResponseCode();
            conn.disconnect();

            if (responseCode >= 200 && responseCode < 300) {
                pkg.setStatusOci("exitoso");
                packageResultRepository.save(pkg);

                return OciUploadResponseDto.builder()
                        .packageId(packageId)
                        .statusOci("exitoso")
                        .rutaObjeto("activos/package_" + packageId + ".json")
                        .build();
            } else {
                throw new RuntimeException("OCI respondió con código HTTP: " + responseCode);
            }
        } catch (Exception e) {
            pkg.setStatusOci("error");
            packageResultRepository.save(pkg);
            throw new RuntimeException("Error al subir a OCI: " + e.getMessage(), e);
        }
    }

    public List<PackageResult> getAllPackages() {
        return packageResultRepository.findAll();
    }

    public PackageResult getPackageById(Long id) {
        return packageResultRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("PackageResult no encontrado con id: " + id));
    }
}