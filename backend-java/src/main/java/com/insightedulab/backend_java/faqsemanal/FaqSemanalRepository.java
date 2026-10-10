package com.insightedulab.backend_java.faqsemanal;

import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.sql.Types;
import java.time.Instant;
import java.util.List;

/**
 * SQL de la FAQ semanal (T06b). Una fila por semana en faq_semanas (V5): la columna semana es única, así que
 * nunca hay dos FAQ de la misma semana. Una reserva con vencimiento evita que dos ejecuciones la armen a la vez.
 */
@Repository
public class FaqSemanalRepository {

    /** Una semana reservada para armar su FAQ. */
    public record Semana(long id, String semana, Instant desde, Instant hasta, int intentos) {}

    /** Una duda de la ventana, con la respuesta del bot si la tiene (respuesta_estado = RESPONDIDA, T05). */
    public record Duda(String autorId, String texto, String tema, String respuestaTexto, String respuestaFuentes) {}

    private static final String CREAR = """
            INSERT INTO faq_semanas (semana, desde, hasta) VALUES (:semana, :desde, :hasta)
            ON CONFLICT (semana) DO NOTHING
            """;

    private static final String RESERVA = "SET reservada_hasta = now() + make_interval(secs => :segundos)";
    private static final String LIBRE = "estado IS NULL AND (reservada_hasta IS NULL OR reservada_hasta < now())";
    private static final String DEVOLVER = " RETURNING id, semana, desde, hasta, intentos";

    // La semana pedida, si todavía no terminó y nadie la está armando. El UPDATE bloquea la fila: si dos
    // ejecuciones llegan a la vez, la segunda vuelve a evaluar el WHERE y ya la encuentra reservada
    private static final String RESERVAR = "UPDATE faq_semanas " + RESERVA
            + " WHERE semana = :semana AND " + LIBRE + DEVOLVER;

    // La semana más antigua que quedó sin terminar: falló y se reintenta, o Java se cayó mientras se armaba
    private static final String RESERVAR_PENDIENTE = "UPDATE faq_semanas " + RESERVA
            + " WHERE id = (SELECT id FROM faq_semanas WHERE " + LIBRE
            + " ORDER BY creada_en, id LIMIT 1 FOR UPDATE SKIP LOCKED)" + DEVOLVER;

    // Las dudas de personas, ya clasificadas, que son del curso (DEC-98). Las más recientes primero.
    // Los textos se recortan a los topes del contrato (§10.2)
    private static final String DUDAS = """
            SELECT autor_id, left(texto, 4000) AS texto, tema,
                   CASE WHEN respuesta_estado = 'RESPONDIDA' AND btrim(coalesce(respuesta_texto, '')) <> ''
                        THEN left(respuesta_texto, 8000) END AS respuesta_texto,
                   CASE WHEN respuesta_estado = 'RESPONDIDA' THEN respuesta_fuentes::text END AS respuesta_fuentes
              FROM mensajes
             WHERE intencion = 'PREGUNTA_FAQ' AND estado_clasificacion = 'OK' AND autor_tipo = 'persona'
               AND tema IS DISTINCT FROM 'otro' AND btrim(texto) <> ''
               AND fecha >= :desde AND fecha < :hasta
             ORDER BY fecha DESC, id DESC
             LIMIT :maximo
            """;

    private static final String INSERTAR_BORRADOR = """
            INSERT INTO borradores (mensaje_id, tipo, texto_ia, estado, tokens_in, tokens_out)
            VALUES (NULL, 'FAQ', :textoIa, 'PENDIENTE', :tokensIn, :tokensOut)
            RETURNING id
            """;

    // La guarda: nadie guardó otro resultado mientras la IA trabajaba
    private static final String TERMINAR = """
            UPDATE faq_semanas
               SET estado = :estado, motivo = :motivo, intentos = intentos + 1, dudas = :dudas,
                   repetidas = :repetidas, con_respuesta = :conRespuesta, borrador_id = :borradorId,
                   terminada_en = now(), reservada_hasta = NULL
             WHERE id = :id AND estado IS NULL
            """;

