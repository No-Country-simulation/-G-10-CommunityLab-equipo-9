package com.insightedulab.backend_java;

import com.insightedulab.backend_java.client.IaNoDisponibleException;
import com.insightedulab.backend_java.client.IaRechazoException;
import com.insightedulab.backend_java.client.NlpDataClient;
import com.insightedulab.backend_java.client.RespuestaGenerar;
import com.insightedulab.backend_java.client.RespuestaIa;
import com.insightedulab.backend_java.generacion.GeneracionRepository;
import com.insightedulab.backend_java.generacion.GeneracionRepository.Logro;
import com.insightedulab.backend_java.generacion.GeneracionService;
import com.insightedulab.backend_java.generacion.GeneracionService.Resumen;
import com.insightedulab.backend_java.model.enums.AutorRol;
import com.insightedulab.backend_java.model.enums.AutorTipo;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository.DatosMensaje;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

import java.time.Instant;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.function.Function;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;

/**
 * Generación de borradores del Agente-Mod (T06) contra PostgreSQL real, con la IA simulada (Mockito).
 * ⚠️ Vacían las tablas: solo corren en una base *_test.
 */
@SpringBootTest(properties = {
        "clasificacion.habilitada=false",
        "generacion.habilitada=false",  // la tarea programada no corre: las pruebas llaman a procesarTanda()
        "generacion.tanda=3",
        "generacion.max-intentos=3",
        "generacion.max-respuestas=20",
})
class GeneracionTest {

    private static final String SERVIDOR = "1554157903701741700";
    private static final String POST = "🎉 Camila empieza su primer trabajo en tecnología… #CommunityLab";
    private static final String CASO = "Situación: … Desafío: … Logro: … En sus palabras: \"me contrataron\" Cierre: …";

    @MockitoBean NlpDataClient ia;
    @Autowired GeneracionService servicio;
    @Autowired GeneracionRepository repo;
    @Autowired MensajeUpsertRepository upsert;
    @Autowired JdbcTemplate jdbc;

    @BeforeEach
    void vaciarTablas() {
        String base = jdbc.queryForObject("SELECT current_database()", String.class);
        assertThat(base).as("Las pruebas solo corren en una base *_test").endsWith("_test");
        jdbc.execute("TRUNCATE borradores, mensajes, lotes_recibidos RESTART IDENTITY CASCADE");
    }

    // ── Caso 1: un TESTIMONIO OK sin generación ──

    @Test
    void unLogroPublicableTieneSusDosBorradoresPendientes() {
        logro("101");
        iaResponde(id -> publicable(id));

        Resumen r = servicio.procesarTanda();

        assertThat(r.tomados()).isEqualTo(1);
        assertThat(r.generados()).isEqualTo(1);
        assertThat(fila("101")).containsEntry("generacion_estado", "GENERADO")
                .containsEntry("generacion_motivo", "Es una contratación.")
                .containsEntry("generacion_intentos", 1).containsEntry("generacion_reservada_hasta", null);
        assertThat(fila("101").get("generado_en")).isNotNull();
        List<Map<String, Object>> borradores = borradores();
        assertThat(borradores).hasSize(2);
        assertThat(borradores.get(0)).containsEntry("tipo", "POST_LINKEDIN").containsEntry("estado", "PENDIENTE")
                .containsEntry("texto_ia", POST).containsEntry("tokens_in", 1450).containsEntry("tokens_out", 520)
                .containsEntry("consentimiento_confirmado", false).containsEntry("discord_id", "101");
        assertThat(borradores.get(1)).containsEntry("tipo", "CASO_EXITO").containsEntry("estado", "PENDIENTE")
                .containsEntry("texto_ia", CASO).containsEntry("tokens_in", 0).containsEntry("tokens_out", 0)
                .containsEntry("discord_id", "101");
    }

    @Test
    void elPedidoLlevaElLogroTalCualSinRespuestas() {
        logro("101");
        iaResponde(id -> publicable(id));

        servicio.procesarTanda();

        Map<String, Object> pedido = pedidoEnviado();
        assertThat(pedido.get("versionContrato")).isEqualTo("1.0");
        assertThat((String) pedido.get("pedidoId")).startsWith("gen-");
        assertThat(pedido.get("logro")).isEqualTo(caja("101", "me contrataron!!! empiezo el lunes como QA trainee", null));
        assertThat((List<?>) pedido.get("respuestas")).isEmpty();
    }

    // ── Caso 2: la IA dice "no publicable" ──

