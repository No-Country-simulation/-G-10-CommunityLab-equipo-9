package com.insightedulab.backend_java.client;

import java.util.List;

/**
 * La respuesta de POST /v1/procesar (contrato Java ↔ IA v1, §4). Solo los campos que Java usa;
 * los demás se ignoran.
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
            String razon,
            Respuesta respuesta  // solo en tiempoReal y para PREGUNTA_FAQ (§4.2); si no, null
    ) {
        /** Sin respuesta del Agente FAQ: así llega siempre en modo historial. */
        public Resultado(String discordId, String estado, String metodo, String intencion, Double confianza,
                         String sentimiento, String tema, String razon) {
            this(discordId, estado, metodo, intencion, confianza, sentimiento, tema, razon, null);
        }

        public boolean ok() {
            return "OK".equals(estado);
        }
    }

    /**
     * La respuesta del Agente FAQ a una duda (§4.2). D3: se publica solo si {@code encontrada} es true.
     * Si se agotó el tope de tiempo real (DEC-54), llega con encontrada = false y el motivo.
     */
    public record Respuesta(String texto, Boolean encontrada, List<String> fuentes, String motivo) {
        public boolean publicable() {
            return Boolean.TRUE.equals(encontrada) && texto != null && !texto.isBlank();
        }
    }

    public record Metricas(Integer duracionMs, Integer tokensIn, Integer tokensOut) {}
}
