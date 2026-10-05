package com.insightedulab.backend_java.oci;

import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.sql.Types;
import java.time.Instant;
import java.util.List;

/**
 * SQL de la subida a OCI (T09). Mismo patrón que la generación de T06: reserva con SKIP LOCKED y una columna
 * propia de reserva, y escrituras con guarda (solo se guarda si la subida sigue PENDIENTE).
 * Cada método es UNA sentencia: nada queda con una transacción abierta mientras se espera a OCI.
 */
@Repository
public class SubidaOciRepository {

    public static final String GENERADOS = "generados";
    public static final String APROBADOS = "aprobados";

    /** Una subida reservada: qué borrador y a qué carpeta. */
    public record Subida(long id, long borradorId, String carpeta, int intentos) {}

    // Todo borrador que se revisa en el panel y todavía no tiene su subida a generados/. Las respuestas del bot
    // no son activos: no se aprueban (D3, DEC-66). El ORDER BY hace que dos Java encolen en el mismo orden
    private static final String ENCOLAR_GENERADOS = """
            INSERT INTO subidas_oci (borrador_id, carpeta)
            SELECT b.id, 'generados' FROM borradores b
             WHERE b.tipo <> 'RESPUESTA_BOT'
               AND NOT EXISTS (SELECT 1 FROM subidas_oci s WHERE s.borrador_id = b.id AND s.carpeta = 'generados')
             ORDER BY b.id
            ON CONFLICT (borrador_id, carpeta) DO NOTHING
            """;

    // F11: a aprobados/ solo van los APROBADOS. Un rechazado o uno pendiente nunca
    private static final String ENCOLAR_APROBADOS = """
            INSERT INTO subidas_oci (borrador_id, carpeta)
            SELECT b.id, 'aprobados' FROM borradores b
             WHERE b.tipo <> 'RESPUESTA_BOT' AND b.estado = 'APROBADO'
               AND NOT EXISTS (SELECT 1 FROM subidas_oci s WHERE s.borrador_id = b.id AND s.carpeta = 'aprobados')
             ORDER BY b.id
            ON CONFLICT (borrador_id, carpeta) DO NOTHING
            """;

    private static final String RESERVAR = """
            UPDATE subidas_oci s
               SET reservada_hasta = now() + make_interval(secs => :segundos)
             WHERE s.id IN (
                   SELECT id FROM subidas_oci
                    WHERE estado = 'PENDIENTE' AND (reservada_hasta IS NULL OR reservada_hasta < now())
                    ORDER BY id
                    LIMIT :tanda
                    FOR UPDATE SKIP LOCKED)
            RETURNING s.id, s.borrador_id, s.carpeta, s.intentos
            """;

    // El borrador tal como está ahora. motivo_ia es el de la generación (post y caso) o el de la semana (FAQ),
    // igual que el detalle del panel. No se lee nada del mensaje de Discord salvo ese motivo
    private static final String BORRADOR = """
            SELECT b.id, b.tipo, b.estado, b.texto_ia, b.texto_final, b.consentimiento_confirmado, b.creado_en,
                   b.aprobado_por, b.aprobado_en, b.tiempo_curaduria_seg,
                   CASE WHEN b.mensaje_id IS NULL THEN f.motivo ELSE m.generacion_motivo END AS motivo_ia,
                   f.semana
              FROM borradores b
              LEFT JOIN mensajes m ON m.id = b.mensaje_id
              LEFT JOIN faq_semanas f ON f.borrador_id = b.id
             WHERE b.id = :id
            """;

    private static final String SUBIDO = """
            UPDATE subidas_oci
               SET estado = 'SUBIDO', ruta = :ruta, intentos = intentos + 1, subido_en = now(),
                   reservada_hasta = NULL, ultimo_error = NULL
             WHERE id = :id AND estado = 'PENDIENTE'
            """;

