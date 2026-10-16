package com.insightedulab.backend_java;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightedulab.backend_java.clasificacion.ClasificacionService;
import com.insightedulab.backend_java.client.NlpDataClient;
import com.insightedulab.backend_java.client.RespuestaFaqSemanal;
import com.insightedulab.backend_java.client.RespuestaGenerar;
import com.insightedulab.backend_java.client.RespuestaIa;
import com.insightedulab.backend_java.controller.BorradorController;
import com.insightedulab.backend_java.controller.ErroresController;
import com.insightedulab.backend_java.curaduria.CuraduriaRepository;
import com.insightedulab.backend_java.curaduria.CuraduriaService;
import com.insightedulab.backend_java.curaduria.VistasPanel.PedidoAprobar;
import com.insightedulab.backend_java.error.ConflictoException;
import com.insightedulab.backend_java.error.ProhibidoException;
import com.insightedulab.backend_java.generacion.GeneracionService;
import com.insightedulab.backend_java.linkedin.LinkedinClient;
import com.insightedulab.backend_java.linkedin.LinkedinProperties;
import com.insightedulab.backend_java.linkedin.LinkedinService;
import com.insightedulab.backend_java.model.enums.AutorRol;
import com.insightedulab.backend_java.model.enums.AutorTipo;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository.DatosMensaje;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;

import java.net.URI;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.function.Supplier;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.timeout;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.request;

/**
 * Puertas del panel de curaduría (T07, docs/contratos/PANEL_JAVA_v1.md) contra PostgreSQL real,
 * pasando por los filtros de la API key. La IA está simulada (solo la usa el caso de reintentar).
 * ⚠️ Vacían las tablas: solo corren en una base *_test.
 */
@SpringBootTest(properties = {
        "seguridad.api-keys.ingesta=" + CuraduriaApiTest.CLAVE_INGESTA,
        "seguridad.api-keys.bot=" + CuraduriaApiTest.CLAVE_BOT,
        "seguridad.api-keys.panel=" + CuraduriaApiTest.CLAVE_PANEL,
        "clasificacion.habilitada=false",  // las pruebas llaman a procesarTanda() cuando lo necesitan
        "generacion.habilitada=false",
        "faq.habilitada=false",
        "clasificacion.max-intentos=3",
        "generacion.max-intentos=3",
})
@AutoConfigureMockMvc
class CuraduriaApiTest {

    static final String CLAVE_INGESTA = "clave-de-prueba-ingesta-0123456789";
    static final String CLAVE_BOT = "clave-de-prueba-bot-0123456789";
    static final String CLAVE_PANEL = "clave-de-prueba-panel-0123456789";
    private static final String SERVIDOR = "1554157903701741700";
    private static final String USUARIO = "harrison";
    private static final String LOGRO = "me contrataron!!! empiezo el lunes como QA trainee";
    private static final String POST = "🎉 Camila empieza su primer trabajo en tecnología… #CommunityLab";
    private static final String CASO = "Situación: … Logro: … En sus palabras: \"me contrataron\"";
    private static final String FAQ = "Preguntas frecuentes de la semana…";

    @MockitoBean NlpDataClient ia;
    @Autowired ClasificacionService clasificacion;
    @Autowired GeneracionService generacion;
    @Autowired CuraduriaService curaduria;
    @Autowired CuraduriaRepository repo;
    @Autowired MensajeUpsertRepository upsert;
    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;
    @Autowired ObjectMapper json;

    @BeforeEach
    void vaciarTablas() {
        String base = jdbc.queryForObject("SELECT current_database()", String.class);
        assertThat(base).as("Las pruebas solo corren en una base *_test").endsWith("_test");
        jdbc.execute("TRUNCATE faq_semanas, borradores, mensajes, lotes_recibidos RESTART IDENTITY CASCADE");
    }

    // ── Caso 1: cada clave abre solo su puerta (DEC-70) ──

    @Test
    void sinClaveEs401() throws Exception {
        assertThat(estado(get("/api/v1/borradores"), null)).isEqualTo(401);
        assertThat(estado(post("/api/v1/errores/clasificacion/1/reintentar"), null)).isEqualTo(401);
    }

    @ParameterizedTest
    @ValueSource(strings = {CLAVE_BOT, CLAVE_INGESTA})
    void lasClavesDelBotYDeLaIngestaNoAbrenLasPuertasDelPanel(String clave) throws Exception {
        long id = postPendiente("101");
        assertThat(estado(get("/api/v1/borradores"), clave)).isEqualTo(403);
        assertThat(estado(get("/api/v1/borradores/" + id), clave)).isEqualTo(403);
        assertThat(estado(aprobarPedido(id, true, null), clave)).isEqualTo(403);
        assertThat(estado(get("/api/v1/errores"), clave)).isEqualTo(403);
        assertThat(estadoBorrador(id)).isEqualTo("PENDIENTE");
    }

    @ParameterizedTest
    @ValueSource(strings = {"/api/v1/borradores;x=1", "/api/v1/borrador%65s", "/api//v1/borradores",
            "/api/v1/borradores/", "/api/v1/errore%73", "/api/v1/errores;x=1"})
    void laClaveDelBotNoEntraConUnaRutaDisfrazada(String ruta) throws Exception {
        assertThat(estado(get(URI.create(ruta)), CLAVE_BOT)).as(ruta).isEqualTo(403);
    }

    @Test
    void laClaveDelBotNoApruebaConUnaRutaDisfrazada() throws Exception {
        long id = postPendiente("101");
        MockHttpServletRequestBuilder disfrazada = post(URI.create("/api/v1/borradores;x=1/" + id + "/aprobar"))
                .header(BorradorController.CABECERA_USUARIO, USUARIO)
                .contentType(MediaType.APPLICATION_JSON).content("{\"consentimiento\":true,\"tiempoCuraduriaSeg\":5}");
        assertThat(estado(disfrazada, CLAVE_BOT)).isEqualTo(403);
        assertThat(estadoBorrador(id)).isEqualTo("PENDIENTE");
    }

