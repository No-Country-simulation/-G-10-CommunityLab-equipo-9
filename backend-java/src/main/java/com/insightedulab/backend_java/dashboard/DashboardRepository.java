package com.insightedulab.backend_java.dashboard;

import com.insightedulab.backend_java.dashboard.VistasDashboard.Bot;
import com.insightedulab.backend_java.dashboard.VistasDashboard.DudaSinResponder;
import com.insightedulab.backend_java.dashboard.VistasDashboard.Embudo;
import com.insightedulab.backend_java.dashboard.VistasDashboard.LogroAAprobacion;
import com.insightedulab.backend_java.dashboard.VistasDashboard.PersonaDesercion;
import com.insightedulab.backend_java.dashboard.VistasDashboard.PersonaFrustracion;
import com.insightedulab.backend_java.dashboard.VistasDashboard.SemanaCantidad;
import com.insightedulab.backend_java.dashboard.VistasDashboard.TemaCantidad;
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
 *   <li>el período es [desde, hasta) en instantes; Java ya convirtió los días de la zona del dashboard;</li>
 *   <li>los tiempos se resumen con la mediana, que no se deja arrastrar por un caso raro (DEC-155).</li>
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
    // T12: rol=alumnos deja solo a los alumnos (autor_rol = miembro); rol=todos, a todas las personas
    private static final String SOLO_ALUMNOS = "(NOT CAST(:soloAlumnos AS boolean) OR m.autor_rol = 'miembro')";

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
             WHERE %s AND m.sentimiento IS NOT NULL AND %s AND %s AND %s
             GROUP BY 1, 2
            """.formatted(OK_DE_PERSONA, EN_PERIODO, SIN_OTRO, SOLO_ALUMNOS);

    // El período actual y el anterior de igual largo, en una sola pasada
    private static final String TEMAS = """
            SELECT m.tema,
                   count(*) FILTER (WHERE m.fecha >= :desde) AS actual,
                   count(*) FILTER (WHERE m.fecha < :desde) AS anterior
              FROM mensajes m
             WHERE %s AND m.tema IS NOT NULL AND m.fecha >= :desdeAnterior AND m.fecha < :hasta AND %s AND %s
             GROUP BY m.tema
             ORDER BY actual DESC, anterior DESC, m.tema
            """.formatted(OK_DE_PERSONA, SIN_OTRO, SOLO_ALUMNOS);

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

    // DEC-121: un MUY_NEGATIVO en el período, o 2 negativos entre sus últimos 3 mensajes OK.
    // DEC-157: los "últimos 3" son solo del período; un negativo viejo ya no dispara la alerta
    private static final String FRUSTRACION = """
            WITH ok AS (
                SELECT m.autor_id, m.fecha, m.sentimiento, %s AS nombre,
                       row_number() OVER (PARTITION BY m.autor_id ORDER BY m.fecha DESC, m.id DESC) AS orden
                  FROM mensajes m
                 WHERE %s AND m.autor_rol = 'miembro' AND m.sentimiento IS NOT NULL AND %s
            ), por_persona AS (
                SELECT autor_id,
                       (array_agg(nombre ORDER BY fecha DESC))[1] AS nombre,
                       count(*) FILTER (WHERE sentimiento = 'MUY_NEGATIVO') AS muy_negativos,
                       count(*) FILTER (WHERE sentimiento IN ('NEGATIVO', 'MUY_NEGATIVO')) AS negativos_periodo,
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
            """.formatted(NOMBRE, OK_DE_PERSONA, EN_PERIODO);

    // DEC-123: atendida = el bot la respondió (RESPONDIDA) o le contestó una persona distinta del autor.
    // Una DERIVADA sigue sin responder hasta que alguien la conteste. Las de menos de N horas no cuentan todavía
    private static final String DUDAS = """
            SELECT m.id, m.discord_id, m.fecha, m.tema, m.respuesta_estado, left(m.texto, 1000) AS texto,
                   %s AS nombre, %s AS canal, m.servidor_id, m.canal_id, count(*) OVER () AS total
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

    // ── Vista Comunidad (T12) ──

    // Como la deserción: cualquier mensaje del alumno es actividad (también sin clasificar). Hasta el fin del período
    private static final String ALUMNOS = """
            SELECT count(DISTINCT m.autor_id) AS total,
                   count(DISTINCT m.autor_id) FILTER (WHERE m.fecha >= :hace7) AS activos7,
                   count(DISTINCT m.autor_id) FILTER (WHERE m.fecha >= :hace30) AS activos30,
                   count(*) FILTER (WHERE m.estado_clasificacion = 'OK' AND m.intencion = 'PREGUNTA_FAQ'
                                      AND m.fecha >= :desde) AS dudas
              FROM mensajes m
             WHERE m.autor_tipo = 'persona' AND m.autor_rol = 'miembro' AND m.fecha < :hasta
            """;

    // Las dudas que vio el bot son las RESPONDIDA y las DERIVADA; las demás llegaron por lote, sin pasar por él.
    // Todas las personas: el bot responde igual a un alumno que a un mentor
    private static final String BOT = """
            SELECT count(*) FILTER (WHERE m.respuesta_estado = 'RESPONDIDA') AS respondidas,
                   count(*) FILTER (WHERE m.respuesta_estado = 'DERIVADA') AS derivadas,
                   count(*) FILTER (WHERE m.respuesta_estado IS NULL) AS sin_bot,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM m.respondido_en - m.fecha))
                       FILTER (WHERE m.respuesta_estado IS NOT NULL AND m.respondido_en IS NOT NULL) AS segundos
              FROM mensajes m
             WHERE %s AND m.intencion = 'PREGUNTA_FAQ' AND %s
            """.formatted(OK_DE_PERSONA, EN_PERIODO);

    // Lo que el bot no encontró en los PDF: qué falta en los documentos
    private static final String DERIVADAS_POR_TEMA = """
            SELECT m.tema, count(*) AS cantidad
              FROM mensajes m
             WHERE m.autor_tipo = 'persona' AND m.respuesta_estado = 'DERIVADA' AND %s
             GROUP BY m.tema
             ORDER BY cantidad DESC, m.tema
            """.formatted(EN_PERIODO);

    // ── Vista Contenido (T12). RESPUESTA_BOT nunca cuenta: no pasa por el panel ──

    // Hoy, no en el período: lo que espera revisión ahora
    private static final String PENDIENTES = """
            SELECT b.tipo, count(*) AS cantidad, min(b.creado_en) AS mas_antiguo
              FROM borradores b
             WHERE b.estado = 'PENDIENTE' AND b.tipo <> 'RESPUESTA_BOT'
             GROUP BY b.tipo
            """;

    // Lo revisado (aprobado o rechazado) en el período. percentile_cont ignora los tiempos vacíos
    // y, con un número par de datos, promedia los dos del medio
    private static final String REVISION = """
            SELECT b.tipo,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY b.tiempo_curaduria_seg) AS mediana,
                   count(b.tiempo_curaduria_seg) AS n,
                   count(*) FILTER (WHERE b.estado = 'APROBADO') AS aprobados,
                   count(*) FILTER (WHERE b.estado = 'RECHAZADO') AS rechazados
              FROM borradores b
             WHERE b.tipo <> 'RESPUESTA_BOT' AND b.estado IN ('APROBADO', 'RECHAZADO')
               AND coalesce(b.aprobado_en, b.rechazado_en) >= :desde
               AND coalesce(b.aprobado_en, b.rechazado_en) < :hasta
             GROUP BY b.tipo
            """;

    // Los logros del período (por la fecha de su mensaje) y qué pasó con ellos, hoy
    private static final String EMBUDO = """
            SELECT count(*) AS logros,
                   count(*) FILTER (WHERE m.generacion_estado = 'GENERADO') AS publicables,
                   count(*) FILTER (WHERE m.generacion_estado = 'NO_PUBLICABLE') AS no_publicables,
                   count(*) FILTER (WHERE EXISTS (SELECT 1 FROM borradores b
                                                   WHERE b.mensaje_id = m.id AND b.tipo = 'POST_LINKEDIN'
                                                     AND b.estado = 'APROBADO')) AS con_post_aprobado,
                   (SELECT count(*) FROM mensajes m WHERE m.autor_tipo = 'persona' AND %s) AS mensajes
              FROM mensajes m
             WHERE %s AND m.intencion = 'TESTIMONIO' AND %s
            """.formatted(EN_PERIODO, OK_DE_PERSONA, EN_PERIODO);

    private static final String APROBADOS_POR_SEMANA = """
            SELECT CAST(date_trunc('week', b.aprobado_en AT TIME ZONE CAST(:zona AS text)) AS date) AS inicio,
                   count(*) AS cantidad
              FROM borradores b
             WHERE b.estado = 'APROBADO' AND b.tipo <> 'RESPUESTA_BOT'
               AND b.aprobado_en >= :desde AND b.aprobado_en < :hasta
             GROUP BY 1
            """;

    // Los posts aprobados en el período: cuánto tardó cada logro en convertirse en contenido aprobado
    private static final String LOGRO_A_APROBACION = """
            SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM b.aprobado_en - m.fecha) / 3600)
                       AS horas,
                   count(*) AS n
              FROM borradores b
              JOIN mensajes m ON m.id = b.mensaje_id
             WHERE b.tipo = 'POST_LINKEDIN' AND b.estado = 'APROBADO'
               AND b.aprobado_en >= :desde AND b.aprobado_en < :hasta
            """;

    // Todo lo que ya está en el bucket, sin importar el período
    private static final String ACTIVOS_OCI = "SELECT count(*) FROM subidas_oci WHERE estado = 'SUBIDO'";

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
                                             boolean excluirOtro, boolean soloAlumnos) {
        MapSqlParameterSource p = periodo(desde, hasta).addValue("unidad", unidad).addValue("zona", zona)
                .addValue("excluirOtro", excluirOtro).addValue("soloAlumnos", soloAlumnos);
        return jdbc.query(SENTIMIENTO, p, (rs, i) -> new FilaSentimiento(rs.getObject("inicio", LocalDate.class),
                rs.getString("sentimiento"), rs.getLong("cantidad")));
    }

    public List<TemaTendencia> temas(Instant desdeAnterior, Instant desde, Instant hasta, boolean excluirOtro,
                                     boolean soloAlumnos) {
        MapSqlParameterSource p = periodo(desde, hasta).addValue("desdeAnterior", Timestamp.from(desdeAnterior))
                .addValue("excluirOtro", excluirOtro).addValue("soloAlumnos", soloAlumnos);
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
                    rs.getString("nombre"), rs.getString("texto"), rs.getString("servidor_id"),
                    rs.getString("canal_id"));
        });
        return new Dudas(total[0], dudas);
    }

    // ── Vista Comunidad (T12) ──

    /** total, activos en 7 días, activos en 30 días y dudas del período, en ese orden. */
    public long[] alumnos(Instant hace7Dias, Instant hace30Dias, Instant desde, Instant hasta) {
        MapSqlParameterSource p = periodo(desde, hasta).addValue("hace7", Timestamp.from(hace7Dias))
                .addValue("hace30", Timestamp.from(hace30Dias));
        return jdbc.queryForObject(ALUMNOS, p, (rs, i) -> new long[]{rs.getLong("total"), rs.getLong("activos7"),
                rs.getLong("activos30"), rs.getLong("dudas")});
    }

    public Bot bot(Instant desde, Instant hasta) {
        return jdbc.queryForObject(BOT, periodo(desde, hasta), (rs, i) -> new Bot(rs.getLong("respondidas"),
                rs.getLong("derivadas"), rs.getLong("sin_bot"), decimal(rs, "segundos")));
    }

    public List<TemaCantidad> derivadasPorTema(Instant desde, Instant hasta) {
        return jdbc.query(DERIVADAS_POR_TEMA, periodo(desde, hasta),
                (rs, i) -> new TemaCantidad(rs.getString("tema"), rs.getLong("cantidad")));
    }

    // ── Vista Contenido (T12) ──

    /** Una fila por tipo con pendientes: cuántos y desde cuándo espera el más antiguo. */
    public record FilaPendientes(String tipo, long cantidad, Instant masAntiguo) {}

    public List<FilaPendientes> pendientes() {
        return jdbc.query(PENDIENTES, new MapSqlParameterSource(), (rs, i) -> new FilaPendientes(rs.getString("tipo"),
                rs.getLong("cantidad"), instante(rs, "mas_antiguo")));
    }

    /** Una fila por tipo revisado en el período: la mediana y la n del tiempo, y cuántos aprobados y rechazados. */
    public record FilaRevision(String tipo, Double medianaSeg, long n, long aprobados, long rechazados) {}

    public List<FilaRevision> revision(Instant desde, Instant hasta) {
        return jdbc.query(REVISION, periodo(desde, hasta), (rs, i) -> new FilaRevision(rs.getString("tipo"),
                decimal(rs, "mediana"), rs.getLong("n"), rs.getLong("aprobados"), rs.getLong("rechazados")));
    }

    /** El embudo de los logros del período y, aparte, los mensajes de personas del período. */
    public record FilaEmbudo(Embudo embudo, long mensajesDePersonas) {}

    public FilaEmbudo embudo(Instant desde, Instant hasta) {
        return jdbc.queryForObject(EMBUDO, periodo(desde, hasta), (rs, i) -> new FilaEmbudo(
                new Embudo(rs.getLong("logros"), rs.getLong("publicables"), rs.getLong("no_publicables"),
                        rs.getLong("con_post_aprobado")), rs.getLong("mensajes")));
    }

    /** Solo las semanas con aprobados; Java completa los ceros. */
    public List<SemanaCantidad> aprobadosPorSemana(Instant desde, Instant hasta, String zona) {
        MapSqlParameterSource p = periodo(desde, hasta).addValue("zona", zona);
        return jdbc.query(APROBADOS_POR_SEMANA, p, (rs, i) -> new SemanaCantidad(rs.getObject("inicio",
                LocalDate.class), rs.getLong("cantidad")));
    }

    public LogroAAprobacion logroAAprobacion(Instant desde, Instant hasta) {
        return jdbc.queryForObject(LOGRO_A_APROBACION, periodo(desde, hasta),
                (rs, i) -> new LogroAAprobacion(decimal(rs, "horas"), rs.getLong("n")));
    }

    public long activosOci() {
        Long n = jdbc.queryForObject(ACTIVOS_OCI, new MapSqlParameterSource(), Long.class);
        return n == null ? 0 : n;
    }

    private static MapSqlParameterSource periodo(Instant desde, Instant hasta) {
        return new MapSqlParameterSource().addValue("desde", Timestamp.from(desde))
                .addValue("hasta", Timestamp.from(hasta));
    }

    private static Instant instante(ResultSet rs, String columna) throws SQLException {
        Timestamp t = rs.getTimestamp(columna);
        return t == null ? null : t.toInstant();
    }

    /** Un número que puede faltar (la mediana sin datos es NULL, no 0). */
    private static Double decimal(ResultSet rs, String columna) throws SQLException {
        double d = rs.getDouble(columna);
        return rs.wasNull() ? null : d;
    }
}
