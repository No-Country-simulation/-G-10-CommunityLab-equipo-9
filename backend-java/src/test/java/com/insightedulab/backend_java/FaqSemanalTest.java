package com.insightedulab.backend_java;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightedulab.backend_java.client.IaNoDisponibleException;
import com.insightedulab.backend_java.client.IaRechazoException;
import com.insightedulab.backend_java.client.NlpDataClient;
import com.insightedulab.backend_java.client.RespuestaFaqSemanal;
import com.insightedulab.backend_java.client.RespuestaIa;
import com.insightedulab.backend_java.faqsemanal.FaqSemanalService;
import com.insightedulab.backend_java.faqsemanal.FaqSemanalService.Resultado;
import com.insightedulab.backend_java.model.enums.AutorRol;
import com.insightedulab.backend_java.model.enums.AutorTipo;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository.DatosMensaje;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;

/**
 * FAQ semanal (T06b) contra PostgreSQL real, con la IA simulada (Mockito).
 * ⚠️ Vacían las tablas: solo corren en una base *_test.
 */
@SpringBootTest(properties = {
        "clasificacion.habilitada=false",
        "generacion.habilitada=false",
        "faq.habilitada=false",  // las tareas programadas no corren: las pruebas llaman al servicio
        "faq.zona=America/Bogota",
        "faq.dias=7",
        "faq.max-intentos=3",
})
class FaqSemanalTest {

    private static final String SERVIDOR = "1554157903701741700";
    // Domingo 2026-10-04, 10:00 en Bogotá: semana ISO 40
    private static final Instant AHORA = Instant.parse("2026-10-04T15:00:00Z");
    private static final String TEXTO = "# Preguntas frecuentes de la semana (27/09 al 04/10/2026)\n\n…";

    @MockitoBean NlpDataClient ia;
    @Autowired FaqSemanalService servicio;
    @Autowired MensajeUpsertRepository upsert;
    @Autowired JdbcTemplate jdbc;
    @Autowired ObjectMapper objectMapper;

    private int siguienteId = 100;

    @BeforeEach
    void vaciarTablas() {
        String base = jdbc.queryForObject("SELECT current_database()", String.class);
        assertThat(base).as("Las pruebas solo corren en una base *_test").endsWith("_test");
        jdbc.execute("TRUNCATE faq_semanas, borradores, mensajes, lotes_recibidos RESTART IDENTITY CASCADE");
    }

    // ── Caso 1: una semana con dudas repetidas ──

    @Test
    void unaSemanaConDudasRepetidasTieneUnBorradorFaqPendienteSinMensaje() {
        tresDudasDeTresPersonas();
        iaResponde(conTexto(2, 1));

        Resultado r = servicio.ejecutar(AHORA);

        assertThat(r.semana()).isEqualTo("2026-W40");
        assertThat(r.estado()).isEqualTo("GENERADA");
        assertThat(r.dudas()).isEqualTo(3);
        List<Map<String, Object>> borradores = jdbc.queryForList(
                "SELECT id, mensaje_id, tipo, estado, texto_ia, tokens_in, tokens_out FROM borradores");
        assertThat(borradores).hasSize(1);
        assertThat(borradores.get(0)).containsEntry("mensaje_id", null).containsEntry("tipo", "FAQ")
                .containsEntry("estado", "PENDIENTE").containsEntry("texto_ia", TEXTO.strip())
                .containsEntry("tokens_in", 2210).containsEntry("tokens_out", 240);
        assertThat(semana("2026-W40")).containsEntry("estado", "GENERADA").containsEntry("intentos", 1)
                .containsEntry("dudas", 3).containsEntry("repetidas", 2).containsEntry("con_respuesta", 1)
                .containsEntry("borrador_id", borradores.get(0).get("id")).containsEntry("reservada_hasta", null)
                .containsEntry("motivo", "2 preguntas repetidas, 1 con respuesta en los documentos.");
        assertThat(semana("2026-W40").get("terminada_en")).isNotNull();
    }