    // En el SET, intentos es el valor de antes de sumar. Al fallar, la subida espera más cada vez (reservada_hasta)
    // antes de volver a tomarse: así una caída corta de OCI no gasta todos los intentos en unos minutos
    private static final String FALLO = """
            UPDATE subidas_oci
               SET intentos = intentos + 1, ultimo_error = :motivo,
                   estado = CASE WHEN intentos + 1 >= :maxIntentos THEN 'ERROR' ELSE 'PENDIENTE' END,
                   reservada_hasta = CASE WHEN intentos + 1 >= :maxIntentos THEN NULL
                                          ELSE now() + make_interval(secs => :espera * (intentos + 1)) END
             WHERE id = :id AND estado = 'PENDIENTE'
            RETURNING estado
            """;

    // Un caso que ningún reintento arregla (por ejemplo, un pendiente en aprobados/): ERROR sin gastar intentos
    private static final String ERROR_DEFINITIVO = """
            UPDATE subidas_oci
               SET estado = 'ERROR', ultimo_error = :motivo, reservada_hasta = NULL
             WHERE id = :id AND estado = 'PENDIENTE'
            """;

    private final NamedParameterJdbcTemplate jdbc;

    public SubidaOciRepository(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** Crea las subidas que faltan: la de generados/ de cada borrador y la de aprobados/ de cada aprobado. */
    public int encolar() {
        MapSqlParameterSource sinParametros = new MapSqlParameterSource();
        return jdbc.update(ENCOLAR_GENERADOS, sinParametros) + jdbc.update(ENCOLAR_APROBADOS, sinParametros);
    }

    public List<Subida> reservar(int tanda, int segundos) {
        MapSqlParameterSource p = new MapSqlParameterSource().addValue("tanda", tanda).addValue("segundos", segundos);
        return jdbc.query(RESERVAR, p, (rs, i) -> new Subida(rs.getLong("id"), rs.getLong("borrador_id"),
                rs.getString("carpeta"), rs.getInt("intentos")));
    }

    /** El borrador con sus datos, o null si ya no existe. */
    public ArchivoOci borrador(long id) {
        List<ArchivoOci> filas = jdbc.query(BORRADOR, new MapSqlParameterSource("id", id), (rs, i) -> new ArchivoOci(
                ArchivoOci.VERSION, rs.getLong("id"), rs.getString("tipo"), rs.getString("estado"),
                rs.getString("texto_ia"), rs.getString("texto_final"), rs.getBoolean("consentimiento_confirmado"),
                instante(rs.getTimestamp("creado_en")), rs.getString("aprobado_por"),
                instante(rs.getTimestamp("aprobado_en")), (Integer) rs.getObject("tiempo_curaduria_seg"),
                rs.getString("motivo_ia"), rs.getString("semana")));
        return filas.isEmpty() ? null : filas.get(0);
    }

    /** true si se anotó; false si ya no estaba PENDIENTE (otra ejecución se adelantó). */
    public boolean subido(long id, String ruta) {
        return jdbc.update(SUBIDO, new MapSqlParameterSource().addValue("id", id).addValue("ruta", ruta)) == 1;
    }

    /** ERROR o PENDIENTE (se reintenta), o null si ya no estaba PENDIENTE. */
    public String fallo(long id, String motivo, int maxIntentos, int esperaSegundos) {
        List<String> estado = jdbc.queryForList(FALLO, new MapSqlParameterSource().addValue("id", id)
                .addValue("motivo", motivo, Types.VARCHAR).addValue("maxIntentos", maxIntentos)
                .addValue("espera", esperaSegundos), String.class);
        return estado.isEmpty() ? null : estado.get(0);
    }

    public void errorDefinitivo(long id, String motivo) {
        jdbc.update(ERROR_DEFINITIVO, new MapSqlParameterSource().addValue("id", id).addValue("motivo", motivo, Types.VARCHAR));
    }

    private static Instant instante(Timestamp t) {
        return t == null ? null : t.toInstant();
    }
}