    @Test
    void laClaveDelPanelNoAbreLasPuertasDeLaIngestaNiDelBot() throws Exception {
        MockHttpServletRequestBuilder lotes = post("/api/v1/lotes").contentType(MediaType.APPLICATION_JSON).content("{}");
        MockHttpServletRequestBuilder enVivo = post("/api/v1/mensajes/en-vivo").contentType(MediaType.APPLICATION_JSON).content("{}");
        assertThat(estado(lotes, CLAVE_PANEL)).isEqualTo(403);
        assertThat(estado(enVivo, CLAVE_PANEL)).isEqualTo(403);
    }

    @Test
    void segundaCapaElControladorRechazaOtroCliente() {
        // Se llama al controlador directo, como si una ruta rara hubiera pasado el filtro
        BorradorController controlador = new BorradorController(curaduria);
        assertThatThrownBy(() -> controlador.listar("bot", null, null, null))
                .isInstanceOf(ProhibidoException.class);
        assertThatThrownBy(() -> controlador.aprobar(null, USUARIO, 1L, new PedidoAprobar(true, 5, null)))
                .isInstanceOf(ProhibidoException.class);
    }

    // ── Caso 2: listar y ver el detalle ──

    @Test
    void listaLosPendientesConSuContexto() throws Exception {
        long post = postPendiente("101");
        long caso = borrador(mensaje("101"), "CASO_EXITO", CASO);
        long faq = faq("2026-W40");

        JsonNode lista = cuerpo(mvc.perform(conClave(get("/api/v1/borradores"), CLAVE_PANEL)).andReturn())
                .get("borradores");

        assertThat(lista).hasSize(3);
        assertThat(lista.get(0).get("id").asLong()).isEqualTo(post);
        assertThat(lista.get(0).get("tipo").asText()).isEqualTo("POST_LINKEDIN");
        assertThat(lista.get(0).get("autorNombre").asText()).isEqualTo("Camila Rojas");
        assertThat(lista.get(0).get("canal").asText()).isEqualTo("logros");
        assertThat(lista.get(1).get("id").asLong()).isEqualTo(caso);
        assertThat(lista.get(2).get("id").asLong()).isEqualTo(faq);
        assertThat(lista.get(2).get("semana").asText()).isEqualTo("2026-W40");
        assertThat(lista.get(2).get("autorNombre").isNull()).isTrue();

        JsonNode soloFaq = cuerpo(mvc.perform(conClave(get("/api/v1/borradores?tipo=FAQ"), CLAVE_PANEL)).andReturn());
        assertThat(soloFaq.get("borradores")).hasSize(1);
        JsonNode aprobados = cuerpo(mvc.perform(conClave(get("/api/v1/borradores?estado=APROBADO"), CLAVE_PANEL)).andReturn());
        assertThat(aprobados.get("borradores")).isEmpty();
    }

    @Test
    void elDetalleTraeElMensajeOriginalYElMotivoDeLaIa() throws Exception {
        long id = postPendiente("101");

        JsonNode d = detalle(id);

        assertThat(d.get("tipo").asText()).isEqualTo("POST_LINKEDIN");
        assertThat(d.get("estado").asText()).isEqualTo("PENDIENTE");
        assertThat(d.get("requiereConsentimiento").asBoolean()).isTrue();
        assertThat(d.get("textoIa").asText()).isEqualTo(POST);
        assertThat(d.get("textoFinal").isNull()).isTrue();
        assertThat(d.get("motivoIa").asText()).isEqualTo("Es una contratación.");
        JsonNode origen = d.get("origen");
        assertThat(origen.get("discordId").asText()).isEqualTo("101");
        assertThat(origen.get("canal").asText()).isEqualTo("logros");
        assertThat(origen.get("texto").asText()).isEqualTo(LOGRO);
        assertThat(origen.get("autorNombre").asText()).isEqualTo("Camila Rojas");
        assertThat(origen.get("fecha").asText()).isEqualTo("2026-09-28T18:58:11.331Z");
        assertThat(d.get("faq").isNull()).isTrue();
    }

    @Test
    void elDetalleDeLaFaqTraeSuSemana() throws Exception {
        long id = faq("2026-W40");

        JsonNode d = detalle(id);

        assertThat(d.get("requiereConsentimiento").asBoolean()).isFalse();
        assertThat(d.get("origen").isNull()).isTrue();
        assertThat(d.get("faq").get("semana").asText()).isEqualTo("2026-W40");
        assertThat(d.get("motivoIa").asText()).isEqualTo("3 preguntas repetidas, 2 con respuesta.");
    }

    @Test
    void unBorradorQueNoExisteEs404YUnFiltroRaroEs422() throws Exception {
        assertThat(estado(get("/api/v1/borradores/999"), CLAVE_PANEL)).isEqualTo(404);
        assertThat(estado(aprobarPedido(999, true, null), CLAVE_PANEL)).isEqualTo(404);
        assertThat(estado(get("/api/v1/borradores?tipo=OTRA_COSA"), CLAVE_PANEL)).isEqualTo(422);
        assertThat(estado(get("/api/v1/borradores?estado=borrado"), CLAVE_PANEL)).isEqualTo(422);
        assertThat(estado(get("/api/v1/borradores?limite=0"), CLAVE_PANEL)).isEqualTo(422);
        assertThat(estado(get("/api/v1/borradores/abc"), CLAVE_PANEL)).isEqualTo(422);
    }

    // ── Caso 3: editar y aprobar ──

