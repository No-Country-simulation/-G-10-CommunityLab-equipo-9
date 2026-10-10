package com.insightedulab.backend_java.client;

/**
 * La respuesta de POST /v1/generar (contrato Java ↔ IA v1, §9). Con estado ERROR no hay decisión ni textos (F4).
 *
 * @param publicable   null si estado = ERROR
 * @param postLinkedin y casoExito: los dos solo si publicable = true
 */
public record RespuestaGenerar(
        String versionContratoIa,
        String pedidoId,
        String discordId,
        String estado,       // OK | ERROR
        Boolean publicable,
        String motivo,
        String postLinkedin,
        String casoExito,
        RespuestaIa.Metricas metricas
) {
    public boolean ok() {
        return "OK".equals(estado);
    }
}