    @Test
    void laSemanaSeCuentaEnLaZonaConfigurada() {
        // Domingo 23:30 en Bogotá ya es lunes en UTC: sigue siendo la semana 40
        assertThat(servicio.semanaDe(Instant.parse("2026-10-05T04:30:00Z"))).isEqualTo("2026-W40");
        assertThat(servicio.semanaDe(Instant.parse("2026-10-05T13:00:00Z"))).isEqualTo("2026-W41");
    }

    // ── Caso 2: la tarea corre otra vez en la misma semana ──

    @Test
    void correrOtraVezEnLaMismaSemanaNoCreaUnaSegundaFaq() {
        tresDudasDeTresPersonas();
        iaResponde(conTexto(2, 1));

        servicio.ejecutar(AHORA);
        Resultado otra = servicio.ejecutar(AHORA.plus(Duration.ofHours(5)));

        assertThat(otra.estado()).isEqualTo("OMITIDA");
        assertThat(servicio.reintentar()).isNull();
        verify(ia, times(1)).faq(any(), anyString());
        assertThat(jdbc.queryForObject("SELECT count(*) FROM borradores", Integer.class)).isEqualTo(1);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM faq_semanas", Integer.class)).isEqualTo(1);
    }

    @Test
    void dosEjecucionesALaVezArmanUnaSolaFaq() throws Exception {
        tresDudasDeTresPersonas();
        doAnswer(inv -> {
            Thread.sleep(300);  // mientras la IA trabaja, la otra ejecución encuentra la semana reservada
            return conTexto(2, 1);
        }).when(ia).faq(any(), anyString());
        ExecutorService hilos = Executors.newFixedThreadPool(2);
        CountDownLatch largada = new CountDownLatch(1);
        try {
            Callable<Resultado> correr = () -> {
                largada.await();
                return servicio.ejecutar(AHORA);
            };
            Future<Resultado> a = hilos.submit(correr);
            Future<Resultado> b = hilos.submit(correr);
            largada.countDown();
            assertThat(List.of(a.get().estado(), b.get().estado())).containsExactlyInAnyOrder("GENERADA", "OMITIDA");
        } finally {
            hilos.shutdownNow();
        }
        verify(ia, times(1)).faq(any(), anyString());
        assertThat(jdbc.queryForObject("SELECT count(*) FROM borradores", Integer.class)).isEqualTo(1);
    }

    // ── Caso 3: la IA dice "sin repetidas" ──

    @Test
    void sinRepetidasLaSemanaQuedaRegistradaSinBorradorYSinReintentos() {
        tresDudasDeTresPersonas();
        iaResponde(new RespuestaFaqSemanal("1.0", "faq-x", "2026-W40", "OK", null,
                "No hubo preguntas repetidas por al menos 2 personas.", List.of(), metricas()));

        assertThat(servicio.ejecutar(AHORA).estado()).isEqualTo("SIN_REPETIDAS");

        assertThat(semana("2026-W40")).containsEntry("estado", "SIN_REPETIDAS").containsEntry("borrador_id", null)
                .containsEntry("intentos", 1).containsEntry("repetidas", 0)
                .containsEntry("motivo", "No hubo preguntas repetidas por al menos 2 personas.");
        assertThat(servicio.reintentar()).isNull();
        assertThat(servicio.ejecutar(AHORA.plus(Duration.ofHours(1))).estado()).isEqualTo("OMITIDA");
        verify(ia, times(1)).faq(any(), anyString());
        assertThat(jdbc.queryForObject("SELECT count(*) FROM borradores", Integer.class)).isZero();
    }

