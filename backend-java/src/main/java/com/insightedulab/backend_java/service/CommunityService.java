package com.insightedulab.backend_java.service;

import com.insightedulab.backend_java.dto.request.CommunityProcessRequestDto;
import com.insightedulab.backend_java.dto.request.CurationRequestDto;
import com.insightedulab.backend_java.dto.request.InteractionInputDto;
import com.insightedulab.backend_java.dto.response.OciUploadResponseDto;
import com.insightedulab.backend_java.model.Interaction;
import com.insightedulab.backend_java.model.PackageResult;
import com.insightedulab.backend_java.model.enums.TipoAutor;
import com.insightedulab.backend_java.repository.PackageResultRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

@Service
public class CommunityService {

    private final PackageResultRepository packageResultRepository;

    @Value("${oci.par.url}")
    private String parUrlBase;

    public CommunityService(PackageResultRepository packageResultRepository) {
        this.packageResultRepository = packageResultRepository;
    }

    @Transactional
    public PackageResult processBatch(CommunityProcessRequestDto request) {
        // 1. Creamos la lista de interacciones mapeadas previamente
        List<Interaction> interacciones = new ArrayList<>();

        if (request.getInteracciones() != null) {
            for (InteractionInputDto dto : request.getInteracciones()) {
                Interaction interaction = Interaction.builder()
                        // Nota: el packageResult se asociará automáticamente gracias al Cascade en el save
                        .loteId(request.getLoteId())
                        .tipoServidor(request.getTipoServidor())
                        .discordId(dto.getDiscordId())
                        .channelId(dto.getChannelId())
                        .authorId(dto.getAuthorId())
                        .authorUsername(dto.getAuthorUsername())
                        .autorNombre(dto.getAutorNombre())
                        .autorRol(dto.getAutorRol())
                        .textoMensaje(dto.getTextoMensaje())
                        .tipoAutor(dto.getTipoAutor())
                        .clasificacionSentimiento(dto.getClasificacionSentimiento())
                        .timestampMensaje(dto.getTimestampMensaje() != null ? dto.getTimestampMensaje() : Instant.now())
                        .build();

                interacciones.add(interaction);
            }
        }

        // 2. Construimos el paquete completo con sus interacciones ya listas
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

        // Asignamos la relación bidireccional correctamente para cada interacción
        for (Interaction interaction : interacciones) {
            interaction.setPackageResult(pkg);
            pkg.getInteracciones().add(interaction);
        }

        // 3. Un solo guardado en base de datos (Hibernate se encarga de guardar el padre y los hijos por CascadeType.ALL)
        return packageResultRepository.save(pkg);
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
                pkg.getTimestampFin() != null ? "\"" + pkg.getTimestampFin() + "\"" : "null",
                packageId
        );

        try {
            sendJsonToOci(targetUrl, jsonPayload);

            pkg.setStatusOci("exitoso");
            packageResultRepository.save(pkg);

            return OciUploadResponseDto.builder()
                    .packageId(packageId)
                    .statusOci("exitoso")
                    .rutaObjeto("activos/package_" + packageId + ".json")
                    .build();

        } catch (Exception e) {
            pkg.setStatusOci("error");
            packageResultRepository.save(pkg);
            throw new RuntimeException("Error al subir a OCI: " + e.getMessage(), e);
        }
    }

    private void sendJsonToOci(String targetUrl, String jsonPayload) throws Exception {
        byte[] rawData = jsonPayload.getBytes(StandardCharsets.UTF_8);
        URL url = new URI(targetUrl).toURL();
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("PUT");
        conn.setDoOutput(true);
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setFixedLengthStreamingMode(rawData.length);

        try (OutputStream os = conn.getOutputStream()) {
            os.write(rawData);
            os.flush();
        }

        int responseCode = conn.getResponseCode();
        conn.disconnect();

        if (responseCode < 200 || responseCode >= 300) {
            throw new RuntimeException("OCI respondió con código HTTP: " + responseCode);
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