    @Test
    void unLogroNoPublicableTieneMotivoYCeroBorradores() {
        logro("101");
        iaResponde(id -> new RespuestaGenerar("1.0", "gen-x", id, "OK", false,
                "Es un avance de aprendizaje del día a día.", null, null, metricas()));

        Resumen r = servicio.procesarTanda();

        assertThat(r.noPublicables()).isEqualTo(1);
        assertThat(fila("101")).containsEntry("generacion_estado", "NO_PUBLICABLE")
                .containsEntry("generacion_motivo", "Es un avance de aprendizaje del día a día.")
                .containsEntry("generacion_reservada_hasta", null);
        assertThat(borradores()).isEmpty();
    }

    // ── Caso 3: la IA falla ──

    @Test
    void siLaIaFallaSumaIntentosHastaQuedarEnError() {
        logro("101");
        doThrow(new IaNoDisponibleException("La IA respondió HTTP 500")).when(ia).generar(any(), anyString());

        for (int vuelta = 1; vuelta <= 2; vuelta++) {
            assertThat(servicio.procesarTanda().reintento()).isEqualTo(1);
            assertThat(fila("101")).containsEntry("generacion_estado", null).containsEntry("generacion_intentos", vuelta)
                    .containsEntry("generacion_reservada_hasta", null)
                    .containsEntry("generacion_motivo", "La IA respondió HTTP 500");
        }
        assertThat(servicio.procesarTanda().error()).isEqualTo(1);
        assertThat(fila("101")).containsEntry("generacion_estado", "ERROR").containsEntry("generacion_intentos", 3);
        assertThat(borradores()).isEmpty();  // nada a medias
        assertThat(servicio.procesarTanda().tomados()).isZero();  // ERROR es definitivo
    }

    @Test
    void unErrorDelLlmUn422YUnaRespuestaIncoherenteCuentanComoIntento() {
        logro("101");
        logro("102");
        logro("103");
        doAnswer(inv -> {
            String id = discordIdDe(inv.getArgument(0));
            return switch (id) {
                case "101" -> new RespuestaGenerar("1.0", "gen-x", id, "ERROR", null, "El LLM no respondió en 25 s.",
                        null, null, metricas());
                case "102" -> throw new IaRechazoException(List.of());
                default -> new RespuestaGenerar("1.0", "gen-x", id, "OK", true, "sí", POST, "  ", metricas());
            };
        }).when(ia).generar(any(), anyString());

        Resumen r = servicio.procesarTanda();

        assertThat(r.reintento()).isEqualTo(3);
        for (String id : List.of("101", "102", "103")) {
            assertThat(fila(id)).as(id).containsEntry("generacion_estado", null).containsEntry("generacion_intentos", 1)
                    .containsEntry("generacion_reservada_hasta", null);
        }
        assertThat(fila("101").get("generacion_motivo")).isEqualTo("El LLM no respondió en 25 s.");
        assertThat(borradores()).isEmpty();
    }

    // ── Caso 4: dos ejecuciones a la vez ──

    @Test
    void dosReservasAlMismoTiempoNoTomanLosMismosLogros() throws Exception {
        for (int i = 101; i <= 106; i++) {
            logro(String.valueOf(i));
        }
        ExecutorService hilos = Executors.newFixedThreadPool(2);
        CountDownLatch largada = new CountDownLatch(1);
        try {
            Callable<List<Logro>> reservar = () -> {
                largada.await();
                return repo.reservar(3, 180);
            };
            Future<List<Logro>> a = hilos.submit(reservar);
            Future<List<Logro>> b = hilos.submit(reservar);
            largada.countDown();
            Set<String> idsA = ids(a.get());
            Set<String> idsB = ids(b.get());
            assertThat(idsA).doesNotContainAnyElementsOf(idsB);
            Set<String> todos = new HashSet<>(idsA);
            todos.addAll(idsB);
            assertThat(todos).hasSize(6);
        } finally {
            hilos.shutdown();
        }
    }

    @Test
    void unLogroReservadoPorOtraEjecucionNoSeToma() {
        logro("101");
        assertThat(repo.reservar(3, 180)).hasSize(1);  // otra ejecución lo tiene

        assertThat(servicio.procesarTanda().tomados()).isZero();
        verifyNoInteractions(ia);

        jdbc.update("UPDATE mensajes SET generacion_reservada_hasta = now() - interval '1 minute'");  // murió
        iaResponde(id -> publicable(id));
        assertThat(servicio.procesarTanda().generados()).isEqualTo(1);
    }

