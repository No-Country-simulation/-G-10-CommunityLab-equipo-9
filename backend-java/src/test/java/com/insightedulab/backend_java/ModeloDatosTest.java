package com.insightedulab.backend_java;

import com.insightedulab.backend_java.model.Borrador;
import com.insightedulab.backend_java.model.LoteRecibido;
import com.insightedulab.backend_java.model.Mensaje;
import com.insightedulab.backend_java.model.enums.*;
import com.insightedulab.backend_java.repository.BorradorRepository;
import com.insightedulab.backend_java.repository.LoteRecibidoRepository;
import com.insightedulab.backend_java.repository.MensajeRepository;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository.DatosMensaje;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository.Resultado;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;

import java.time.Instant;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Pruebas del modelo de datos (T01) contra PostgreSQL real: jsonb y ON CONFLICT no existen en H2.
 * Usan la base que digan POSTGRES_HOST / POSTGRES_DB (ver docs/OPERACION.md §5).
 * ⚠️ Vacían las tablas antes de cada prueba: nunca correrlas contra la base principal.
 */
@SpringBootTest(properties = {"clasificacion.habilitada=false", "generacion.habilitada=false", "faq.habilitada=false"})  // que la tarea programada no tome sus mensajes
class ModeloDatosTest {

    private static final String DISCORD_ID = "1554205393054466139";
    private static final Instant FECHA = Instant.parse("2026-09-28T18:56:30.331Z");

    @Autowired JdbcTemplate jdbc;
    @Autowired MensajeUpsertRepository upsertRepo;
    @Autowired MensajeRepository mensajeRepo;
    @Autowired BorradorRepository borradorRepo;
    @Autowired LoteRecibidoRepository loteRepo;

    @BeforeEach
    void vaciarTablas() {
        // Freno de seguridad: si falta -e POSTGRES_DB=insightedu_test, no vaciar la base principal
        String base = jdbc.queryForObject("SELECT current_database()", String.class);
        assertThat(base).as("Las pruebas solo corren en una base *_test").endsWith("_test");
        jdbc.execute("TRUNCATE borradores, mensajes, lotes_recibidos RESTART IDENTITY CASCADE");
    }

    // ── Caso 1: Flyway aplicó V1 y la aplicación arrancó con ddl-auto=validate ──

    @Test
    void flywayAplicoV1ConTablasEIndices() {
        Integer v1 = jdbc.queryForObject(
                "SELECT count(*) FROM flyway_schema_history WHERE version = '1' AND success", Integer.class);
        assertThat(v1).isEqualTo(1);

        List<String> indices = jdbc.queryForList(
                "SELECT indexname FROM pg_indexes WHERE schemaname = current_schema()", String.class);
        assertThat(indices).contains(
                "idx_mensajes_autor_fecha", "idx_mensajes_fecha", "idx_mensajes_intencion", "idx_borradores_estado");
    }

    // ── Caso 2: mensaje nuevo ──

    @Test
    void mensajeNuevoCreaUnaFila() {
        Resultado r = upsertRepo.upsert(datos("me contrataron!!!", 1));

        assertThat(r).isEqualTo(Resultado.NUEVO);
        assertThat(mensajeRepo.count()).isEqualTo(1);
        Mensaje m = mensajeRepo.findByDiscordId(DISCORD_ID).orElseThrow();
        assertThat(m.getAutorTipo()).isEqualTo(AutorTipo.persona);
        assertThat(m.getEstadoClasificacion()).isEqualTo(EstadoClasificacion.PENDIENTE);
        assertThat(m.getFecha()).isEqualTo(FECHA);
    }

    // ── Caso 3: mismo discord_id con más reacciones ──

    @Test
    void reenvioConMasReaccionesActualizaLaCaja() {
        upsertRepo.upsert(datos("me contrataron!!!", 1));

        Resultado r = upsertRepo.upsert(datos("me contrataron!!!", 5));

        assertThat(r).isEqualTo(Resultado.ACTUALIZADO);
        assertThat(mensajeRepo.count()).isEqualTo(1);
        Mensaje m = mensajeRepo.findByDiscordId(DISCORD_ID).orElseThrow();
        assertThat(cantidadDeReacciones(m)).isEqualTo(5);
    }

    @Test
    void reenvioIdenticoNoReescribeLaFila() {
        upsertRepo.upsert(datos("me contrataron!!!", 1));

        Resultado r = upsertRepo.upsert(datos("me contrataron!!!", 1));

        assertThat(r).isEqualTo(Resultado.SIN_CAMBIOS);
        assertThat(mensajeRepo.count()).isEqualTo(1);
    }

    // ── Caso 4: las etiquetas de la IA sobreviven al reenvío (F2) ──

    @Test
    void reenvioNoPisaLasEtiquetasDeLaIa() {
        upsertRepo.upsert(datos("me contrataron!!!", 1));
        etiquetar();

        upsertRepo.upsert(datos("me contrataron!!!", 7));

        Mensaje m = mensajeRepo.findByDiscordId(DISCORD_ID).orElseThrow();
        assertThat(cantidadDeReacciones(m)).isEqualTo(7);
        assertThat(m.getIntencion()).isEqualTo(Intencion.TESTIMONIO);
        assertThat(m.getConfianza()).isEqualTo(0.92);
        assertThat(m.getSentimiento()).isEqualTo("POSITIVO");
        assertThat(m.getTema()).isEqualTo("empleo");
        assertThat(m.getEstadoClasificacion()).isEqualTo(EstadoClasificacion.OK);
        assertThat(m.getClasificadoEn()).isNotNull();
    }