    @Test
    void editarYDespuesAprobarGuardaElTextoEditadoYQuienAprobo() throws Exception {
        long id = postPendiente("101");

        MvcResult edicion = mvc.perform(conClave(put("/api/v1/borradores/" + id), CLAVE_PANEL)
                .header(BorradorController.CABECERA_USUARIO, USUARIO)
                .contentType(MediaType.APPLICATION_JSON).content("{\"textoFinal\":\"Texto editado\"}")).andReturn();
        assertThat(edicion.getResponse().getStatus()).isEqualTo(200);
        assertThat(cuerpo(edicion).get("textoFinal").asText()).isEqualTo("Texto editado");

        MvcResult r = mvc.perform(conClave(aprobarPedido(id, true, null), CLAVE_PANEL)).andReturn();

        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(cuerpo(r).get("estado").asText()).isEqualTo("APROBADO");
        Map<String, Object> f = fila(id);
        assertThat(f).containsEntry("estado", "APROBADO").containsEntry("texto_final", "Texto editado")
                .containsEntry("texto_ia", POST).containsEntry("aprobado_por", USUARIO)
                .containsEntry("tiempo_curaduria_seg", 42).containsEntry("consentimiento_confirmado", true);
        assertThat(f.get("aprobado_en")).isNotNull();
    }

    @Test
    void editarYAprobarEnElMismoPaso() throws Exception {
        long id = borrador(logro("101"), "CASO_EXITO", CASO);

        mvc.perform(conClave(aprobarPedido(id, true, "Caso editado"), CLAVE_PANEL)).andReturn();

        assertThat(fila(id)).containsEntry("estado", "APROBADO").containsEntry("texto_final", "Caso editado");
    }

    @Test
    void sinEdicionElTextoFinalQuedaIgualAlDeLaIa() throws Exception {
        long id = postPendiente("101");

        mvc.perform(conClave(aprobarPedido(id, true, null), CLAVE_PANEL)).andReturn();

        assertThat(fila(id)).containsEntry("texto_final", POST);
    }

    @Test
    void sinUsuarioOConUnUsuarioRaroEs422() throws Exception {
        long id = postPendiente("101");
        String cuerpo = "{\"consentimiento\":true,\"tiempoCuraduriaSeg\":5}";
        for (String usuario : new String[]{null, " ", "ana\nFALSO registro", "a".repeat(41), "josé"}) {
            MockHttpServletRequestBuilder p = post("/api/v1/borradores/" + id + "/aprobar")
                    .contentType(MediaType.APPLICATION_JSON).content(cuerpo);
            if (usuario != null) {
                p.header(BorradorController.CABECERA_USUARIO, usuario);
            }
            assertThat(estado(p, CLAVE_PANEL)).as(String.valueOf(usuario)).isEqualTo(422);
        }
        assertThat(estadoBorrador(id)).isEqualTo("PENDIENTE");
    }

    @Test
    void unaEdicionVaciaOSinTiempoEs422() throws Exception {
        long id = postPendiente("101");
        MockHttpServletRequestBuilder vacia = put("/api/v1/borradores/" + id)
                .header(BorradorController.CABECERA_USUARIO, USUARIO)
                .contentType(MediaType.APPLICATION_JSON).content("{\"textoFinal\":\"   \"}");
        MockHttpServletRequestBuilder sinTiempo = post("/api/v1/borradores/" + id + "/aprobar")
                .header(BorradorController.CABECERA_USUARIO, USUARIO)
                .contentType(MediaType.APPLICATION_JSON).content("{\"consentimiento\":true}");
        assertThat(estado(vacia, CLAVE_PANEL)).isEqualTo(422);
        assertThat(estado(sinTiempo, CLAVE_PANEL)).isEqualTo(422);
        assertThat(fila(id)).containsEntry("estado", "PENDIENTE").containsEntry("texto_final", null);
    }

    @Test
    void unCaracterNulEnLaEdicionSeQuita() throws Exception {
        long id = postPendiente("101");

        mvc.perform(conClave(aprobarPedido(id, true, "con\u0000nul"), CLAVE_PANEL)).andReturn();

        assertThat(fila(id)).containsEntry("texto_final", "connul");
    }

    // ── Caso 4 y 5: el consentimiento (D6) ──

    @Test
    void unPostSinConsentimientoNoSeAprueba() throws Exception {
        long post = postPendiente("101");
        long caso = borrador(mensaje("101"), "CASO_EXITO", CASO);

        MvcResult r = mvc.perform(conClave(aprobarPedido(post, false, null), CLAVE_PANEL)).andReturn();

        assertThat(r.getResponse().getStatus()).isEqualTo(422);
        assertThat(cuerpo(r).get("errores").get(0).get("campo").asText()).isEqualTo("consentimiento");
        assertThat(estado(aprobarPedido(caso, false, null), CLAVE_PANEL)).isEqualTo(422);
        assertThat(fila(post)).containsEntry("estado", "PENDIENTE").containsEntry("aprobado_por", null);
        assertThat(estadoBorrador(caso)).isEqualTo("PENDIENTE");
    }

    @Test
    void laFaqSeApruebaSinConsentimiento() throws Exception {
        long id = faq("2026-W40");

        MvcResult r = mvc.perform(conClave(aprobarPedido(id, false, null), CLAVE_PANEL)).andReturn();

        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(fila(id)).containsEntry("estado", "APROBADO").containsEntry("aprobado_por", USUARIO)
                .containsEntry("texto_final", FAQ);
    }

    @Test
    void laV6ImpideEnLaBaseUnPostAprobadoSinConsentimiento() {
        long id = postPendiente("101");

        assertThatThrownBy(() -> jdbc.update("""
                UPDATE borradores SET estado = 'APROBADO', aprobado_por = 'x', aprobado_en = now(),
                       texto_final = texto_ia WHERE id = ?""", id))
                .isInstanceOf(DataIntegrityViolationException.class)
                .hasMessageContaining("borradores_consentimiento_check");
        assertThatThrownBy(() -> jdbc.update("UPDATE borradores SET estado = 'RECHAZADO' WHERE id = ?", id))
                .isInstanceOf(DataIntegrityViolationException.class)
                .hasMessageContaining("borradores_rechazado_check");
    }

    // ── Caso 6: lo que ya no está PENDIENTE no se toca ──