    // En el SET, intentos es el valor de antes de sumar
    private static final String REGISTRAR_ERROR = """
            UPDATE faq_semanas
               SET intentos = intentos + 1,
                   estado = CASE WHEN intentos + 1 >= :maxIntentos THEN 'ERROR' END,
                   terminada_en = CASE WHEN intentos + 1 >= :maxIntentos THEN now() END,
                   motivo = :motivo, dudas = :dudas, reservada_hasta = NULL
             WHERE id = :id AND estado IS NULL
            RETURNING COALESCE(estado, 'REINTENTO')
            """;

    private final NamedParameterJdbcTemplate jdbc;

    public FaqSemanalRepository(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** Registra la semana si no existe. Si ya existe, no cambia nada (ni su ventana). */
    public void crear(String semana, Instant desde, Instant hasta) {
        jdbc.update(CREAR, new MapSqlParameterSource().addValue("semana", semana)
                .addValue("desde", Timestamp.from(desde)).addValue("hasta", Timestamp.from(hasta)));
    }

    /** La semana, o null si ya terminó (GENERADA, SIN_REPETIDAS o ERROR) o la está armando otra ejecución. */
    public Semana reservar(String semana, int segundos) {
        return una(jdbc.query(RESERVAR, new MapSqlParameterSource().addValue("semana", semana)
                .addValue("segundos", segundos), (rs, i) -> semana(rs)));
    }

    /** La semana más antigua sin terminar y libre, o null. */
    public Semana reservarPendiente(int segundos) {
        return una(jdbc.query(RESERVAR_PENDIENTE, new MapSqlParameterSource("segundos", segundos),
                (rs, i) -> semana(rs)));
    }

    public List<Duda> dudas(Instant desde, Instant hasta, int maximo) {
        MapSqlParameterSource p = new MapSqlParameterSource().addValue("desde", Timestamp.from(desde))
                .addValue("hasta", Timestamp.from(hasta)).addValue("maximo", maximo);
        return jdbc.query(DUDAS, p, (rs, i) -> new Duda(rs.getString("autor_id"), rs.getString("texto"),
                rs.getString("tema"), rs.getString("respuesta_texto"), rs.getString("respuesta_fuentes")));
    }

    public long insertarBorrador(String textoIa, int tokensIn, int tokensOut) {
        Long id = jdbc.queryForObject(INSERTAR_BORRADOR, new MapSqlParameterSource().addValue("textoIa", textoIa)
                .addValue("tokensIn", tokensIn).addValue("tokensOut", tokensOut), Long.class);
        if (id == null) {
            throw new IllegalStateException("El INSERT del borrador FAQ no devolvió su id");
        }
        return id;
    }

    /** GENERADA (con su borrador) o SIN_REPETIDAS. true si se guardó; false si otra ejecución ya la terminó. */
    public boolean terminar(Semana s, String estado, String motivo, int dudas, Integer repetidas, Integer conRespuesta,
                            Long borradorId) {
        return jdbc.update(TERMINAR, new MapSqlParameterSource().addValue("id", s.id()).addValue("estado", estado)
                .addValue("motivo", motivo, Types.VARCHAR).addValue("dudas", dudas)
                .addValue("repetidas", repetidas, Types.INTEGER).addValue("conRespuesta", conRespuesta, Types.INTEGER)
                .addValue("borradorId", borradorId, Types.BIGINT)) == 1;
    }

    /** ERROR o REINTENTO, o null si otra ejecución ya la terminó. */
    public String registrarError(Semana s, String motivo, int dudas, int maxIntentos) {
        List<String> estado = jdbc.queryForList(REGISTRAR_ERROR, new MapSqlParameterSource().addValue("id", s.id())
                .addValue("motivo", motivo, Types.VARCHAR).addValue("dudas", dudas)
                .addValue("maxIntentos", maxIntentos), String.class);
        return estado.isEmpty() ? null : estado.get(0);
    }

    private static Semana semana(java.sql.ResultSet rs) throws java.sql.SQLException {
        return new Semana(rs.getLong("id"), rs.getString("semana"), rs.getTimestamp("desde").toInstant(),
                rs.getTimestamp("hasta").toInstant(), rs.getInt("intentos"));
    }

    private static Semana una(List<Semana> filas) {
        return filas.isEmpty() ? null : filas.get(0);
    }
}