    @Test
    void conDudasDeUnaSolaPersonaNoSeLlamaALaIa() {
        duda("a", "¿hasta cuándo es la entrega?", "evaluaciones", AHORA.minus(Duration.ofHours(2)));
        duda("a", "¿hasta cuándo es la entrega? nadie responde", "evaluaciones", AHORA.minus(Duration.ofHours(1)));

        Resultado r = servicio.ejecutar(AHORA);

        assertThat(r.estado()).isEqualTo("SIN_REPETIDAS");
        assertThat(semana("2026-W40")).containsEntry("dudas", 2).containsEntry("borrador_id", null);
        verifyNoInteractions(ia);
    }

    // ── Caso 4: la IA falla ──

    @Test
    void siLaIaFallaSumaIntentosConLaMismaVentanaHastaQuedarEnError() {
        tresDudasDeTresPersonas();
        doThrow(new IaNoDisponibleException("La IA respondió HTTP 500")).when(ia).faq(any(), anyString());

        assertThat(servicio.ejecutar(AHORA).estado()).isEqualTo("REINTENTO");
        assertThat(semana("2026-W40")).containsEntry("estado", null).containsEntry("intentos", 1)
                .containsEntry("reservada_hasta", null).containsEntry("motivo", "La IA respondió HTTP 500");
        assertThat(servicio.reintentar().estado()).isEqualTo("REINTENTO");
        assertThat(servicio.reintentar().estado()).isEqualTo("ERROR");
        assertThat(semana("2026-W40")).containsEntry("estado", "ERROR").containsEntry("intentos", 3);

        assertThat(servicio.reintentar()).isNull();  // ERROR es definitivo
        assertThat(servicio.ejecutar(AHORA.plus(Duration.ofHours(1))).estado()).isEqualTo("OMITIDA");
        assertThat(jdbc.queryForObject("SELECT count(*) FROM borradores", Integer.class)).isZero();

        // Los tres intentos pidieron la misma ventana
        List<Map<String, Object>> pedidos = pedidosEnviados(3);
        assertThat(pedidos).extracting(p -> p.get("desde")).containsOnly("2026-09-27");
        assertThat(pedidos).extracting(p -> p.get("hasta")).containsOnly("2026-10-04");
    }

    @Test
    void unErrorDeLaIaUn422YUnaRespuestaIncoherenteCuentanComoIntento() {
        tresDudasDeTresPersonas();
        doReturn(new RespuestaFaqSemanal("1.0", "faq-x", "2026-W40", "ERROR", null,
                "El LLM no agrupó las dudas en 45 s.", List.of(), metricas()))
                .doThrow(new IaRechazoException(List.of()))
                .doReturn(new RespuestaFaqSemanal("1.0", "faq-x", "2026-W40", "OK", "  ", "x", grupos(1, 1), metricas()))
                .when(ia).faq(any(), anyString());

        assertThat(servicio.ejecutar(AHORA).estado()).isEqualTo("REINTENTO");
        assertThat(semana("2026-W40")).containsEntry("motivo", "El LLM no agrupó las dudas en 45 s.");
        assertThat(servicio.reintentar().estado()).isEqualTo("REINTENTO");
        assertThat(servicio.reintentar().estado()).isEqualTo("ERROR");
        assertThat(semana("2026-W40")).containsEntry("motivo", "La IA respondió texto y grupos que no coinciden.");
        assertThat(jdbc.queryForObject("SELECT count(*) FROM borradores", Integer.class)).isZero();
    }

    // ── Caso 5: lo que no viaja ──

