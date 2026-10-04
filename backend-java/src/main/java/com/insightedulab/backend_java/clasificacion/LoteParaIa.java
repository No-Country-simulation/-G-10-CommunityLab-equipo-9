package com.insightedulab.backend_java.clasificacion;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightedulab.backend_java.clasificacion.ClasificacionRepository.Pendiente;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Arma el Lote del contrato v1 que se envía a la IA, con las cajas tal cual se guardaron en mensajes.contrato.
 * Lo usan la clasificación en segundo plano (modo historial) y la puerta en vivo (modo tiempoReal).
 */
@Component
public class LoteParaIa {

    private static final DateTimeFormatter FECHA_UTC = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'");

    private final ObjectMapper objectMapper;

    public LoteParaIa(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    /** Los mensajes van en el orden recibido: quien llama los ordena si hace falta. */
    public Map<String, Object> armar(String loteId, String servidorId, String modo, List<Pendiente> mensajes) {
        Map<String, Object> lote = new LinkedHashMap<>();
        lote.put("versionContrato", mensajes.get(0).versionContrato());
        lote.put("loteId", loteId);
        lote.put("fuente", "discord");
        lote.put("modo", modo);
        lote.put("servidorId", servidorId);
        lote.put("generadoEn", FECHA_UTC.format(Instant.now().truncatedTo(ChronoUnit.MILLIS).atOffset(ZoneOffset.UTC)));
        List<Map<String, Object>> cajas = new ArrayList<>(mensajes.size());
        for (Pendiente m : mensajes) {
            cajas.add(caja(m));
        }
        lote.put("mensajes", cajas);
        return lote;
    }

    private Map<String, Object> caja(Pendiente m) {
        try {
            return objectMapper.readValue(m.contratoJson(), new TypeReference<>() {});
        } catch (IOException e) {
            throw new IllegalStateException("La caja del mensaje " + m.discordId() + " no es JSON válido", e);
        }
    }
}
