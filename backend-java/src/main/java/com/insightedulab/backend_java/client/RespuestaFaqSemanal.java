package com.insightedulab.backend_java.client;

import java.util.List;

/**
 * La respuesta de POST /v1/faq (contrato Java ↔ IA v1, §10). Hay texto si y solo si hay grupos;
 * con estado ERROR no hay ni texto ni grupos (F4).
 *
 * @param texto el borrador en Markdown, o null si no hubo preguntas repetidas
 */
public record RespuestaFaqSemanal(
        String versionContratoIa,
        String pedidoId,
        String semana,
        String estado,       // OK | ERROR
        String texto,
        String motivo,
        List<Grupo> grupos,
        RespuestaIa.Metricas metricas
) {
    /** Una pregunta repetida por al menos 2 personas. */
    public record Grupo(String pregunta, Integer personas, Boolean respondida, String origen, List<String> fuentes,
                        String motivo) {}

    public boolean ok() {
        return "OK".equals(estado);
    }
}
