package com.insightedulab.backend_java.repository;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightedulab.backend_java.model.enums.AutorRol;
import com.insightedulab.backend_java.model.enums.AutorTipo;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;

/**
 * "Actualizar o insertar" un mensaje por su discord_id, en una sola sentencia de PostgreSQL.
 *
 * <ul>
 *   <li>F1: la columna única discord_id impide duplicados.</li>
 *   <li>F2: solo se actualizan los campos del mensaje; las etiquetas de la IA no se tocan.
 *       Si el texto cambió, estado_clasificacion vuelve a PENDIENTE para reclasificarlo.</li>
 *   <li>F3: ON CONFLICT resuelve que el bot y el lote de la hora escriban el mismo mensaje a la vez.</li>
 * </ul>
 *
 * Se escribe en SQL porque JPA (save) no sabe hacer ON CONFLICT.
 */
@Repository
public class MensajeUpsertRepository {

    /** Lo que sale del contrato v1 para un mensaje: la etiqueta (columnas) más la caja completa. */
    public record DatosMensaje(
            String discordId,
            String canalId,
            String autorId,
            AutorTipo autorTipo,
            AutorRol autorRol,
            boolean esSimulado,
            Instant fecha,
            String respondeA,
            String texto,
            Map<String, Object> contrato,
            String versionContrato
    ) {}

    public enum Resultado {
        NUEVO,
        ACTUALIZADO,
        SIN_CAMBIOS  // llegó idéntico a lo guardado: no se reescribe la fila
    }

    // xmax = 0 solo en una fila recién insertada; en una fila actualizada por ON CONFLICT es distinto de 0.
    // Si nada cambió, el WHERE del DO UPDATE no actualiza y RETURNING no devuelve filas.
    private static final String SQL = """
            INSERT INTO mensajes (discord_id, canal_id, autor_id, autor_tipo, autor_rol, es_simulado,
                                  fecha, responde_a, texto, contrato, version_contrato)
            VALUES (:discordId, :canalId, :autorId, :autorTipo, :autorRol, :esSimulado,
                    :fecha, :respondeA, :texto, CAST(:contrato AS jsonb), :versionContrato)
            ON CONFLICT (discord_id) DO UPDATE SET
                canal_id             = EXCLUDED.canal_id,
                autor_id             = EXCLUDED.autor_id,
                autor_tipo           = EXCLUDED.autor_tipo,
                autor_rol            = EXCLUDED.autor_rol,
                es_simulado          = EXCLUDED.es_simulado,
                fecha                = EXCLUDED.fecha,
                responde_a           = EXCLUDED.responde_a,
                texto                = EXCLUDED.texto,
                contrato             = EXCLUDED.contrato,
                version_contrato     = EXCLUDED.version_contrato,
                actualizado_en       = now(),
                estado_clasificacion = CASE
                    WHEN mensajes.texto IS DISTINCT FROM EXCLUDED.texto THEN 'PENDIENTE'
                    ELSE mensajes.estado_clasificacion
                END
            WHERE (mensajes.canal_id, mensajes.autor_id, mensajes.autor_tipo, mensajes.autor_rol,
                   mensajes.es_simulado, mensajes.fecha, mensajes.responde_a, mensajes.texto,
                   mensajes.contrato, mensajes.version_contrato)
                  IS DISTINCT FROM
                  (EXCLUDED.canal_id, EXCLUDED.autor_id, EXCLUDED.autor_tipo, EXCLUDED.autor_rol,
                   EXCLUDED.es_simulado, EXCLUDED.fecha, EXCLUDED.responde_a, EXCLUDED.texto,
                   EXCLUDED.contrato, EXCLUDED.version_contrato)
            RETURNING (xmax = 0) AS insertado
            """;

    private final NamedParameterJdbcTemplate jdbc;
    private final ObjectMapper objectMapper;

    public MensajeUpsertRepository(NamedParameterJdbcTemplate jdbc, ObjectMapper objectMapper) {
        this.jdbc = jdbc;
        this.objectMapper = objectMapper;
    }

    public Resultado upsert(DatosMensaje m) {
        MapSqlParameterSource params = new MapSqlParameterSource()
                .addValue("discordId", m.discordId())
                .addValue("canalId", m.canalId())
                .addValue("autorId", m.autorId())
                .addValue("autorTipo", m.autorTipo().name())
                .addValue("autorRol", m.autorRol().name())
                .addValue("esSimulado", m.esSimulado())
                // El driver de PostgreSQL no acepta Instant; OffsetDateTime en UTC sí
                .addValue("fecha", m.fecha().atOffset(ZoneOffset.UTC))
                .addValue("respondeA", m.respondeA())
                .addValue("texto", m.texto() == null ? "" : m.texto())
                .addValue("contrato", aJson(m.contrato()))
                .addValue("versionContrato", m.versionContrato());

        List<Boolean> filas = jdbc.query(SQL, params, (rs, i) -> rs.getBoolean("insertado"));
        if (filas.isEmpty()) {
            return Resultado.SIN_CAMBIOS;
        }
        return filas.get(0) ? Resultado.NUEVO : Resultado.ACTUALIZADO;
    }

    private String aJson(Map<String, Object> contrato) {
        try {
            return objectMapper.writeValueAsString(contrato);
        } catch (JsonProcessingException e) {
            throw new IllegalArgumentException("La caja del contrato no se pudo convertir a JSON", e);
        }
    }
}
