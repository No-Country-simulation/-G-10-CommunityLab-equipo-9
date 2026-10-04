package com.insightedulab.backend_java.client;

import java.util.List;

/**
 * La respuesta de POST /v1/procesar (contrato Java ↔ IA v1, §4). Solo los campos que Java usa;
 * los demás (por ejemplo, "respuesta", que solo llega en tiempoReal) se ignoran.
 */
public record RespuestaIa(String versionContratoIa, String loteId, List<Resultado> resultados, Metricas metricas) {

    /** Uno por mensaje. Con estado ERROR, las etiquetas vienen en null (F4). */
    public record Resultado(
            String discordId,
            String estado,       // OK | ERROR
            String metodo,       // llm | palabrasClave | regla
            String intencion,
            Double confianza,
            String sentimiento,
            String tema,
            String razon
    ) {
        public boolean ok() {
            return "OK".equals(estado);
        }
    }

    public record Metricas(Integer duracionMs, Integer tokensIn, Integer tokensOut) {}
}