    // ── Caso 5: si el texto cambió, hay que volver a clasificar ──

    @Test
    void textoCambiadoVuelveAPendiente() {
        upsertRepo.upsert(datos("me contrataron!!!", 1));
        etiquetar();

        Resultado r = upsertRepo.upsert(datos("me contrataron!!! empiezo el lunes", 1));

        assertThat(r).isEqualTo(Resultado.ACTUALIZADO);
        Mensaje m = mensajeRepo.findByDiscordId(DISCORD_ID).orElseThrow();
        assertThat(m.getTexto()).isEqualTo("me contrataron!!! empiezo el lunes");
        assertThat(m.getEstadoClasificacion()).isEqualTo(EstadoClasificacion.PENDIENTE);
        assertThat(m.getIntencion()).isEqualTo(Intencion.TESTIMONIO);  // se conserva hasta reclasificar
    }

    // ── Caso 6: los CHECK rechazan valores fuera de la lista ──

    @Test
    void checkRechazaEstadoDeBorradorInventado() {
        upsertRepo.upsert(datos("me contrataron!!!", 1));
        Long mensajeId = mensajeRepo.findByDiscordId(DISCORD_ID).orElseThrow().getId();

        assertThatThrownBy(() -> jdbc.update(
                "INSERT INTO borradores (mensaje_id, tipo, texto_ia, estado) VALUES (?, 'POST_LINKEDIN', 'x', 'PUBLICADO')",
                mensajeId))
                .isInstanceOf(DataIntegrityViolationException.class)
                .hasMessageContaining("borradores_estado_check");
    }

    @Test
    void checkRechazaTipoDeAutorFueraDelContrato() {
        assertThatThrownBy(() -> jdbc.update("""
                INSERT INTO mensajes (discord_id, canal_id, autor_id, autor_tipo, autor_rol, fecha, contrato, version_contrato)
                VALUES ('1', 'c', 'a', 'HUMANO', 'miembro', now(), '{}', '1.0')"""))
                .isInstanceOf(DataIntegrityViolationException.class)
                .hasMessageContaining("mensajes_autor_tipo_check");
    }

    @Test
    void checkExigeMensajeSalvoEnFaq() {
        assertThatThrownBy(() -> jdbc.update(
                "INSERT INTO borradores (tipo, texto_ia) VALUES ('POST_LINKEDIN', 'x')"))
                .isInstanceOf(DataIntegrityViolationException.class);

        jdbc.update("INSERT INTO borradores (tipo, texto_ia) VALUES ('FAQ', 'Preguntas de la semana')");
        assertThat(borradorRepo.count()).isEqualTo(1);
    }

    // ── Las entidades JPA leen y escriben las tablas de V1 ──

    @Test
    void entidadesSeGuardanConJpa() {
        upsertRepo.upsert(datos("me contrataron!!!", 1));
        Mensaje m = mensajeRepo.findByDiscordId(DISCORD_ID).orElseThrow();

        borradorRepo.save(Borrador.builder()
                .mensaje(m)
                .tipo(TipoBorrador.POST_LINKEDIN)
                .textoIa("¡Felicitaciones, Camila!")
                .build());
        loteRepo.save(LoteRecibido.builder()
                .loteId("3f2b8c1e-0d4a-4b7e-9a51-6c2f0e8d9b10")
                .modo(ModoLote.historial)
                .versionContrato("1.0")
                .total(1).nuevos(1)
                .build());

        assertThat(borradorRepo.findByEstado(EstadoBorrador.PENDIENTE)).hasSize(1);
        LoteRecibido lote = loteRepo.findByLoteId("3f2b8c1e-0d4a-4b7e-9a51-6c2f0e8d9b10").orElseThrow();
        assertThat(lote.getModo()).isEqualTo(ModoLote.historial);
        assertThat(lote.getActualizados()).isZero();
    }

    // ── Ayudas ──

    /** Un logro del canal #logros, como en CONTRACT.md §7, con la cantidad de 🎉 que se pida. */
    private static DatosMensaje datos(String texto, int reacciones) {
        Map<String, Object> contrato = Map.of(
                "id", DISCORD_ID,
                "canal", Map.of("id", "1554158272867467374", "nombre", "logros"),
                "fecha", "2026-09-28T18:56:30.331Z",
                "autor", Map.of("id", "sim-camila-rojas", "tipo", "persona", "rol", "miembro"),
                "textoOriginal", texto,
                "esSimulado", true,
                "reacciones", List.of(Map.of("emoji", "🎉", "cantidad", reacciones)));
        return new DatosMensaje(DISCORD_ID, "1554158272867467374", "sim-camila-rojas",
                AutorTipo.persona, AutorRol.miembro, true, FECHA, null, texto, contrato, "1.0",
                "1554157903701741700");
    }

    /** Simula lo que hará la IA (T04): guardar sus etiquetas. */
    private void etiquetar() {
        jdbc.update("""
                UPDATE mensajes SET intencion = 'TESTIMONIO', confianza = 0.92, sentimiento = 'POSITIVO',
                       tema = 'empleo', estado_clasificacion = 'OK', clasificado_en = now()
                WHERE discord_id = ?""", DISCORD_ID);
    }

    @SuppressWarnings("unchecked")
    private static int cantidadDeReacciones(Mensaje m) {
        List<Map<String, Object>> reacciones = (List<Map<String, Object>>) m.getContrato().get("reacciones");
        return ((Number) reacciones.get(0).get("cantidad")).intValue();
    }
}