    @Test
    void temaOtroComentariosBotsPendientesYFueraDeLaVentanaNoViajan() {
        duda("a", "¿hasta cuándo es la entrega?", "evaluaciones", AHORA.minus(Duration.ofDays(1)));
        duda("b", "¿cuándo cierra la entrega?", "evaluaciones", AHORA.minus(Duration.ofDays(6)));
        duda("c", "hola, ¿alguien juega fútbol?", "otro", AHORA.minus(Duration.ofHours(1)));
        etiquetado("d", "me encantó la clase", "COMENTARIO", "OK", "contenido_curso", AutorTipo.persona,
                AHORA.minus(Duration.ofHours(1)));
        etiquetado("e", "¿plazo? (bot propio)", "PREGUNTA_FAQ", "OK", "evaluaciones", AutorTipo.botPropio,
                AHORA.minus(Duration.ofHours(1)));
        etiquetado("f", "¿plazo? (otro bot)", "PREGUNTA_FAQ", "OK", "evaluaciones", AutorTipo.otroBot,
                AHORA.minus(Duration.ofHours(1)));
        etiquetado("g", "¿plazo? (sin clasificar)", null, "PENDIENTE", null, AutorTipo.persona,
                AHORA.minus(Duration.ofHours(1)));
        etiquetado("h", "¿plazo? (error)", null, "ERROR", null, AutorTipo.persona, AHORA.minus(Duration.ofHours(1)));
        duda("i", "¿plazo? (hace 8 días)", "evaluaciones", AHORA.minus(Duration.ofDays(8)));
        duda("j", "¿plazo? (después de la ventana)", "evaluaciones", AHORA.plus(Duration.ofMinutes(5)));
        iaResponde(conTexto(1, 0));

        servicio.ejecutar(AHORA);

        assertThat(dudasEnviadas(pedidosEnviados(1).get(0))).extracting(d -> d.get("texto"))
                .containsExactly("¿hasta cuándo es la entrega?", "¿cuándo cierra la entrega?");  // la más nueva primero
    }

    // ── Caso 6: el pedido ──

    @Test
    void elPedidoLlevaLasRespuestasDelBotYClavesOpacasSinNombresNiIds() throws Exception {
        String respondida = duda("a", "como instalo python", "herramientas_entorno", AHORA.minus(Duration.ofHours(3)));
        jdbc.update("""
                UPDATE mensajes SET respuesta_estado = 'RESPONDIDA', respuesta_texto = 'Descarga el instalador.',
                       respuesta_fuentes = '["Guia_Entorno.pdf (Pág. 2)"]'::jsonb WHERE discord_id = ?""", respondida);
        String derivada = duda("b", "python no instala", "herramientas_entorno", AHORA.minus(Duration.ofHours(2)));
        jdbc.update("UPDATE mensajes SET respuesta_estado = 'DERIVADA' WHERE discord_id = ?", derivada);
        duda("a", "y si tengo mac?", "herramientas_entorno", AHORA.minus(Duration.ofHours(1)));
        iaResponde(conTexto(1, 1));

        servicio.ejecutar(AHORA);

        Map<String, Object> pedido = pedidosEnviados(1).get(0);
        assertThat((String) pedido.get("pedidoId")).startsWith("faq-");
        assertThat(pedido).containsEntry("semana", "2026-W40");
        List<Map<String, Object>> dudas = dudasEnviadas(pedido);
        // El autor "a" es siempre la misma clave; "b", otra
        assertThat(dudas).extracting(d -> d.get("autor")).containsExactly("a1", "a2", "a1");
        assertThat(dudas.get(2)).containsEntry("respuesta",
                Map.of("texto", "Descarga el instalador.", "fuentes", List.of("Guia_Entorno.pdf (Pág. 2)")));
        assertThat(dudas.get(1)).containsEntry("respuesta", null);  // DERIVADA: el bot no respondió
        assertThat(dudas.get(0)).containsOnlyKeys("autor", "texto", "tema", "respuesta");

        String json = objectMapper.writeValueAsString(pedido);
        assertThat(json).doesNotContain("Camila", "camila.rojas", autorId("a"), autorId("b"), respondida, derivada,
                "1554158272867467374");
    }

    // ── Ayudas ──