    @Test
    void aprobarEditarORechazarAlgoYaRevisadoEs409() throws Exception {
        long id = postPendiente("101");
        mvc.perform(conClave(aprobarPedido(id, true, null), CLAVE_PANEL)).andReturn();

        MockHttpServletRequestBuilder editar = put("/api/v1/borradores/" + id)
                .header(BorradorController.CABECERA_USUARIO, "otra")
                .contentType(MediaType.APPLICATION_JSON).content("{\"textoFinal\":\"tarde\"}");
        assertThat(estado(aprobarPedido(id, true, null), CLAVE_PANEL)).isEqualTo(409);
        assertThat(estado(editar, CLAVE_PANEL)).isEqualTo(409);
        assertThat(estado(rechazarPedido(id, null), CLAVE_PANEL)).isEqualTo(409);
        assertThat(fila(id)).containsEntry("estado", "APROBADO").containsEntry("texto_final", POST)
                .containsEntry("rechazado_por", null);
    }

    // ── Caso 7: dos personas aprueban a la vez ──

    @Test
    void dosAprobacionesALaVezUnaGanaYLaOtraRecibe409() throws Exception {
        for (int vuelta = 0; vuelta < 10; vuelta++) {
            long id = borrador(logro(String.valueOf(101 + vuelta)), "POST_LINKEDIN", POST);
            CountDownLatch largada = new CountDownLatch(1);
            ExecutorService hilos = Executors.newFixedThreadPool(2);
            try {
                List<Future<String>> resultados = new ArrayList<>();
                for (String usuario : List.of("ana", "beto")) {
                    Callable<String> aprobar = () -> {
                        largada.await();
                        curaduria.aprobar(id, usuario, new PedidoAprobar(true, 10, "versión de " + usuario));
                        return usuario;
                    };
                    resultados.add(hilos.submit(aprobar));
                }
                largada.countDown();
                List<String> ganadores = new ArrayList<>();
                int conflictos = 0;
                for (Future<String> f : resultados) {
                    try {
                        ganadores.add(f.get());
                    } catch (ExecutionException e) {
                        assertThat(e.getCause()).isInstanceOf(ConflictoException.class);
                        conflictos++;
                    }
                }
                assertThat(ganadores).hasSize(1);
                assertThat(conflictos).isEqualTo(1);
                // Lo guardado es todo del ganador: no se mezclan el usuario de uno y el texto del otro
                assertThat(fila(id)).containsEntry("aprobado_por", ganadores.get(0))
                        .containsEntry("texto_final", "versión de " + ganadores.get(0));
            } finally {
                hilos.shutdown();
            }
        }
    }

    // ── Caso 8: rechazar ──

    @Test
    void rechazarGuardaQuienCuandoYElMotivo() throws Exception {
        long id = borrador(logro("101"), "CASO_EXITO", CASO);

        MvcResult r = mvc.perform(conClave(rechazarPedido(id, "Repite el post de ayer"), CLAVE_PANEL)).andReturn();

        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        Map<String, Object> f = fila(id);
        assertThat(f).containsEntry("estado", "RECHAZADO").containsEntry("rechazado_por", USUARIO)
                .containsEntry("motivo_rechazo", "Repite el post de ayer").containsEntry("aprobado_por", null)
                .containsEntry("tiempo_curaduria_seg", 7);
        assertThat(f.get("rechazado_en")).isNotNull();
        JsonNode rechazados = cuerpo(mvc.perform(conClave(get("/api/v1/borradores?estado=RECHAZADO"), CLAVE_PANEL))
                .andReturn()).get("borradores");
        assertThat(rechazados).hasSize(1);
        assertThat(rechazados.get(0).get("revisadoPor").asText()).isEqualTo(USUARIO);
    }

    @Test
    void rechazarSinMotivoTambienSirve() throws Exception {
        long id = postPendiente("101");
        MockHttpServletRequestBuilder sinCuerpo = post("/api/v1/borradores/" + id + "/rechazar")
                .header(BorradorController.CABECERA_USUARIO, USUARIO)
                .contentType(MediaType.APPLICATION_JSON).content("{}");

        assertThat(estado(sinCuerpo, CLAVE_PANEL)).isEqualTo(200);
        assertThat(fila(id)).containsEntry("estado", "RECHAZADO").containsEntry("motivo_rechazo", null);
    }

    // ── Caso 9: reintentar lo que quedó en ERROR ──

    @Test
    void unaClasificacionEnErrorVuelveALaColaYLaTomaLaTarea() throws Exception {
        upsert.upsert(datos("101", LOGRO));
        jdbc.update("UPDATE mensajes SET estado_clasificacion = 'ERROR', intentos_clasificacion = 3 WHERE discord_id = '101'");
        long id = mensaje("101");

        JsonNode errores = cuerpo(mvc.perform(conClave(get("/api/v1/errores"), CLAVE_PANEL)).andReturn());
        assertThat(errores.get("clasificacion")).hasSize(1);
        assertThat(errores.get("clasificacion").get(0).get("mensajeId").asLong()).isEqualTo(id);
        assertThat(errores.get("clasificacion").get(0).get("intentos").asInt()).isEqualTo(3);
        assertThat(errores.get("generacion")).isEmpty();

        MvcResult r = mvc.perform(conClave(reintentar("clasificacion", id), CLAVE_PANEL)).andReturn();

        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(cuerpo(r).get("estado").asText()).isEqualTo("PENDIENTE");
        assertThat(filaMensaje("101")).containsEntry("estado_clasificacion", "PENDIENTE")
                .containsEntry("intentos_clasificacion", 0);
        when(ia.procesar(any(), anyString())).thenReturn(new RespuestaIa("1.0", "x", List.of(
                new RespuestaIa.Resultado("101", "OK", "llm", "TESTIMONIO", 0.9, "POSITIVO", "empleo", "logro")),
                new RespuestaIa.Metricas(10, 100, 20)));
        assertThat(clasificacion.procesarTanda().ok()).isEqualTo(1);
        assertThat(filaMensaje("101")).containsEntry("estado_clasificacion", "OK");
        // Ya no está en ERROR: reintentar otra vez es 409, y un mensaje que no existe es 404
        assertThat(estado(reintentar("clasificacion", id), CLAVE_PANEL)).isEqualTo(409);
        assertThat(estado(reintentar("clasificacion", 999), CLAVE_PANEL)).isEqualTo(404);
    }

