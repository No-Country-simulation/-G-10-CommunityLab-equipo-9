package com.insightedulab.backend_java.curaduria;

import com.insightedulab.backend_java.curaduria.VistasPanel.DetalleBorrador;
import com.insightedulab.backend_java.curaduria.VistasPanel.MensajeEnError;
import com.insightedulab.backend_java.curaduria.VistasPanel.Origen;
import com.insightedulab.backend_java.curaduria.VistasPanel.ResumenBorrador;
import com.insightedulab.backend_java.curaduria.VistasPanel.SemanaFaq;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.sql.Types;
import java.time.Instant;
import java.util.List;

/**
 * SQL del panel de curaduría (T07). Cada cambio es UNA sentencia con la guarda "AND estado = 'PENDIENTE'"
 * (o "= 'ERROR'" al reintentar): si dos personas aprueban a la vez, PostgreSQL bloquea la fila, la segunda
 * vuelve a evaluar el WHERE, ya no la encuentra PENDIENTE y no cambia nada. Así gana siempre la primera.
 */
@Repository
public class CuraduriaRepository {

    /** El tipo y el estado de un borrador, para decidir entre 404, 409 y 422 antes de cambiarlo. */
    public record Estado(String tipo, String estado) {}

    // El nombre visible y el canal vienen de la caja del contrato v1; si faltan, el nombre de usuario o los ids
    private static final String AUTOR = """
            coalesce(nullif(m.contrato->'autor'->>'nombreVisible', ''), m.contrato->'autor'->>'nombreUsuario',
                     m.autor_id)""";
    private static final String CANAL = "coalesce(m.contrato->'canal'->>'nombre', m.canal_id)";

    // RESPUESTA_BOT queda afuera: lo que responde el bot no se aprueba (D3, DEC-66)
    private static final String LISTAR = """
            SELECT b.id, b.tipo, b.estado, b.creado_en, left(coalesce(b.texto_final, b.texto_ia), 160) AS extracto,
                   %s AS autor_nombre, %s AS canal, f.semana,
                   CASE b.estado WHEN 'APROBADO' THEN b.aprobado_por WHEN 'RECHAZADO' THEN b.rechazado_por END
                       AS revisado_por,
                   CASE b.estado WHEN 'APROBADO' THEN b.aprobado_en WHEN 'RECHAZADO' THEN b.rechazado_en END
                       AS revisado_en
              FROM borradores b
              LEFT JOIN mensajes m ON m.id = b.mensaje_id
              LEFT JOIN faq_semanas f ON f.borrador_id = b.id
             WHERE b.estado = :estado AND b.tipo <> 'RESPUESTA_BOT'
               AND (CAST(:tipo AS text) IS NULL OR b.tipo = CAST(:tipo AS text))
            """.formatted(AUTOR, CANAL);
    // Lo pendiente, del más antiguo al más nuevo (se atiende en orden); lo revisado, lo último primero
    private static final String ORDEN_PENDIENTES = " ORDER BY b.creado_en, b.id LIMIT :limite";
    private static final String ORDEN_REVISADOS = " ORDER BY revisado_en DESC NULLS LAST, b.id DESC LIMIT :limite";

    private static final String DETALLE = """
            SELECT b.id, b.tipo, b.estado, b.texto_ia, b.texto_final, b.consentimiento_confirmado, b.creado_en,
                   b.aprobado_por, b.aprobado_en, b.tiempo_curaduria_seg, b.rechazado_por, b.rechazado_en,
                   b.motivo_rechazo, m.id AS mensaje_id, m.discord_id, m.fecha AS mensaje_fecha,
                   m.texto AS mensaje_texto, m.generacion_motivo, %s AS autor_nombre, %s AS canal,
                   f.semana, f.desde, f.hasta, f.motivo AS faq_motivo
              FROM borradores b
              LEFT JOIN mensajes m ON m.id = b.mensaje_id
              LEFT JOIN faq_semanas f ON f.borrador_id = b.id
             WHERE b.id = :id AND b.tipo <> 'RESPUESTA_BOT'
            """.formatted(AUTOR, CANAL);

    private static final String ESTADO =
            "SELECT tipo, estado FROM borradores WHERE id = :id AND tipo <> 'RESPUESTA_BOT'";

    private static final String EDITAR = """
            UPDATE borradores SET texto_final = :textoFinal
             WHERE id = :id AND estado = 'PENDIENTE'
            """;