    private void tresDudasDeTresPersonas() {
        duda("a", "¿hasta cuándo se puede entregar el challenge?", "evaluaciones", AHORA.minus(Duration.ofHours(30)));
        duda("b", "cual es la fecha limite de la entrega??", "evaluaciones", AHORA.minus(Duration.ofHours(20)));
        duda("c", "¿dan certificado al terminar?", "inscripciones", AHORA.minus(Duration.ofHours(10)));
    }

    /** Una duda de una persona, ya clasificada OK. Devuelve su discord_id. */
    private String duda(String autor, String texto, String tema, Instant fecha) {
        return etiquetado(autor, texto, "PREGUNTA_FAQ", "OK", tema, AutorTipo.persona, fecha);
    }

    private String etiquetado(String autor, String texto, String intencion, String estado, String tema,
                              AutorTipo tipo, Instant fecha) {
        String id = String.valueOf(1556000000000000000L + siguienteId++);
        Map<String, Object> caja = new LinkedHashMap<>();
        caja.put("id", id);
        caja.put("textoOriginal", texto);
        caja.put("autor", Map.of("id", autorId(autor), "nombreVisible", "Camila Rojas", "nombreUsuario", "camila.rojas",
                "tipo", tipo.name(), "rol", "miembro"));
        upsert.upsert(new DatosMensaje(id, "1554158272867467374", autorId(autor), tipo, AutorRol.miembro, false, fecha,
                null, texto, caja, "1.0", SERVIDOR));
        jdbc.update("UPDATE mensajes SET intencion = ?, estado_clasificacion = ?, tema = ?, confianza = 0.9 WHERE discord_id = ?",
                intencion, estado, tema, id);
        return id;
    }

    private static String autorId(String autor) {
        return "33333333333333333" + (char) ('0' + (autor.charAt(0) - 'a'));
    }

    private void iaResponde(RespuestaFaqSemanal respuesta) {
        doReturn(respuesta).when(ia).faq(any(), anyString());
    }

    private static RespuestaFaqSemanal conTexto(int repetidas, int conRespuesta) {
        return new RespuestaFaqSemanal("1.0", "faq-x", "2026-W40", "OK", TEXTO,
                repetidas + " preguntas repetidas, " + conRespuesta + " con respuesta en los documentos.",
                grupos(repetidas, conRespuesta), metricas());
    }

    private static List<RespuestaFaqSemanal.Grupo> grupos(int repetidas, int conRespuesta) {
        return java.util.stream.IntStream.range(0, repetidas).mapToObj(i -> i < conRespuesta
                ? new RespuestaFaqSemanal.Grupo("¿Pregunta " + i + "?", 2, true, "agenteFaq", List.of("Doc.pdf (Pág. 1)"), null)
                : new RespuestaFaqSemanal.Grupo("¿Pregunta " + i + "?", 2, false, null, List.of(), "Sin respaldo."))
                .toList();
    }

    private static RespuestaIa.Metricas metricas() {
        return new RespuestaIa.Metricas(38250, 2210, 240);
    }

    private List<Map<String, Object>> pedidosEnviados(int veces) {
        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> pedido = ArgumentCaptor.forClass(Map.class);
        ArgumentCaptor<String> idCorrelacion = ArgumentCaptor.forClass(String.class);
        verify(ia, times(veces)).faq(pedido.capture(), idCorrelacion.capture());
        for (int i = 0; i < veces; i++) {
            assertThat(pedido.getAllValues().get(i).get("pedidoId")).isEqualTo(idCorrelacion.getAllValues().get(i));
        }
        return pedido.getAllValues();
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> dudasEnviadas(Map<String, Object> pedido) {
        return (List<Map<String, Object>>) pedido.get("dudas");
    }

    private Map<String, Object> semana(String semana) {
        return jdbc.queryForMap("""
                SELECT estado, motivo, intentos, dudas, repetidas, con_respuesta, borrador_id, reservada_hasta,
                       terminada_en FROM faq_semanas WHERE semana = ?""", semana);
    }
}
