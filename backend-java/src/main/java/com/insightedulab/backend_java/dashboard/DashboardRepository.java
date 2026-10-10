package com.insightedulab.backend_java.dashboard;

import com.insightedulab.backend_java.dashboard.VistasDashboard.DudaSinResponder;
import com.insightedulab.backend_java.dashboard.VistasDashboard.PersonaDesercion;
import com.insightedulab.backend_java.dashboard.VistasDashboard.PersonaFrustracion;
import com.insightedulab.backend_java.dashboard.VistasDashboard.TemaTendencia;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

/**
 * SQL del dashboard (T08, N5). Solo lectura: nada aquí cambia la base.
 *
 * Reglas comunes (DEC-123):
 * <ul>
 *   <li>los indicadores cuentan solo mensajes clasificados OK y de personas (no bots);</li>
 *   <li>las alertas cuentan solo a los alumnos (autor_rol = miembro): un mentor no "deserta";</li>
 *   <li>el período es [desde, hasta) en instantes; Java ya convirtió los días de la zona del dashboard.</li>
 * </ul>
 */
@Repository
public class DashboardRepository {

    /** Una fila del sentimiento: el día o la semana (en la zona), el sentimiento y cuántos. */
    public record FilaSentimiento(LocalDate inicio, String sentimiento, long cantidad) {}

    private static final String NOMBRE = """
            coalesce(nullif(m.contrato->'autor'->>'nombreVisible', ''), m.contrato->'autor'->>'nombreUsuario',
                     m.autor_id)""";
    private static final String CANAL = "coalesce(m.contrato->'canal'->>'nombre', m.canal_id)";
    private static final String OK_DE_PERSONA = "m.estado_clasificacion = 'OK' AND m.autor_tipo = 'persona'";
    private static final String SIN_OTRO = "(NOT CAST(:excluirOtro AS boolean) OR m.tema IS DISTINCT FROM 'otro')";
    private static final String EN_PERIODO = "m.fecha >= :desde AND m.fecha < :hasta";

    private static final String TOTALES = """
            SELECT count(*) AS mensajes,
                   count(DISTINCT m.autor_id) AS personas,
                   count(*) FILTER (WHERE m.estado_clasificacion = 'OK' AND m.intencion = 'PREGUNTA_FAQ') AS dudas,
                   count(*) FILTER (WHERE m.estado_clasificacion = 'OK' AND m.intencion = 'TESTIMONIO') AS logros,
                   count(*) FILTER (WHERE m.estado_clasificacion <> 'OK') AS sin_clasificar,
                   (SELECT count(*) FROM borradores WHERE estado = 'PENDIENTE' AND tipo <> 'RESPUESTA_BOT')
                       AS borradores_pendientes
              FROM mensajes m
             WHERE m.autor_tipo = 'persona' AND %s
            """.formatted(EN_PERIODO);

    // date_trunc('week') empieza el lunes. "AT TIME ZONE" pasa la fecha a la hora local antes de cortar el día
    private static final String SENTIMIENTO = """
            SELECT CAST(date_trunc(CAST(:unidad AS text), m.fecha AT TIME ZONE CAST(:zona AS text)) AS date) AS inicio,
                   m.sentimiento, count(*) AS cantidad
              FROM mensajes m
             WHERE %s AND m.sentimiento IS NOT NULL AND %s AND %s
             GROUP BY 1, 2
            """.formatted(OK_DE_PERSONA, EN_PERIODO, SIN_OTRO);

    // El período actual y el anterior de igual largo, en una sola pasada
    private static final String TEMAS = """
            SELECT m.tema,
                   count(*) FILTER (WHERE m.fecha >= :desde) AS actual,
                   count(*) FILTER (WHERE m.fecha < :desde) AS anterior
              FROM mensajes m
             WHERE %s AND m.tema IS NOT NULL AND m.fecha >= :desdeAnterior AND m.fecha < :hasta AND %s
             GROUP BY m.tema
             ORDER BY actual DESC, anterior DESC, m.tema
            """.formatted(OK_DE_PERSONA, SIN_OTRO);