    @Test
    void unaGeneracionEnErrorVuelveALaColaYLaTomaLaTarea() throws Exception {
        long id = logro("101");
        jdbc.update("""
                UPDATE mensajes SET generacion_estado = 'ERROR', generacion_intentos = 3,
                       generacion_motivo = 'La IA respondió HTTP 500' WHERE id = ?""", id);

        JsonNode errores = cuerpo(mvc.perform(conClave(get("/api/v1/errores"), CLAVE_PANEL)).andReturn());
        assertThat(errores.get("generacion")).hasSize(1);
        assertThat(errores.get("generacion").get(0).get("motivo").asText()).isEqualTo("La IA respondió HTTP 500");

        assertThat(estado(reintentar("generacion", id), CLAVE_PANEL)).isEqualTo(200);

        assertThat(filaMensaje("101")).containsEntry("generacion_estado", null).containsEntry("generacion_intentos", 0);
        when(ia.generar(any(), anyString())).thenReturn(new RespuestaGenerar("1.0", "gen-x", "101", "OK", true,
                "Es una contratación.", POST, CASO, new RespuestaIa.Metricas(6120, 1450, 520)));
        assertThat(generacion.procesarTanda().generados()).isEqualTo(1);
        assertThat(filaMensaje("101")).containsEntry("generacion_estado", "GENERADO");
        assertThat(jdbc.queryForObject("SELECT count(*) FROM borradores WHERE estado = 'PENDIENTE'", Integer.class))
                .isEqualTo(2);
        assertThat(estado(reintentar("generacion", id), CLAVE_PANEL)).isEqualTo(409);
    }

    @Test
    void reintentarSinUsuarioEs422() throws Exception {
        long id = logro("101");
        jdbc.update("UPDATE mensajes SET generacion_estado = 'ERROR' WHERE id = ?", id);

        MockHttpServletRequestBuilder sinUsuario = post("/api/v1/errores/generacion/" + id + "/reintentar")
                .contentType(MediaType.APPLICATION_JSON).content("{}");

        assertThat(estado(sinUsuario, CLAVE_PANEL)).isEqualTo(422);
        assertThat(filaMensaje("101")).containsEntry("generacion_estado", "ERROR");
    }

    // ── Caso 10: el CORS quedó cerrado (S6) ──

    @Test
    void unNavegadorDeOtroOrigenNoRecibeCabecerasCors() throws Exception {
        MvcResult simple = mvc.perform(conClave(get("/api/v1/borradores"), CLAVE_PANEL)
                .header("Origin", "http://sitio-malicioso.example")).andReturn();
        MvcResult previo = mvc.perform(conClave(options("/api/v1/borradores"), CLAVE_PANEL)
                .header("Origin", "http://sitio-malicioso.example")
                .header("Access-Control-Request-Method", "POST")).andReturn();
        MvcResult previoSinClave = mvc.perform(request(HttpMethod.OPTIONS, URI.create("/api/v1/borradores"))
                .header("Origin", "http://sitio-malicioso.example")
                .header("Access-Control-Request-Method", "POST")).andReturn();

        for (MvcResult r : List.of(simple, previo, previoSinClave)) {
            assertThat(r.getResponse().getHeader("Access-Control-Allow-Origin")).isNull();
            assertThat(r.getResponse().getHeader("Access-Control-Allow-Credentials")).isNull();
        }
    }

    // ── T13 · Caso 1: la V9 ──

    @Test
    void laV9AgregaLasColumnasYSoloUnPostAprobadoTieneEstadoEnLinkedin() {
        List<String> columnas = jdbc.queryForList("""
                SELECT column_name FROM information_schema.columns
                 WHERE table_name = 'borradores' AND column_name LIKE 'linkedin%'""", String.class);
        assertThat(columnas).containsExactlyInAnyOrder("linkedin_estado", "linkedin_post_id", "linkedin_en",
                "linkedin_motivo");
        long caso = borrador(logro("101"), "CASO_EXITO", CASO);
        jdbc.update("""
                UPDATE borradores SET estado = 'APROBADO', aprobado_por = 'x', aprobado_en = now(),
                       texto_final = texto_ia, consentimiento_confirmado = true WHERE id = ?""", caso);
        long post = borrador(mensaje("101"), "POST_LINKEDIN", POST);

        assertThatThrownBy(() -> jdbc.update(
                "UPDATE borradores SET linkedin_estado = 'APAGADO', linkedin_en = now() WHERE id = ?", caso))
                .isInstanceOf(DataIntegrityViolationException.class)
                .hasMessageContaining("borradores_linkedin_check");
        // Un post todavía PENDIENTE tampoco
        assertThatThrownBy(() -> jdbc.update(
                "UPDATE borradores SET linkedin_estado = 'APAGADO', linkedin_en = now() WHERE id = ?", post))
                .isInstanceOf(DataIntegrityViolationException.class)
                .hasMessageContaining("borradores_linkedin_check");
    }

    // ── T13 · Caso 2: aprobar un post guarda su estado en LinkedIn ──

    @Test
    void aprobarUnPostConLinkedinApagadoLoGuardaComoApagado() throws Exception {
        long post = postPendiente("101");
        long caso = borrador(mensaje("101"), "CASO_EXITO", CASO);

        mvc.perform(conClave(aprobarPedido(caso, true, null), CLAVE_PANEL)).andReturn();
        long inicio = System.nanoTime();
        MvcResult r = mvc.perform(conClave(aprobarPedido(post, true, null), CLAVE_PANEL)).andReturn();

        // Aprobar responde enseguida: LinkedIn va en segundo plano
        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(Duration.ofNanos(System.nanoTime() - inicio)).isLessThan(Duration.ofSeconds(5));
        esperar(() -> fila(post).get("linkedin_estado") != null);
        Map<String, Object> f = fila(post);
        assertThat(f).containsEntry("linkedin_estado", "APAGADO").containsEntry("linkedin_post_id", null)
                .containsEntry("linkedin_motivo", null);
        assertThat(f.get("linkedin_en")).isNotNull();
        // El caso de éxito no se publica en LinkedIn
        assertThat(fila(caso)).containsEntry("linkedin_estado", null);
        JsonNode linkedin = detalle(post).get("linkedin");
        assertThat(linkedin.get("estado").asText()).isEqualTo("APAGADO");
        assertThat(linkedin.get("en").isNull()).isFalse();
        assertThat(detalle(caso).get("linkedin").isNull()).isTrue();
    }