    // ── Caso 5: el mensaje cambió mientras la IA redactaba ──

    @Test
    void siElMensajeCambioMientrasLaIaRedactabaNoSeGuardaNada() {
        logro("101");
        doAnswer(inv -> {
            // Mientras la IA redacta, el lote de la hora trae el texto editado (vuelve a PENDIENTE)
            upsert.upsert(datos("101", "me contrataron!!! (editado)", null, AutorTipo.persona));
            return publicable("101");
        }).when(ia).generar(any(), anyString());

        Resumen r = servicio.procesarTanda();

        assertThat(r.cambiaron()).isEqualTo(1);
        assertThat(borradores()).isEmpty();
        assertThat(fila("101")).containsEntry("generacion_estado", null).containsEntry("generacion_intentos", 0)
                .containsEntry("generacion_reservada_hasta", null);
    }

    @Test
    void siLoReclasificaronMientrasLaIaRedactabaNoSeGuardaNada() {
        logro("101");
        doAnswer(inv -> {
            jdbc.update("UPDATE mensajes SET intencion = 'COMENTARIO' WHERE discord_id = '101'");
            return publicable("101");
        }).when(ia).generar(any(), anyString());

        assertThat(servicio.procesarTanda().cambiaron()).isEqualTo(1);
        assertThat(borradores()).isEmpty();
    }

    // ── Caso 6: lo que no es un logro de una persona, ya clasificado, no se envía ──

    @Test
    void comentariosDudasBotsYPendientesNoSeEnvian() {
        etiquetado("201", "COMENTARIO", "OK", AutorTipo.persona);
        etiquetado("202", "PREGUNTA_FAQ", "OK", AutorTipo.persona);
        etiquetado("203", "TESTIMONIO", "OK", AutorTipo.botPropio);
        etiquetado("204", "TESTIMONIO", "OK", AutorTipo.otroBot);
        upsert.upsert(datos("205", "me contrataron", null, AutorTipo.persona));  // PENDIENTE, sin etiquetas
        etiquetado("206", "TESTIMONIO", "ERROR", AutorTipo.persona);

        assertThat(servicio.procesarTanda().tomados()).isZero();
        verifyNoInteractions(ia);
    }

    // ── Caso 7: correr la tarea otra vez no duplica ──

    @Test
    void correrLaTareaOtraVezNoDuplicaBorradores() {
        logro("101");
        iaResponde(id -> publicable(id));

        servicio.procesarTanda();
        assertThat(servicio.procesarTanda().tomados()).isZero();
        assertThat(servicio.procesarTanda().tomados()).isZero();

        assertThat(borradores()).hasSize(2);
        verify(ia, times(1)).generar(any(), anyString());
    }