    // Contra hoy, no contra el período: cualquier mensaje del alumno cuenta como actividad (también sin clasificar).
    // El nombre es el de su mensaje más reciente
    private static final String DESERCION = """
            SELECT (array_agg(%s ORDER BY m.fecha DESC, m.id DESC))[1] AS nombre,
                   max(m.fecha) AS ultimo,
                   floor(extract(epoch FROM now() - max(m.fecha)) / 86400) AS dias,
                   count(*) AS mensajes
              FROM mensajes m
             WHERE m.autor_tipo = 'persona' AND m.autor_rol = 'miembro'
             GROUP BY m.autor_id
            HAVING max(m.fecha) < now() - make_interval(days => :dias)
             ORDER BY ultimo, nombre
             LIMIT :limite
            """.formatted(NOMBRE);

    // DEC-121: un MUY_NEGATIVO en el período, o 2 negativos entre sus últimos 3 mensajes OK (hasta el fin del período)
    private static final String FRUSTRACION = """
            WITH ok AS (
                SELECT m.autor_id, m.fecha, m.sentimiento, %s AS nombre,
                       row_number() OVER (PARTITION BY m.autor_id ORDER BY m.fecha DESC, m.id DESC) AS orden
                  FROM mensajes m
                 WHERE %s AND m.autor_rol = 'miembro' AND m.sentimiento IS NOT NULL AND m.fecha < :hasta
            ), por_persona AS (
                SELECT autor_id,
                       (array_agg(nombre ORDER BY fecha DESC))[1] AS nombre,
                       count(*) FILTER (WHERE sentimiento = 'MUY_NEGATIVO' AND fecha >= :desde) AS muy_negativos,
                       count(*) FILTER (WHERE sentimiento IN ('NEGATIVO', 'MUY_NEGATIVO') AND fecha >= :desde)
                           AS negativos_periodo,
                       count(*) FILTER (WHERE orden <= 3 AND sentimiento IN ('NEGATIVO', 'MUY_NEGATIVO'))
                           AS negativos_ultimos3,
                       max(fecha) FILTER (WHERE sentimiento IN ('NEGATIVO', 'MUY_NEGATIVO')) AS ultimo_negativo
                  FROM ok
                 GROUP BY autor_id
            )
            SELECT * FROM por_persona
             WHERE muy_negativos > 0 OR negativos_ultimos3 >= 2
             ORDER BY ultimo_negativo DESC, nombre
             LIMIT :limite
            """.formatted(NOMBRE, OK_DE_PERSONA);

    // DEC-123: atendida = el bot la respondió (RESPONDIDA) o le contestó una persona distinta del autor.
    // Una DERIVADA sigue sin responder hasta que alguien la conteste. Las de menos de N horas no cuentan todavía
    private static final String DUDAS = """
            SELECT m.id, m.discord_id, m.fecha, m.tema, m.respuesta_estado, left(m.texto, 1000) AS texto,
                   %s AS nombre, %s AS canal, count(*) OVER () AS total
              FROM mensajes m
             WHERE %s AND m.intencion = 'PREGUNTA_FAQ' AND m.autor_rol = 'miembro' AND %s AND %s
               AND m.fecha < now() - make_interval(hours => :horas)
               AND m.respuesta_estado IS DISTINCT FROM 'RESPONDIDA'
               AND NOT EXISTS (SELECT 1 FROM mensajes r
                                WHERE r.responde_a = m.discord_id AND r.autor_tipo = 'persona'
                                  AND r.autor_id <> m.autor_id)
             ORDER BY m.fecha, m.id
             LIMIT :limite
            """.formatted(NOMBRE, CANAL, OK_DE_PERSONA, EN_PERIODO, SIN_OTRO);

    private final NamedParameterJdbcTemplate jdbc;