    // D6 también en el WHERE: aunque Java se equivocara antes, un post sin consentimiento no se aprueba
    // (y la V6 lo impide en la base). Sin edición, texto_final queda igual a texto_ia
    private static final String APROBAR = """
            UPDATE borradores
               SET estado = 'APROBADO', texto_final = coalesce(:textoFinal, texto_final, texto_ia),
                   consentimiento_confirmado = :consentimiento, aprobado_por = :usuario, aprobado_en = now(),
                   tiempo_curaduria_seg = :tiempo
             WHERE id = :id AND estado = 'PENDIENTE' AND (tipo = 'FAQ' OR CAST(:consentimiento AS boolean))
            """;

    private static final String RECHAZAR = """
            UPDATE borradores
               SET estado = 'RECHAZADO', rechazado_por = :usuario, rechazado_en = now(),
                   motivo_rechazo = :motivo, tiempo_curaduria_seg = :tiempo
             WHERE id = :id AND estado = 'PENDIENTE'
            """;

    private static final String ERRORES_CLASIFICACION = """
            SELECT m.id, m.discord_id, %s AS canal, m.fecha, %s AS autor_nombre, left(m.texto, 160) AS extracto,
                   m.intentos_clasificacion AS intentos, NULL AS motivo
              FROM mensajes m
             WHERE m.estado_clasificacion = 'ERROR'
             ORDER BY m.fecha DESC, m.id DESC
             LIMIT :limite
            """.formatted(CANAL, AUTOR);

    private static final String ERRORES_GENERACION = """
            SELECT m.id, m.discord_id, %s AS canal, m.fecha, %s AS autor_nombre, left(m.texto, 160) AS extracto,
                   m.generacion_intentos AS intentos, m.generacion_motivo AS motivo
              FROM mensajes m
             WHERE m.generacion_estado = 'ERROR'
             ORDER BY m.fecha DESC, m.id DESC
             LIMIT :limite
            """.formatted(CANAL, AUTOR);

    // Vuelve a la cola de T04: la clasificación en segundo plano lo toma en su vuelta siguiente
    private static final String REINTENTAR_CLASIFICACION = """
            UPDATE mensajes
               SET estado_clasificacion = 'PENDIENTE', intentos_clasificacion = 0, reservado_hasta = NULL
             WHERE id = :id AND estado_clasificacion = 'ERROR'
            """;

    // Vuelve a "sin generar": la generación de T06 lo toma en su vuelta siguiente
    private static final String REINTENTAR_GENERACION = """
            UPDATE mensajes
               SET generacion_estado = NULL, generacion_intentos = 0, generacion_motivo = NULL,
                   generacion_reservada_hasta = NULL
             WHERE id = :id AND generacion_estado = 'ERROR'
            """;

    private static final String EXISTE_MENSAJE = "SELECT count(*) FROM mensajes WHERE id = :id";

    private final NamedParameterJdbcTemplate jdbc;

