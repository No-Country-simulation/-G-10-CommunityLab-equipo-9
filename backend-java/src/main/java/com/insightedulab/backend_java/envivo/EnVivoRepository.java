package com.insightedulab.backend_java.envivo;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightedulab.backend_java.clasificacion.ClasificacionRepository.Pendiente;
import com.insightedulab.backend_java.client.RespuestaIa;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.Types;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;

/**
 * SQL de la puerta en vivo (T05). Usa las mismas reglas que la clasificación en segundo plano (T04):
 * reserva con reservado_hasta y guardas por actualizado_en y estado PENDIENTE.
 */
@Repository
public class EnVivoRepository {

    /** Qué guardar de la respuesta del bot (DEC-66). Todo null si el bot no responde con texto. */
    public record Respuesta(String estado, String texto, List<String> fuentes) {
        static final Respuesta NINGUNA = new Respuesta(null, null, null);
    }

    // Un solo mensaje, por su discord_id. Solo si nadie lo clasificó, nadie lo tiene reservado
    // y el bot todavía no le respondió: así un mensaje nunca se clasifica ni se responde dos veces.
    private static final String RESERVAR = """
            UPDATE mensajes
               SET reservado_hasta = now() + make_interval(secs => :segundos)
             WHERE discord_id = :discordId
               AND estado_clasificacion = 'PENDIENTE'
               AND respuesta_estado IS NULL
               AND servidor_id IS NOT NULL
               AND (reservado_hasta IS NULL OR reservado_hasta < now())
            RETURNING id, discord_id, servidor_id, version_contrato, contrato::text AS contrato, actualizado_en, fecha
            """;

    // Las etiquetas y la respuesta, en UNA sentencia: o se guardan las dos o ninguna.
    // Mismas guardas que GUARDAR_OK de T04, más "el bot todavía no respondió".
    private static final String GUARDAR_OK = """
            UPDATE mensajes
               SET intencion = :intencion, confianza = :confianza, sentimiento = :sentimiento, tema = :tema,
                   metodo_clasificacion = :metodo, estado_clasificacion = 'OK', clasificado_en = now(),
                   intentos_clasificacion = intentos_clasificacion + 1, reservado_hasta = NULL,
                   respuesta_estado = :respuestaEstado,
                   respuesta_texto = :respuestaTexto,
                   respuesta_fuentes = CAST(:respuestaFuentes AS jsonb),
                   respondido_en = CASE WHEN CAST(:respuestaEstado AS text) IS NULL THEN NULL ELSE now() END
             WHERE id = :id AND actualizado_en = :actualizadoEn AND estado_clasificacion = 'PENDIENTE'
               AND respuesta_estado IS NULL
            """;

    private final NamedParameterJdbcTemplate jdbc;
    private final ObjectMapper objectMapper;

    public EnVivoRepository(NamedParameterJdbcTemplate jdbc, ObjectMapper objectMapper) {
        this.jdbc = jdbc;
        this.objectMapper = objectMapper;
    }

    /** El mensaje reservado, o vacío si ya está clasificado, respondido o reservado por otro. */
    public Optional<Pendiente> reservar(String discordId, int segundos) {
        MapSqlParameterSource p = new MapSqlParameterSource()
                .addValue("discordId", discordId).addValue("segundos", segundos);
        List<Pendiente> filas = jdbc.query(RESERVAR, p, (rs, i) -> new Pendiente(
                rs.getLong("id"), rs.getString("discord_id"), rs.getString("servidor_id"),
                rs.getString("version_contrato"), rs.getString("contrato"),
                rs.getObject("actualizado_en", OffsetDateTime.class), rs.getObject("fecha", OffsetDateTime.class)));
        return filas.stream().findFirst();
    }

    /** true si se guardó; false si el mensaje cambió mientras la IA lo procesaba. */
    public boolean guardarOk(Pendiente m, RespuestaIa.Resultado r, Respuesta respuesta) {
        MapSqlParameterSource p = new MapSqlParameterSource()
                .addValue("id", m.id())
                .addValue("actualizadoEn", m.actualizadoEn())
                .addValue("intencion", r.intencion())
                .addValue("confianza", r.confianza())
                .addValue("sentimiento", r.sentimiento())
                .addValue("tema", r.tema())
                .addValue("metodo", r.metodo())
                .addValue("respuestaEstado", respuesta.estado(), Types.VARCHAR)
                .addValue("respuestaTexto", respuesta.texto(), Types.VARCHAR)
                .addValue("respuestaFuentes", aJson(respuesta.fuentes()), Types.VARCHAR);
        return jdbc.update(GUARDAR_OK, p) == 1;
    }

    private String aJson(List<String> fuentes) {
        if (fuentes == null) {
            return null;
        }
        try {
            return objectMapper.writeValueAsString(fuentes);
        } catch (JsonProcessingException e) {
            throw new IllegalArgumentException("Las fuentes no se pudieron convertir a JSON", e);
        }
    }
}