    public DashboardRepository(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** mensajes, personas, dudas, logros, sin clasificar y borradores pendientes, en ese orden. */
    public long[] totales(Instant desde, Instant hasta) {
        return jdbc.queryForObject(TOTALES, periodo(desde, hasta), (rs, i) -> new long[]{
                rs.getLong("mensajes"), rs.getLong("personas"), rs.getLong("dudas"), rs.getLong("logros"),
                rs.getLong("sin_clasificar"), rs.getLong("borradores_pendientes")});
    }

    /** unidad: "day" o "week" (date_trunc). */
    public List<FilaSentimiento> sentimiento(Instant desde, Instant hasta, String unidad, String zona,
                                             boolean excluirOtro) {
        MapSqlParameterSource p = periodo(desde, hasta).addValue("unidad", unidad).addValue("zona", zona)
                .addValue("excluirOtro", excluirOtro);
        return jdbc.query(SENTIMIENTO, p, (rs, i) -> new FilaSentimiento(rs.getObject("inicio", LocalDate.class),
                rs.getString("sentimiento"), rs.getLong("cantidad")));
    }

    public List<TemaTendencia> temas(Instant desdeAnterior, Instant desde, Instant hasta, boolean excluirOtro) {
        MapSqlParameterSource p = periodo(desde, hasta).addValue("desdeAnterior", Timestamp.from(desdeAnterior))
                .addValue("excluirOtro", excluirOtro);
        return jdbc.query(TEMAS, p, (rs, i) -> {
            long actual = rs.getLong("actual");
            long anterior = rs.getLong("anterior");
            return new TemaTendencia(rs.getString("tema"), actual, anterior, actual - anterior);
        });
    }

    public List<PersonaDesercion> desercion(int dias, int limite) {
        MapSqlParameterSource p = new MapSqlParameterSource().addValue("dias", dias).addValue("limite", limite);
        return jdbc.query(DESERCION, p, (rs, i) -> new PersonaDesercion(rs.getString("nombre"),
                instante(rs, "ultimo"), rs.getLong("dias"), rs.getLong("mensajes")));
    }

    public List<PersonaFrustracion> frustracion(Instant desde, Instant hasta, int limite) {
        MapSqlParameterSource p = periodo(desde, hasta).addValue("limite", limite);
        return jdbc.query(FRUSTRACION, p, (rs, i) -> {
            List<String> motivos = new ArrayList<>();
            if (rs.getLong("muy_negativos") > 0) {
                motivos.add("MUY_NEGATIVO");
            }
            if (rs.getLong("negativos_ultimos3") >= 2) {
                motivos.add("DOS_DE_TRES");
            }
            return new PersonaFrustracion(rs.getString("nombre"), motivos, rs.getLong("negativos_periodo"),
                    rs.getLong("negativos_ultimos3"), instante(rs, "ultimo_negativo"));
        });
    }

    /** Las dudas sin atender y, aparte, cuántas son en total (la lista tiene tope). */
    public record Dudas(long total, List<DudaSinResponder> dudas) {}

    public Dudas dudasSinResponder(Instant desde, Instant hasta, int horas, boolean excluirOtro, int limite) {
        MapSqlParameterSource p = periodo(desde, hasta).addValue("horas", horas)
                .addValue("excluirOtro", excluirOtro).addValue("limite", limite);
        long[] total = {0};
        List<DudaSinResponder> dudas = jdbc.query(DUDAS, p, (rs, i) -> {
            total[0] = rs.getLong("total");
            return new DudaSinResponder(rs.getLong("id"), rs.getString("discord_id"), instante(rs, "fecha"),
                    rs.getString("tema"), "DERIVADA".equals(rs.getString("respuesta_estado")), rs.getString("canal"),
                    rs.getString("nombre"), rs.getString("texto"));
        });
        return new Dudas(total[0], dudas);
    }

    private static MapSqlParameterSource periodo(Instant desde, Instant hasta) {
        return new MapSqlParameterSource().addValue("desde", Timestamp.from(desde))
                .addValue("hasta", Timestamp.from(hasta));
    }

    private static Instant instante(ResultSet rs, String columna) throws SQLException {
        Timestamp t = rs.getTimestamp(columna);
        return t == null ? null : t.toInstant();
    }
}