    public CuraduriaRepository(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<ResumenBorrador> listar(String estado, String tipo, int limite) {
        String sql = LISTAR + ("PENDIENTE".equals(estado) ? ORDEN_PENDIENTES : ORDEN_REVISADOS);
        MapSqlParameterSource p = new MapSqlParameterSource().addValue("estado", estado)
                .addValue("tipo", tipo, Types.VARCHAR).addValue("limite", limite);
        return jdbc.query(sql, p, (rs, i) -> new ResumenBorrador(rs.getLong("id"), rs.getString("tipo"),
                rs.getString("estado"), instante(rs, "creado_en"), rs.getString("extracto"),
                rs.getString("autor_nombre"), rs.getString("canal"), rs.getString("semana"),
                rs.getString("revisado_por"), instante(rs, "revisado_en")));
    }

    /** El borrador con su contexto, o null si no existe. */
    public DetalleBorrador detalle(long id) {
        List<DetalleBorrador> filas = jdbc.query(DETALLE, new MapSqlParameterSource("id", id), (rs, i) -> {
            String tipo = rs.getString("tipo");
            boolean tieneMensaje = rs.getObject("mensaje_id") != null;
            Origen origen = tieneMensaje ? new Origen(rs.getString("discord_id"), rs.getString("canal"),
                    instante(rs, "mensaje_fecha"), rs.getString("mensaje_texto"), rs.getString("autor_nombre")) : null;
            SemanaFaq faq = rs.getString("semana") != null ? new SemanaFaq(rs.getString("semana"),
                    instante(rs, "desde"), instante(rs, "hasta"), rs.getString("faq_motivo")) : null;
            String motivoIa = tieneMensaje ? rs.getString("generacion_motivo") : rs.getString("faq_motivo");
            return new DetalleBorrador(rs.getLong("id"), tipo, rs.getString("estado"), requiereConsentimiento(tipo),
                    rs.getString("texto_ia"), rs.getString("texto_final"), rs.getBoolean("consentimiento_confirmado"),
                    instante(rs, "creado_en"), rs.getString("aprobado_por"), instante(rs, "aprobado_en"),
                    (Integer) rs.getObject("tiempo_curaduria_seg"), rs.getString("rechazado_por"),
                    instante(rs, "rechazado_en"), rs.getString("motivo_rechazo"), motivoIa, origen, faq);
        });
        return filas.isEmpty() ? null : filas.get(0);
    }

    /** El tipo y el estado, o null si el borrador no existe. */
    public Estado estado(long id) {
        List<Estado> filas = jdbc.query(ESTADO, new MapSqlParameterSource("id", id),
                (rs, i) -> new Estado(rs.getString("tipo"), rs.getString("estado")));
        return filas.isEmpty() ? null : filas.get(0);
    }

    /** true si se guardó; false si ya no estaba PENDIENTE. */
    public boolean editar(long id, String textoFinal) {
        return jdbc.update(EDITAR, new MapSqlParameterSource().addValue("id", id)
                .addValue("textoFinal", textoFinal)) == 1;
    }

    /** true si se aprobó; false si ya no estaba PENDIENTE (otra persona ganó) o falta el consentimiento. */
    public boolean aprobar(long id, String usuario, boolean consentimiento, int tiempo, String textoFinal) {
        return jdbc.update(APROBAR, new MapSqlParameterSource().addValue("id", id).addValue("usuario", usuario)
                .addValue("consentimiento", consentimiento).addValue("tiempo", tiempo)
                .addValue("textoFinal", textoFinal, Types.VARCHAR)) == 1;
    }

    /** true si se rechazó; false si ya no estaba PENDIENTE. */
    public boolean rechazar(long id, String usuario, String motivo, Integer tiempo) {
        return jdbc.update(RECHAZAR, new MapSqlParameterSource().addValue("id", id).addValue("usuario", usuario)
                .addValue("motivo", motivo, Types.VARCHAR).addValue("tiempo", tiempo, Types.INTEGER)) == 1;
    }

    public List<MensajeEnError> erroresClasificacion(int limite) {
        return jdbc.query(ERRORES_CLASIFICACION, new MapSqlParameterSource("limite", limite), (rs, i) -> enError(rs));
    }

    public List<MensajeEnError> erroresGeneracion(int limite) {
        return jdbc.query(ERRORES_GENERACION, new MapSqlParameterSource("limite", limite), (rs, i) -> enError(rs));
    }

    /** true si volvió a la cola; false si ya no estaba en ERROR. */
    public boolean reintentarClasificacion(long mensajeId) {
        return jdbc.update(REINTENTAR_CLASIFICACION, new MapSqlParameterSource("id", mensajeId)) == 1;
    }

    /** true si volvió a la cola; false si ya no estaba en ERROR. */
    public boolean reintentarGeneracion(long mensajeId) {
        return jdbc.update(REINTENTAR_GENERACION, new MapSqlParameterSource("id", mensajeId)) == 1;
    }

    public boolean existeMensaje(long mensajeId) {
        Long n = jdbc.queryForObject(EXISTE_MENSAJE, new MapSqlParameterSource("id", mensajeId), Long.class);
        return n != null && n > 0;
    }

    /** D6: el post y el caso de éxito nombran al alumno. La FAQ no (DEC-100). */
    public static boolean requiereConsentimiento(String tipo) {
        return "POST_LINKEDIN".equals(tipo) || "CASO_EXITO".equals(tipo);
    }

    private static MensajeEnError enError(ResultSet rs) throws SQLException {
        return new MensajeEnError(rs.getLong("id"), rs.getString("discord_id"), rs.getString("canal"),
                instante(rs, "fecha"), rs.getString("autor_nombre"), rs.getString("extracto"),
                rs.getInt("intentos"), rs.getString("motivo"));
    }

    private static Instant instante(ResultSet rs, String columna) throws SQLException {
        Timestamp t = rs.getTimestamp(columna);
        return t == null ? null : t.toInstant();
    }
}