    // ── T13 · Caso 4: la guarda del estado en LinkedIn ──

    @Test
    void elEstadoEnLinkedinSeGuardaUnaSolaVezYSoloEnUnPostAprobado() {
        long mensajeId = logro("101");
        // Ids altos: ninguna tarea en segundo plano de otra prueba puede tocar estas filas
        long post = jdbc.queryForObject("""
                INSERT INTO borradores (id, mensaje_id, tipo, texto_ia, estado, aprobado_por, aprobado_en, texto_final,
                                        consentimiento_confirmado)
                VALUES (9001, ?, 'POST_LINKEDIN', ?, 'APROBADO', 'x', now(), ?, true) RETURNING id""",
                Long.class, mensajeId, POST, POST);
        long pendiente = jdbc.queryForObject(
                "INSERT INTO borradores (id, mensaje_id, tipo, texto_ia) VALUES (9002, ?, 'POST_LINKEDIN', ?) RETURNING id",
                Long.class, mensajeId, POST);

        assertThat(repo.guardarLinkedin(post, "PUBLICADO", "urn:li:share:123", null)).isTrue();
        assertThat(repo.guardarLinkedin(post, "ERROR", null, "LinkedIn respondió HTTP 500")).isFalse();
        assertThat(repo.guardarLinkedin(pendiente, "APAGADO", null, null)).isFalse();

        assertThat(fila(post)).containsEntry("linkedin_estado", "PUBLICADO")
                .containsEntry("linkedin_post_id", "urn:li:share:123").containsEntry("linkedin_motivo", null);
        assertThat(fila(pendiente)).containsEntry("linkedin_estado", null);
    }

    // ── T13 · Caso 5 y 5b: listar y ver traen lo nuevo ──

    @Test
    void listarYVerTraenElLogroElMotivoYElEstadoEnLinkedin() throws Exception {
        long post = postPendiente("101");
        long caso = borrador(mensaje("101"), "CASO_EXITO", CASO);
        long faq = faq("2026-W40");

        MvcResult r = mvc.perform(conClave(get("/api/v1/borradores"), CLAVE_PANEL)).andReturn();
        JsonNode cuerpo = cuerpo(r);
        JsonNode lista = cuerpo.get("borradores");

        assertThat(cuerpo.get("linkedinModo").asText()).isEqualTo("APAGADO");  // las pruebas la apagan (pom.xml)
        assertThat(lista.get(0).get("id").asLong()).isEqualTo(post);
        assertThat(lista.get(0).get("mensajeId").asLong()).isEqualTo(mensaje("101"));
        assertThat(lista.get(0).get("motivoIa").asText()).isEqualTo("Es una contratación.");
        JsonNode linkedin = lista.get(0).get("linkedin");
        for (String campo : List.of("estado", "postId", "en", "motivo")) {
            assertThat(linkedin.get(campo).isNull()).as(campo).isTrue();  // sin dato: todavía no se aprobó
        }
        assertThat(lista.get(1).get("id").asLong()).isEqualTo(caso);
        assertThat(lista.get(1).get("mensajeId").asLong()).isEqualTo(mensaje("101"));
        assertThat(lista.get(1).get("linkedin").isNull()).isTrue();
        assertThat(lista.get(2).get("id").asLong()).isEqualTo(faq);
        assertThat(lista.get(2).get("mensajeId").isNull()).isTrue();
        assertThat(lista.get(2).get("linkedin").isNull()).isTrue();
        assertThat(lista.get(2).get("motivoIa").asText()).isEqualTo("3 preguntas repetidas, 2 con respuesta.");

        assertThat(detalle(post).get("linkedin").get("estado").isNull()).isTrue();
        assertThat(detalle(faq).get("linkedin").isNull()).isTrue();
    }

    @Test
    void elModoDeLinkedinNoMuestraElTokenNiElAutor() throws Exception {
        // Encendido con token y autor (propiedades de prueba): solo se lee el modo, nunca se llama a LinkedIn
        LinkedinClient cliente = Mockito.mock(LinkedinClient.class);
        LinkedinService real = new LinkedinService(cliente,
                new LinkedinProperties(true, "token-secreto-de-prueba", "urn:li:organization:777", null));
        CuraduriaService servicio = new CuraduriaService(Mockito.mock(CuraduriaRepository.class), real, null);

        String respuesta = json.writeValueAsString(servicio.listar(null, null, null));

        assertThat(json.readTree(respuesta).get("linkedinModo").asText()).isEqualTo("REAL");
        assertThat(respuesta).doesNotContain("token-secreto-de-prueba").doesNotContain("urn:li:organization:777");
        Mockito.verifyNoInteractions(cliente);
    }

    // ── T13 · Caso 6 y 7: reintentar la FAQ en ERROR ──