    @Test
    void laV4ImpideDosBorradoresPendientesDelMismoTipo() {
        logro("101");
        iaResponde(id -> publicable(id));
        servicio.procesarTanda();
        long id = jdbc.queryForObject("SELECT id FROM mensajes WHERE discord_id = '101'", Long.class);

        assertThatThrownBy(() -> repo.insertarBorrador(id, "POST_LINKEDIN", "otro", 0, 0))
                .isInstanceOf(DataIntegrityViolationException.class)
                .hasMessageContaining("uq_borradores_pendiente_por_tipo");
        // Uno APROBADO no bloquea: se puede volver a generar en el futuro (T07)
        jdbc.update("UPDATE borradores SET estado = 'APROBADO' WHERE tipo = 'POST_LINKEDIN'");
        repo.insertarBorrador(id, "POST_LINKEDIN", "otro", 0, 0);
        assertThatThrownBy(() -> jdbc.update("UPDATE mensajes SET generacion_estado = 'LISTO'"))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    void siYaHabiaUnBorradorPendienteNoQuedaNadaAMedias() {
        logro("101");
        long id = jdbc.queryForObject("SELECT id FROM mensajes WHERE discord_id = '101'", Long.class);
        repo.insertarBorrador(id, "CASO_EXITO", "uno anterior", 0, 0);  // por ejemplo, cargado a mano
        iaResponde(x -> publicable(x));

        Resumen r = servicio.procesarTanda();

        assertThat(r.error()).isEqualTo(1);
        assertThat(borradores()).hasSize(1);  // el POST de esta vuelta también se deshizo
        assertThat(fila("101")).containsEntry("generacion_estado", null).containsEntry("generacion_reservada_hasta", null);
    }

    // ── Caso 8: un logro con respuestas ──

    @Test
    void lasRespuestasDePersonasViajanEnElPedidoConTope() {
        logro("101");
        for (int i = 0; i < 22; i++) {
            upsert.upsert(datos(String.valueOf(300 + i), "felicitaciones " + i, "101", AutorTipo.persona));
        }
        upsert.upsert(datos("400", "respuesta de un bot", "101", AutorTipo.otroBot));
        upsert.upsert(datos("401", "respuesta a otro mensaje", "999", AutorTipo.persona));
        iaResponde(id -> publicable(id));

        servicio.procesarTanda();

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> respuestas = (List<Map<String, Object>>) pedidoEnviado().get("respuestas");
        assertThat(respuestas).hasSize(20);  // tope
        assertThat(respuestas.get(0)).isEqualTo(caja("300", "felicitaciones 0", "101"));
        assertThat(respuestas).extracting(c -> c.get("id")).doesNotContain("400", "401", "320", "321");
    }

    // ── Ayudas ──

    /** Un TESTIMONIO de una persona, ya clasificado OK. */
    private void logro(String id) {
        etiquetado(id, "TESTIMONIO", "OK", AutorTipo.persona);
    }

    private void etiquetado(String id, String intencion, String estado, AutorTipo tipo) {
        upsert.upsert(datos(id, "me contrataron!!! empiezo el lunes como QA trainee", null, tipo));
        jdbc.update("UPDATE mensajes SET intencion = ?, estado_clasificacion = ?, confianza = 0.9 WHERE discord_id = ?",
                intencion, estado, id);
    }

    private static DatosMensaje datos(String id, String texto, String respondeA, AutorTipo tipo) {
        // La fecha crece con el id: así el orden "más antiguo primero" es 101, 102, ...
        Instant fecha = Instant.parse("2026-09-28T18:56:30.331Z").plusSeconds(Long.parseLong(id));
        return new DatosMensaje(id, "1554158272867467374", "111111111111111111", tipo, AutorRol.miembro,
                false, fecha, respondeA, texto, caja(id, texto, respondeA), "1.0", SERVIDOR);
    }

    private static Map<String, Object> caja(String id, String texto, String respondeA) {
        Map<String, Object> c = new LinkedHashMap<>();
        c.put("id", id);
        c.put("textoOriginal", texto);
        c.put("respondeA", respondeA);
        c.put("autor", Map.of("id", "111111111111111111", "nombreVisible", "Camila Rojas", "tipo", "persona",
                "rol", "miembro"));
        return c;
    }

    private void iaResponde(Function<String, RespuestaGenerar> porId) {
        doAnswer(inv -> porId.apply(discordIdDe(inv.getArgument(0)))).when(ia).generar(any(), anyString());
    }

    @SuppressWarnings("unchecked")
    private static String discordIdDe(Map<String, Object> pedido) {
        return (String) ((Map<String, Object>) pedido.get("logro")).get("id");
    }

    private Map<String, Object> pedidoEnviado() {
        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> pedido = ArgumentCaptor.forClass(Map.class);
        ArgumentCaptor<String> idCorrelacion = ArgumentCaptor.forClass(String.class);
        verify(ia).generar(pedido.capture(), idCorrelacion.capture());
        assertThat(pedido.getValue().get("pedidoId")).isEqualTo(idCorrelacion.getValue());
        return pedido.getValue();
    }

    private static RespuestaGenerar publicable(String id) {
        return new RespuestaGenerar("1.0", "gen-x", id, "OK", true, "Es una contratación.", POST, CASO, metricas());
    }

    private static RespuestaIa.Metricas metricas() {
        return new RespuestaIa.Metricas(6120, 1450, 520);
    }

    private Map<String, Object> fila(String discordId) {
        return jdbc.queryForMap("""
                SELECT generacion_estado, generacion_motivo, generacion_intentos, generado_en, generacion_reservada_hasta
                  FROM mensajes WHERE discord_id = ?""", discordId);
    }

    private List<Map<String, Object>> borradores() {
        return jdbc.queryForList("""
                SELECT m.discord_id, b.tipo, b.estado, b.texto_ia, b.tokens_in, b.tokens_out, b.consentimiento_confirmado
                  FROM borradores b JOIN mensajes m ON m.id = b.mensaje_id
                 ORDER BY b.id""");
    }

    private static Set<String> ids(List<Logro> logros) {
        Set<String> ids = new HashSet<>();
        logros.forEach(l -> ids.add(l.discordId()));
        return ids;
    }
}
