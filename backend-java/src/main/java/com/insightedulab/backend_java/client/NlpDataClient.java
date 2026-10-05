package com.insightedulab.backend_java.client;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightedulab.backend_java.dto.request.CommunityProcessRequestDto;
import com.insightedulab.backend_java.dto.response.data.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.List;

@Component
public class NlpDataClient {

    private static final Logger log = LoggerFactory.getLogger(NlpDataClient.class);
    private final RestTemplate restTemplate;
    private final String nlpServiceUrl;
    private final ObjectMapper objectMapper;

    public NlpDataClient(
            @Value("${python.nlp.service.url:http://localhost:8000}") String nlpServiceUrl,
            ObjectMapper objectMapper
    ) {
        this.restTemplate = new RestTemplate();
        this.nlpServiceUrl = nlpServiceUrl;
        this.objectMapper = objectMapper;
    }

    /**
     * Envía la estructura completa del lote hacia FastAPI usando RestTemplate para asegurar el envío del Body.
     */
    public OutputOrquestadorDTO ejecutarOrquestador(CommunityProcessRequestDto inputDTO) {
        try {
            String jsonPayload = objectMapper.writeValueAsString(inputDTO);
            log.info("🚀 Enviando lote {} al motor de IA en FastAPI. Payload: {}", inputDTO.getLoteId(), jsonPayload);

            String url = nlpServiceUrl + "/api/v1/orquestador/ejecutar";

            // Configuramos cabeceras explícitas indicando que enviamos y recibimos JSON
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setAccept(List.of(MediaType.APPLICATION_JSON));

            // Envolvemos el JSON serializado en una entidad HTTP
            HttpEntity<String> entity = new HttpEntity<>(jsonPayload, headers);

            // Disparamos la petición POST
            ResponseEntity<OutputOrquestadorDTO> response = restTemplate.exchange(
                    url,
                    HttpMethod.POST,
                    entity,
                    OutputOrquestadorDTO.class
            );

            return response.getBody();

        } catch (Exception e) {
            log.error("❌ Error en cliente REST de Python NLP al ejecutar orquestador: {}", e.getMessage(), e);

            // 🛡️ FALLBACK TEMPORAL: Si Python falla, devolvemos el Mock
            return crearFallbackOutput(inputDTO);
        }
    }

    private OutputOrquestadorDTO crearFallbackOutput(CommunityProcessRequestDto inputDTO) {
        String loteId = (inputDTO != null && inputDTO.getLoteId() != null) ? inputDTO.getLoteId() : "lote-fallback-id";
        String tiempoActual = LocalDateTime.now().toString();

        RespuestaDiscordDTO discordDTO = new RespuestaDiscordDTO();
        discordDTO.setLoteId(loteId);
        discordDTO.setRespuestas(List.of());

        ResumenLoteDTO resumenDTO = new ResumenLoteDTO();
        resumenDTO.setTotalMensajes(inputDTO != null && inputDTO.getMensajes() != null ? inputDTO.getMensajes().size() : 0);
        resumenDTO.setRequierenHumano(1);

        PaqueteFinalDTO paqueteDTO = new PaqueteFinalDTO();
        paqueteDTO.setLoteId(loteId);
        paqueteDTO.setResumenLote(resumenDTO);
        paqueteDTO.setActivosGenerados(List.of());
        paqueteDTO.setRequierenHumano(List.of());

        LogEjecucionDTO logDTO = new LogEjecucionDTO();
        logDTO.setLoteId(loteId);
        logDTO.setTimestampInicio(tiempoActual);
        logDTO.setTimestampFin(tiempoActual);
        logDTO.setDuracionTotalMs(0L);
        logDTO.setTokensTotales(0);
        logDTO.setSublogs(List.of());
        logDTO.setErrores(List.of("Modo degradado activado: FastAPI no disponible."));

        OutputOrquestadorDTO outputFallback = new OutputOrquestadorDTO();
        outputFallback.setLoteId(loteId);
        outputFallback.setRespuestaDiscord(discordDTO);
        outputFallback.setPaqueteFinal(paqueteDTO);
        outputFallback.setLogEjecucion(logDTO);

        return outputFallback;
    }
}