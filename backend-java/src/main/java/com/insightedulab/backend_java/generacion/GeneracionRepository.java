package com.insightedulab.backend_java.generacion;

import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.Types;
import java.time.OffsetDateTime;
import java.util.List;

/**
 * SQL de la generación de borradores (T06). Mismo patrón que la clasificación de T04: reserva con
 * SKIP LOCKED y una columna propia de reserva, y escrituras que solo se guardan si el mensaje no cambió
 * mientras la IA redactaba (actualizado_en) y sigue siendo un TESTIMONIO OK.
 */
@Repository
public class GeneracionRepository {

    /** Un logro reservado para generar. actualizadoEn es la "foto" del momento de la reserva. */
    public record Logro(long id, String discordId, String versionContrato, String contratoJson,
                        OffsetDateTime actualizadoEn) {}

    // Los logros de personas, ya clasificados, que todavía no tienen generación
    private static final String RESERVAR = """
            UPDATE mensajes m
               SET generacion_reservada_hasta = now() + make_interval(secs => :segundos)
             WHERE m.id IN (
                   SELECT id FROM mensajes
                    WHERE intencion = 'TESTIMONIO'
                      AND estado_clasificacion = 'OK'
                      AND autor_tipo = 'persona'
                      AND generacion_estado IS NULL
                      AND (generacion_reservada_hasta IS NULL OR generacion_reservada_hasta < now())
                    ORDER BY fecha, id
                    LIMIT :tanda
                    FOR UPDATE SKIP LOCKED)
            RETURNING m.id, m.discord_id, m.version_contrato, m.contrato::text AS contrato, m.actualizado_en
            """;

    // Las respuestas de personas al logro (las de bots no aportan), de la más antigua a la más nueva
    private static final String RESPUESTAS = """
            SELECT contrato::text FROM mensajes
             WHERE responde_a = :discordId AND autor_tipo = 'persona'
             ORDER BY fecha, id
             LIMIT :maximo
            """;

    // La guarda: el mensaje no cambió, sigue siendo un TESTIMONIO OK y nadie guardó otro resultado
    private static final String GUARDA = """
             WHERE id = :id AND actualizado_en = :actualizadoEn
               AND intencion = 'TESTIMONIO' AND estado_clasificacion = 'OK' AND generacion_estado IS NULL
            """;

    private static final String MARCAR = """
            UPDATE mensajes
               SET generacion_estado = :estado, generacion_motivo = :motivo,
                   generacion_intentos = generacion_intentos + 1, generado_en = now(),
                   generacion_reservada_hasta = NULL
            """ + GUARDA;

    private static final String INSERTAR_BORRADOR = """
            INSERT INTO borradores (mensaje_id, tipo, texto_ia, estado, tokens_in, tokens_out)
            VALUES (:mensajeId, :tipo, :textoIa, 'PENDIENTE', :tokensIn, :tokensOut)
            """;

    // En el SET, generacion_intentos es el valor de antes de sumar. Sin guarda de TESTIMONIO: si dejó de
    // serlo, sumar un intento no hace daño y la reserva se libera igual
    private static final String REGISTRAR_ERROR = """
            UPDATE mensajes
               SET generacion_intentos = generacion_intentos + 1,
                   generacion_estado = CASE WHEN generacion_intentos + 1 >= :maxIntentos THEN 'ERROR' END,
                   generacion_motivo = :motivo,
                   generacion_reservada_hasta = NULL
             WHERE id = :id AND actualizado_en = :actualizadoEn AND generacion_estado IS NULL
            RETURNING COALESCE(generacion_estado, 'REINTENTO')
            """;

    private static final String LIBERAR = "UPDATE mensajes SET generacion_reservada_hasta = NULL WHERE id = :id";

    private final NamedParameterJdbcTemplate jdbc;

    public GeneracionRepository(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<Logro> reservar(int tanda, int segundos) {
        MapSqlParameterSource p = new MapSqlParameterSource().addValue("tanda", tanda).addValue("segundos", segundos);
        return jdbc.query(RESERVAR, p, (rs, i) -> new Logro(
                rs.getLong("id"), rs.getString("discord_id"), rs.getString("version_contrato"),
                rs.getString("contrato"), rs.getObject("actualizado_en", OffsetDateTime.class)));
    }

    /** Las cajas del contrato v1 de las respuestas al logro. */
    public List<String> respuestas(String discordId, int maximo) {
        MapSqlParameterSource p = new MapSqlParameterSource().addValue("discordId", discordId).addValue("maximo", maximo);
        return jdbc.queryForList(RESPUESTAS, p, String.class);
    }

    /** GENERADO o NO_PUBLICABLE. true si se guardó; false si el mensaje cambió mientras tanto. */
    public boolean marcar(Logro l, String estado, String motivo) {
        return jdbc.update(MARCAR, foto(l).addValue("estado", estado).addValue("motivo", motivo, Types.VARCHAR)) == 1;
    }

    public void insertarBorrador(long mensajeId, String tipo, String textoIa, int tokensIn, int tokensOut) {
        jdbc.update(INSERTAR_BORRADOR, new MapSqlParameterSource()
                .addValue("mensajeId", mensajeId).addValue("tipo", tipo).addValue("textoIa", textoIa)
                .addValue("tokensIn", tokensIn).addValue("tokensOut", tokensOut));
    }

    /** ERROR o REINTENTO, o null si el mensaje cambió mientras tanto. */
    public String registrarError(Logro l, String motivo, int maxIntentos) {
        List<String> estado = jdbc.queryForList(REGISTRAR_ERROR,
                foto(l).addValue("motivo", motivo, Types.VARCHAR).addValue("maxIntentos", maxIntentos), String.class);
        return estado.isEmpty() ? null : estado.get(0);
    }

    public void liberar(Logro l) {
        jdbc.update(LIBERAR, new MapSqlParameterSource("id", l.id()));
    }

    private static MapSqlParameterSource foto(Logro l) {
        return new MapSqlParameterSource().addValue("id", l.id()).addValue("actualizadoEn", l.actualizadoEn());
    }
}