    @Test
    void reintentarUnaFaqEnErrorLaDevuelveALaColaYLaArmaEnSegundoPlano() throws Exception {
        semanaEnError("2026-W39");
        duda("201", "sim-ana");
        duda("202", "sim-beto");
        CountDownLatch soltar = new CountDownLatch(1);
        doAnswer(inv -> {
            soltar.await(10, TimeUnit.SECONDS);  // la IA simulada espera a que la prueba mire la base
            return new RespuestaFaqSemanal("1.0", "faq-x", "2026-W39", "OK", FAQ, "1 pregunta repetida.",
                    List.of(new RespuestaFaqSemanal.Grupo("¿Cuándo es la entrega?", 2, false, null, List.of(),
                            "Sin respaldo.")), new RespuestaIa.Metricas(10, 100, 20));
        }).when(ia).faq(any(), anyString());

        JsonNode errores = cuerpo(mvc.perform(conClave(get("/api/v1/errores"), CLAVE_PANEL)).andReturn());
        assertThat(errores.get("faq")).hasSize(1);
        JsonNode enError = errores.get("faq").get(0);
        assertThat(enError.get("semana").asText()).isEqualTo("2026-W39");
        assertThat(enError.get("intentos").asInt()).isEqualTo(3);
        assertThat(enError.get("motivo").asText()).isEqualTo("La IA no respondió a tiempo.");
        assertThat(enError.get("desde").isNull()).isFalse();
        assertThat(enError.get("hasta").isNull()).isFalse();

        MvcResult r = mvc.perform(conClave(reintentarFaq("2026-W39"), CLAVE_PANEL)).andReturn();

        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(cuerpo(r).get("semana").asText()).isEqualTo("2026-W39");
        assertThat(cuerpo(r).get("etapa").asText()).isEqualTo("faq");
        assertThat(cuerpo(r).get("estado").asText()).isEqualTo("PENDIENTE");
        assertThat(semana("2026-W39")).containsEntry("estado", null).containsEntry("intentos", 0)
                .containsEntry("terminada_en", null);
        assertThat(cuerpo(mvc.perform(conClave(get("/api/v1/errores"), CLAVE_PANEL)).andReturn()).get("faq")).isEmpty();

        // En segundo plano, con la IA simulada (nunca la real)
        verify(ia, timeout(10_000)).faq(any(), anyString());
        soltar.countDown();
        esperar(() -> "GENERADA".equals(semana("2026-W39").get("estado")));
        assertThat(semana("2026-W39")).containsEntry("intentos", 1);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM borradores WHERE tipo = 'FAQ' AND estado = 'PENDIENTE'",
                Integer.class)).isEqualTo(1);
        verify(ia, times(1)).faq(any(), anyString());
    }

    @Test
    void reintentarUnaFaqQueNoEstaEnErrorQueNoExisteOConOtraFormaNoCambiaNada() throws Exception {
        faq("2026-W40");  // GENERADA

        assertThat(estado(reintentarFaq("2026-W40"), CLAVE_PANEL)).isEqualTo(409);
        assertThat(estado(reintentarFaq("2026-W41"), CLAVE_PANEL)).isEqualTo(404);
        for (String semana : List.of("2026-41", "2026-W4", "semana", "2026-W401")) {
            assertThat(estado(reintentarFaq(semana), CLAVE_PANEL)).as(semana).isEqualTo(422);
        }
        MockHttpServletRequestBuilder sinUsuario = post("/api/v1/errores/faq/2026-W40/reintentar")
                .contentType(MediaType.APPLICATION_JSON).content("{}");
        assertThat(estado(sinUsuario, CLAVE_PANEL)).isEqualTo(422);
        assertThat(semana("2026-W40")).containsEntry("estado", "GENERADA").containsEntry("intentos", 1);
        Mockito.verifyNoInteractions(ia);
    }

    // ── T13 · Caso 8: la puerta nueva solo la abre la clave del panel ──

    @Test
    void laPuertaDeReintentarLaFaqSoloLaAbreElPanel() throws Exception {
        semanaEnError("2026-W39");

        assertThat(estado(reintentarFaq("2026-W39"), null)).isEqualTo(401);
        assertThat(estado(reintentarFaq("2026-W39"), CLAVE_BOT)).isEqualTo(403);
        for (String ruta : List.of("/api/v1/errores;x=1/faq/2026-W39/reintentar",
                "/api/v1/%65rrores/faq/2026-W39/reintentar", "/api/v1/errores/faq/2026-W39/reintentar;x=1")) {
            MockHttpServletRequestBuilder disfrazada = post(URI.create(ruta))
                    .header(BorradorController.CABECERA_USUARIO, USUARIO)
                    .contentType(MediaType.APPLICATION_JSON).content("{}");
            assertThat(estado(disfrazada, CLAVE_BOT)).as(ruta).isEqualTo(403);
        }
        // Segunda capa: el controlador también revisa el cliente
        ErroresController controlador = new ErroresController(curaduria);
        assertThatThrownBy(() -> controlador.reintentarFaq("bot", USUARIO, "2026-W39"))
                .isInstanceOf(ProhibidoException.class);
        assertThat(semana("2026-W39")).containsEntry("estado", "ERROR").containsEntry("intentos", 3);
    }

    // ── Ayudas ──

    private static MockHttpServletRequestBuilder reintentarFaq(String semana) {
        return post("/api/v1/errores/faq/" + semana + "/reintentar")
                .header(BorradorController.CABECERA_USUARIO, USUARIO)
                .contentType(MediaType.APPLICATION_JSON).content("{}");
    }

    /** Una semana de la FAQ que agotó sus intentos, con la ventana de las dudas de datos() (fin de septiembre). */
    private void semanaEnError(String semana) {
        jdbc.update("""
                INSERT INTO faq_semanas (semana, desde, hasta, estado, motivo, intentos, terminada_en)
                VALUES (?, '2026-09-21T13:00:00Z', '2026-10-01T13:00:00Z', 'ERROR', 'La IA no respondió a tiempo.', 3, now())
                """, semana);
    }

    /** Una duda de una persona, ya clasificada OK, que entra en la FAQ semanal. */
    private void duda(String discordId, String autorId) {
        DatosMensaje d = datos(discordId, "¿hasta cuándo se puede entregar el challenge?");
        upsert.upsert(new DatosMensaje(d.discordId(), d.canalId(), autorId, d.autorTipo(), d.autorRol(),
                d.esSimulado(), d.fecha(), d.respondeA(), d.texto(), d.contrato(), d.versionContrato(), d.servidorId()));
        jdbc.update("""
                UPDATE mensajes SET intencion = 'PREGUNTA_FAQ', estado_clasificacion = 'OK', tema = 'evaluaciones',
                       confianza = 0.9 WHERE discord_id = ?""", discordId);
    }

    private Map<String, Object> semana(String semana) {
        return jdbc.queryForMap("SELECT estado, intentos, terminada_en FROM faq_semanas WHERE semana = ?", semana);
    }

    /** Sondea la base cada 50 ms hasta que se cumpla, con un tope de 10 s: las tareas en segundo plano tardan poco. */
    private static void esperar(Supplier<Boolean> condicion) throws InterruptedException {
        long tope = System.nanoTime() + Duration.ofSeconds(10).toNanos();
        while (!condicion.get()) {
            assertThat(System.nanoTime()).as("La tarea en segundo plano no terminó en 10 s").isLessThan(tope);
            Thread.sleep(50);
        }
    }

    private MockHttpServletRequestBuilder aprobarPedido(long id, boolean consentimiento, String textoFinal) throws Exception {
        Map<String, Object> cuerpo = new LinkedHashMap<>();
        cuerpo.put("consentimiento", consentimiento);
        cuerpo.put("tiempoCuraduriaSeg", 42);
        if (textoFinal != null) {
            cuerpo.put("textoFinal", textoFinal);
        }
        return post("/api/v1/borradores/" + id + "/aprobar").header(BorradorController.CABECERA_USUARIO, USUARIO)
                .contentType(MediaType.APPLICATION_JSON).content(json.writeValueAsBytes(cuerpo));
    }

    private MockHttpServletRequestBuilder rechazarPedido(long id, String motivo) throws Exception {
        Map<String, Object> cuerpo = new LinkedHashMap<>();
        cuerpo.put("motivo", motivo);
        cuerpo.put("tiempoCuraduriaSeg", 7);
        return post("/api/v1/borradores/" + id + "/rechazar").header(BorradorController.CABECERA_USUARIO, USUARIO)
                .contentType(MediaType.APPLICATION_JSON).content(json.writeValueAsBytes(cuerpo));
    }

    private static MockHttpServletRequestBuilder reintentar(String etapa, long mensajeId) {
        return post("/api/v1/errores/" + etapa + "/" + mensajeId + "/reintentar")
                .header(BorradorController.CABECERA_USUARIO, USUARIO)
                .contentType(MediaType.APPLICATION_JSON).content("{}");
    }

    private static MockHttpServletRequestBuilder conClave(MockHttpServletRequestBuilder p, String clave) {
        return clave == null ? p : p.header("X-Api-Key", clave);
    }

    private int estado(MockHttpServletRequestBuilder p, String clave) throws Exception {
        return mvc.perform(conClave(p, clave)).andReturn().getResponse().getStatus();
    }

    private JsonNode detalle(long id) throws Exception {
        MvcResult r = mvc.perform(conClave(get("/api/v1/borradores/" + id), CLAVE_PANEL)).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        return cuerpo(r);
    }

    private JsonNode cuerpo(MvcResult r) throws Exception {
        return json.readTree(r.getResponse().getContentAsByteArray());
    }

    /** Un logro clasificado con su post de LinkedIn pendiente, como lo deja la generación de T06. */
    private long postPendiente(String discordId) {
        long mensajeId = logro(discordId);
        jdbc.update("UPDATE mensajes SET generacion_estado = 'GENERADO', generacion_motivo = 'Es una contratación.' WHERE id = ?",
                mensajeId);
        return borrador(mensajeId, "POST_LINKEDIN", POST);
    }

    private long logro(String discordId) {
        upsert.upsert(datos(discordId, LOGRO));
        jdbc.update("UPDATE mensajes SET intencion = 'TESTIMONIO', estado_clasificacion = 'OK', confianza = 0.9 WHERE discord_id = ?",
                discordId);
        return mensaje(discordId);
    }

    private long borrador(long mensajeId, String tipo, String texto) {
        return jdbc.queryForObject("INSERT INTO borradores (mensaje_id, tipo, texto_ia) VALUES (?, ?, ?) RETURNING id",
                Long.class, mensajeId, tipo, texto);
    }

    private long faq(String semana) {
        long id = jdbc.queryForObject("INSERT INTO borradores (mensaje_id, tipo, texto_ia) VALUES (NULL, 'FAQ', ?) RETURNING id",
                Long.class, FAQ);
        jdbc.update("""
                INSERT INTO faq_semanas (semana, desde, hasta, estado, motivo, intentos, borrador_id, terminada_en)
                VALUES (?, now() - interval '7 days', now(), 'GENERADA', '3 preguntas repetidas, 2 con respuesta.', 1, ?, now())
                """, semana, id);
        return id;
    }

    private long mensaje(String discordId) {
        return jdbc.queryForObject("SELECT id FROM mensajes WHERE discord_id = ?", Long.class, discordId);
    }

    private String estadoBorrador(long id) {
        return jdbc.queryForObject("SELECT estado FROM borradores WHERE id = ?", String.class, id);
    }

    private Map<String, Object> fila(long borradorId) {
        return jdbc.queryForMap("SELECT * FROM borradores WHERE id = ?", borradorId);
    }

    private Map<String, Object> filaMensaje(String discordId) {
        return jdbc.queryForMap("SELECT * FROM mensajes WHERE discord_id = ?", discordId);
    }

    private static DatosMensaje datos(String id, String texto) {
        Instant fecha = Instant.parse("2026-09-28T18:56:30.331Z").plusSeconds(Long.parseLong(id));
        Map<String, Object> caja = new LinkedHashMap<>();
        caja.put("id", id);
        caja.put("textoOriginal", texto);
        caja.put("canal", Map.of("id", "1554158272867467374", "nombre", "logros"));
        caja.put("autor", Map.of("id", "sim-camila-rojas", "nombreVisible", "Camila Rojas", "tipo", "persona",
                "rol", "miembro"));
        return new DatosMensaje(id, "1554158272867467374", "sim-camila-rojas", AutorTipo.persona, AutorRol.miembro,
                true, fecha, null, texto, caja, "1.0", SERVIDOR);
    }
}
