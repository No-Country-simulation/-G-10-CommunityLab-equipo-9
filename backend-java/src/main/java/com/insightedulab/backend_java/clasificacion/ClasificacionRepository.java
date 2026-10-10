package com.insightedulab.backend_java.clasificacion;

import com.insightedulab.backend_java.client.RespuestaIa;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

import java.time.OffsetDateTime;
import java.util.List;

/**
 * SQL de la clasificación en segundo plano. Cada método es UNA sentencia (se confirma sola):
 * no queda ninguna transacción abierta mientras se espera a la IA.
 *
 * Las escrituras de resultados llevan "AND actualizado_en = :actualizadoEn": si el lote de la hora
 * cambió el mensaje mientras la IA lo procesaba, el resultado viejo no se guarda.
 */
@Repository
public class ClasificacionRepository {

    /** Un mensaje reservado para clasificar. actualizadoEn es la "foto" del momento de la reserva. */
    public record Pendiente(long id, String discordId, String servidorId, String versionContrato,
                            String contratoJson, OffsetDateTime actualizadoEn, OffsetDateTime fecha) {}

    // FOR UPDATE SKIP LOCKED: si otra ejecución está reservando los mismos, los salta en vez de esperar.
    // reservado_hasta: la reserva dura más que la espera a la IA y vence sola si Java se cae.
    private static final String RESERVAR = """
            UPDATE mensajes m
               SET reservado_hasta = now() + make_interval(secs => :segundos)
             WHERE m.id IN (
                   SELECT id FROM mensajes
                    WHERE estado_clasificacion = 'PENDIENTE'
                      AND servidor_id IS NOT NULL
                      AND (reservado_hasta IS NULL OR reservado_hasta < now())
                    ORDER BY fecha, id
                    LIMIT :tanda
                    FOR UPDATE SKIP LOCKED)
            RETURNING m.id, m.discord_id, m.servidor_id, m.version_contrato, m.contrato::text AS contrato,
                      m.actualizado_en, m.fecha
            """;

    private static final String GUARDAR_OK = """
            UPDATE mensajes
               SET intencion = :intencion, confianza = :confianza, sentimiento = :sentimiento, tema = :tema,
                   metodo_clasificacion = :metodo, estado_clasificacion = 'OK', clasificado_en = now(),
                   intentos_clasificacion = intentos_clasificacion + 1, reservado_hasta = NULL
             WHERE id = :id AND actualizado_en = :actualizadoEn AND estado_clasificacion = 'PENDIENTE'
            """;

    // Las etiquetas no se tocan (F4). En el SET, intentos_clasificacion es el valor de antes de sumar.
    private static final String GUARDAR_ERROR = """
            UPDATE mensajes
               SET intentos_clasificacion = intentos_clasificacion + 1,
                   estado_clasificacion = CASE WHEN intentos_clasificacion + 1 >= :maxIntentos
                                               THEN 'ERROR' ELSE 'PENDIENTE' END,
                   metodo_clasificacion = COALESCE(:metodo, metodo_clasificacion),
                   reservado_hasta = NULL
             WHERE id = :id AND actualizado_en = :actualizadoEn AND estado_clasificacion = 'PENDIENTE'
            RETURNING estado_clasificacion
            """;

    // Falla de toda la llamada: suma el intento pero el estado no cambia (sigue PENDIENTE)
    private static final String SUMAR_INTENTO = """
            UPDATE mensajes
               SET intentos_clasificacion = intentos_clasificacion + 1, reservado_hasta = NULL
             WHERE id = :id AND actualizado_en = :actualizadoEn AND estado_clasificacion = 'PENDIENTE'
            """;

    private static final String LIBERAR = "UPDATE mensajes SET reservado_hasta = NULL WHERE id = :id";

    private static final String CONTAR_SIN_SERVIDOR =
            "SELECT count(*) FROM mensajes WHERE estado_clasificacion = 'PENDIENTE' AND servidor_id IS NULL";

    private final NamedParameterJdbcTemplate jdbc;

    public ClasificacionRepository(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<Pendiente> reservar(int tanda, int segundos) {
        MapSqlParameterSource p = new MapSqlParameterSource().addValue("tanda", tanda).addValue("segundos", segundos);
        return jdbc.query(RESERVAR, p, (rs, i) -> new Pendiente(
                rs.getLong("id"), rs.getString("discord_id"), rs.getString("servidor_id"),
                rs.getString("version_contrato"), rs.getString("contrato"),
                rs.getObject("actualizado_en", OffsetDateTime.class), rs.getObject("fecha", OffsetDateTime.class)));
    }

    /** true si se guardó; false si el mensaje cambió mientras tanto. */
    public boolean guardarOk(Pendiente m, RespuestaIa.Resultado r) {
        MapSqlParameterSource p = foto(m)
                .addValue("intencion", r.intencion())
                .addValue("confianza", r.confianza())
                .addValue("sentimiento", r.sentimiento())
                .addValue("tema", r.tema())
                .addValue("metodo", r.metodo());
        return jdbc.update(GUARDAR_OK, p) == 1;
    }

    /** El estado en que quedó (PENDIENTE o ERROR), o null si el mensaje cambió mientras tanto. */
    public String guardarError(Pendiente m, String metodo, int maxIntentos) {
        MapSqlParameterSource p = foto(m).addValue("metodo", metodo).addValue("maxIntentos", maxIntentos);
        List<String> estado = jdbc.queryForList(GUARDAR_ERROR, p, String.class);
        return estado.isEmpty() ? null : estado.get(0);
    }

    /** true si se sumó; false si el mensaje cambió mientras tanto. */
    public boolean sumarIntento(Pendiente m) {
        return jdbc.update(SUMAR_INTENTO, foto(m)) == 1;
    }

    public void liberar(Pendiente m) {
        jdbc.update(LIBERAR, new MapSqlParameterSource("id", m.id()));
    }

    public long contarSinServidor() {
        Long n = jdbc.queryForObject(CONTAR_SIN_SERVIDOR, new MapSqlParameterSource(), Long.class);
        return n == null ? 0 : n;
    }

    private static MapSqlParameterSource foto(Pendiente m) {
        return new MapSqlParameterSource().addValue("id", m.id()).addValue("actualizadoEn", m.actualizadoEn());
    }
}
