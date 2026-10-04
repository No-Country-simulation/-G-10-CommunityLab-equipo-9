package com.insightedulab.backend_java;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doCallRealMethod;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Pruebas de POST /api/v1/lotes (T03) contra PostgreSQL real, pasando por los filtros
 * (API key, tope de tamaño) y el manejo global de errores.
 * ⚠️ Vacían las tablas: solo corren en una base *_test.
 */
@SpringBootTest(properties = {
        "seguridad.api-keys.ingesta=" + LotesApiTest.CLAVE,
        "seguridad.max-bytes-cuerpo=200000",
        "clasificacion.habilitada=false",  // que la tarea programada no tome los mensajes de estas pruebas
        "generacion.habilitada=false",  // T06: que la generación no tome los logros de estas pruebas
})
@AutoConfigureMockMvc
class LotesApiTest {

    static final String CLAVE = "clave-de-prueba-ingesta-0123456789";
    private static final String RUTA = "/api/v1/lotes";

    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;
    @Autowired ObjectMapper json;
    // Espía: hace lo de siempre, salvo cuando una prueba le pide fallar
    @MockitoSpyBean MensajeUpsertRepository upsertRepo;

    @BeforeEach
    void vaciarTablas() {
        String base = jdbc.queryForObject("SELECT current_database()", String.class);
        assertThat(base).as("Las pruebas solo corren en una base *_test").endsWith("_test");
        jdbc.execute("TRUNCATE borradores, mensajes, lotes_recibidos RESTART IDENTITY CASCADE");
    }

    // ── Caso 1: lote válido ──

    @Test
    void loteValidoGuardaLosMensajesYElLote() throws Exception {
        MvcResult r = enviar(lote("lote-1", mensaje("101", 1), mensaje("102", 1), mensaje("103", 1)));

        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        JsonNode recibo = cuerpo(r);
        assertThat(recibo.get("loteId").asText()).isEqualTo("lote-1");
        assertThat(recibo.get("total").asInt()).isEqualTo(3);
        assertThat(recibo.get("nuevos").asInt()).isEqualTo(3);
        assertThat(recibo.get("actualizados").asInt()).isZero();
        assertThat(recibo.get("sinCambios").asInt()).isZero();
        assertThat(recibo.get("yaRecibido").asBoolean()).isFalse();
        assertThat(contar("mensajes")).isEqualTo(3);
        assertThat(contar("lotes_recibidos")).isEqualTo(1);
        // La caja se guardó completa, con los nombres del contrato
        assertThat(jdbc.queryForObject(
                "SELECT contrato->'autor'->>'nombreVisible' FROM mensajes WHERE discord_id = '101'", String.class))
                .isEqualTo("Ana Pérez");
        assertThat(jdbc.queryForObject(
                "SELECT autor_tipo || '/' || autor_rol || '/' || es_simulado FROM mensajes WHERE discord_id = '101'",
                String.class)).isEqualTo("persona/miembro/true");
    }

    // ── Caso 2: el mismo loteId otra vez ──

    @Test
    void elMismoLoteDosVecesDevuelveElMismoRecibo() throws Exception {
        Map<String, Object> lote = lote("lote-1", mensaje("101", 1), mensaje("102", 1), mensaje("103", 1));
        JsonNode primero = cuerpo(enviar(lote));

        MvcResult r = enviar(lote);

        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        JsonNode segundo = cuerpo(r);
        assertThat(segundo.get("yaRecibido").asBoolean()).isTrue();
        ((com.fasterxml.jackson.databind.node.ObjectNode) segundo).put("yaRecibido", false);
        assertThat(segundo).isEqualTo(primero);  // mismos números y misma fecha de recepción
        assertThat(contar("mensajes")).isEqualTo(3);
        assertThat(contar("lotes_recibidos")).isEqualTo(1);
    }

    @Test
    void dosEnviosSimultaneosDelMismoLoteNoDuplican() throws Exception {
        Map<String, Object> lote = lote("lote-concurrente", mensaje("101", 1), mensaje("102", 1));
        ExecutorService hilos = Executors.newFixedThreadPool(4);
        try {
            List<Future<JsonNode>> futuros = new ArrayList<>();
            for (int i = 0; i < 4; i++) {
                futuros.add(hilos.submit((Callable<JsonNode>) () -> cuerpo(enviar(lote))));
            }
            int primeros = 0;
            for (Future<JsonNode> f : futuros) {
                JsonNode recibo = f.get();
                assertThat(recibo.get("total").asInt()).isEqualTo(2);
                assertThat(recibo.get("nuevos").asInt()).isEqualTo(2);
                if (!recibo.get("yaRecibido").asBoolean()) {
                    primeros++;
                }
            }
            assertThat(primeros).isEqualTo(1);
        } finally {
            hilos.shutdown();
        }
        assertThat(contar("lotes_recibidos")).isEqualTo(1);
        assertThat(contar("mensajes")).isEqualTo(2);
    }

    // ── Caso 3: loteId nuevo, mismos mensajes, uno con más reacciones ──

    @Test
    void loteNuevoConUnMensajeCambiadoCuentaUnActualizado() throws Exception {
        enviar(lote("lote-1", mensaje("101", 1), mensaje("102", 1), mensaje("103", 1)));

        JsonNode recibo = cuerpo(enviar(lote("lote-2", mensaje("101", 1), mensaje("102", 5), mensaje("103", 1))));

        assertThat(recibo.get("nuevos").asInt()).isZero();
        assertThat(recibo.get("actualizados").asInt()).isEqualTo(1);
        assertThat(recibo.get("sinCambios").asInt()).isEqualTo(2);
        assertThat(contar("mensajes")).isEqualTo(3);
        assertThat(contar("lotes_recibidos")).isEqualTo(2);
        assertThat(jdbc.queryForObject(
                "SELECT (contrato->'reacciones'->0->>'cantidad')::int FROM mensajes WHERE discord_id = '102'",
                Integer.class)).isEqualTo(5);
    }

    // ── Caso 4: sin clave o con clave incorrecta ──

    @Test
    void sinApiKeyEs401YNoGuardaNada() throws Exception {
        MvcResult r = mvc.perform(post(RUTA).contentType(MediaType.APPLICATION_JSON)
                .content(json.writeValueAsBytes(lote("lote-1", mensaje("101", 1))))).andReturn();

        assertThat(r.getResponse().getStatus()).isEqualTo(401);
        assertThat(cuerpo(r).get("codigo").asText()).isEqualTo("NO_AUTORIZADO");
        assertThat(cuerpo(r).get("idCorrelacion").asText()).isNotBlank();
        assertThat(contar("mensajes")).isZero();
    }

    @Test
    void conApiKeyIncorrectaEs401YNoGuardaNada() throws Exception {
        MvcResult r = enviar(lote("lote-1", mensaje("101", 1)), "otra-clave");

        assertThat(r.getResponse().getStatus()).isEqualTo(401);
        assertThat(r.getResponse().getContentAsString()).doesNotContain("otra-clave");
        assertThat(contar("mensajes")).isZero();
        assertThat(contar("lotes_recibidos")).isZero();
    }

    // ── Caso 5: health sin clave ──

    @Test
    void healthNoPideClave() throws Exception {
        MvcResult r = mvc.perform(get("/actuator/health")).andReturn();

        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(r.getResponse().getContentAsString()).contains("UP");
    }

    @Test
    void otrasRutasDelActuadorSiPidenClave() throws Exception {
        assertThat(mvc.perform(get("/actuator/info")).andReturn().getResponse().getStatus()).isEqualTo(401);
    }

    // ── Caso 6: versión distinta o valor fuera de la lista ──

    @Test
    void valoresFueraDelContratoSon422SinRepetirLosDatos() throws Exception {
        Map<String, Object> lote = lote("lote-1", mensaje("101", 1));
        lote.put("versionContrato", "2.0");
        Map<String, Object> m = primerMensaje(lote);
        autorDe(m).put("tipo", "HUMANO");
        m.put("textoOriginal", "dato privado del alumno");

        MvcResult r = enviar(lote, CLAVE, "corr-123");

        assertThat(r.getResponse().getStatus()).isEqualTo(422);
        JsonNode error = cuerpo(r);
        assertThat(error.get("codigo").asText()).isEqualTo("CONTRATO_INVALIDO");
        assertThat(error.get("idCorrelacion").asText()).isEqualTo("corr-123");
        assertThat(campos(error)).contains("versionContrato", "mensajes[0].autor.tipo");
        String texto = r.getResponse().getContentAsString();
        assertThat(texto).doesNotContain("HUMANO").doesNotContain("2.0").doesNotContain("dato privado");  // S7
        assertThat(contar("mensajes")).isZero();
    }

    @Test
    void tipoDeDatoIncorrectoEs422ConLaRuta() throws Exception {
        Map<String, Object> lote = lote("lote-1", mensaje("101", 1));
        primerMensaje(lote).put("esSimulado", List.of("no", "es", "booleano"));

        MvcResult r = enviar(lote);

        assertThat(r.getResponse().getStatus()).isEqualTo(422);
        assertThat(campos(cuerpo(r))).contains("mensajes[0].esSimulado");
    }

    @Test
    void fechaImposibleEs422() throws Exception {
        Map<String, Object> lote = lote("lote-1", mensaje("101", 1));
        primerMensaje(lote).put("fecha", "2026-13-45T18:56:30.331Z");

        MvcResult r = enviar(lote);

        assertThat(r.getResponse().getStatus()).isEqualTo(422);
        assertThat(campos(cuerpo(r))).contains("mensajes[0].fecha");
    }

    @Test
    void jsonRotoEs400() throws Exception {
        MvcResult r = mvc.perform(conClave(post(RUTA), CLAVE).contentType(MediaType.APPLICATION_JSON)
                .content("{\"loteId\": ")).andReturn();

        assertThat(r.getResponse().getStatus()).isEqualTo(400);
        assertThat(cuerpo(r).get("codigo").asText()).isEqualTo("CUERPO_INVALIDO");
    }

    // ── Caso 7: un mensaje inválido en medio del lote ──

    @Test
    void unMensajeInvalidoEnMedioNoGuardaNada() throws Exception {
        Map<String, Object> malo = mensaje("102", 1);
        autorDe(malo).put("rol", "admin");

        MvcResult r = enviar(lote("lote-1", mensaje("101", 1), malo, mensaje("103", 1)));

        assertThat(r.getResponse().getStatus()).isEqualTo(422);
        assertThat(campos(cuerpo(r))).containsExactly("mensajes[1].autor.rol");
        assertThat(contar("mensajes")).isZero();
        assertThat(contar("lotes_recibidos")).isZero();
    }

    @Test
    void siLaBaseFallaEnMedioSeDeshaceTodo() throws Exception {
        // El 1.er upsert entra de verdad y el 2.º falla dentro de la transacción
        doCallRealMethod().doThrow(new IllegalStateException("falla simulada de la base"))
                .when(upsertRepo).upsert(any());

        MvcResult r = enviar(lote("lote-1", mensaje("101", 1), mensaje("102", 1), mensaje("103", 1)));

        assertThat(r.getResponse().getStatus()).isEqualTo(500);
        assertThat(cuerpo(r).get("codigo").asText()).isEqualTo("ERROR_INTERNO");
        assertThat(r.getResponse().getContentAsString()).doesNotContain("falla simulada");
        assertThat(contar("mensajes")).isZero();
        assertThat(contar("lotes_recibidos")).isZero();
    }

    // ── T04: el carácter NUL se quita al recibir ──

    @Test
    void elCaracterNulSeQuitaDelTextoYDeLaCaja() throws Exception {
        Map<String, Object> conNul = mensaje("102", 1);
        conNul.put("textoOriginal", "hola\u0000mundo");
        autorDe(conNul).put("nombreVisible", "Ana\u0000Pérez");

        MvcResult r = enviar(lote("lote-1", mensaje("101", 1), conNul, mensaje("103", 1)));

        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(cuerpo(r).get("nuevos").asInt()).isEqualTo(3);
        assertThat(jdbc.queryForObject("SELECT texto FROM mensajes WHERE discord_id = '102'", String.class))
                .isEqualTo("holamundo");
        assertThat(jdbc.queryForObject(
                "SELECT contrato->>'textoOriginal' || '|' || (contrato->'autor'->>'nombreVisible') "
                        + "FROM mensajes WHERE discord_id = '102'", String.class))
                .isEqualTo("holamundo|AnaPérez");
    }

    @Test
    void laPuertaGuardaElServidorDelLote() throws Exception {
        enviar(lote("lote-1", mensaje("101", 1)));

        assertThat(jdbc.queryForObject("SELECT servidor_id FROM mensajes WHERE discord_id = '101'", String.class))
                .isEqualTo("1554157903701741700");
    }

    // ── Topes y errores generales ──

    @Test
    void cuerpoDemasiadoGrandeEs413() throws Exception {
        Map<String, Object> m = mensaje("101", 1);
        m.put("textoOriginal", "x".repeat(250_000));

        MvcResult r = enviar(lote("lote-1", m));

        assertThat(r.getResponse().getStatus()).isEqualTo(413);
        assertThat(cuerpo(r).get("codigo").asText()).isEqualTo("CUERPO_DEMASIADO_GRANDE");
    }

    @Test
    void masDeMilMensajesEs422() throws Exception {
        List<Map<String, Object>> muchos = new ArrayList<>();
        for (int i = 0; i < 1001; i++) {
            muchos.add(Map.of());
        }
        Map<String, Object> lote = lote("lote-1");
        lote.put("mensajes", muchos);

        // Cuerpo chico (mensajes vacíos) para no chocar antes con el tope de bytes de esta prueba
        MvcResult r = enviar(lote);

        assertThat(r.getResponse().getStatus()).isEqualTo(422);
        assertThat(campos(cuerpo(r))).contains("mensajes");
    }

    @Test
    void rutaInexistenteEs404ConElFormatoComun() throws Exception {
        MvcResult r = mvc.perform(conClave(get("/api/v1/no-existe"), CLAVE)).andReturn();

        assertThat(r.getResponse().getStatus()).isEqualTo(404);
        assertThat(cuerpo(r).get("codigo").asText()).isEqualTo("NO_ENCONTRADO");
    }

    // ── Ayudas ──

    private MvcResult enviar(Map<String, Object> lote) throws Exception {
        return enviar(lote, CLAVE);
    }

    private MvcResult enviar(Map<String, Object> lote, String clave) throws Exception {
        return enviar(lote, clave, null);
    }

    private MvcResult enviar(Map<String, Object> lote, String clave, String idCorrelacion) throws Exception {
        MockHttpServletRequestBuilder pedido = conClave(post(RUTA), clave)
                .contentType(MediaType.APPLICATION_JSON)
                .content(json.writeValueAsBytes(lote));
        if (idCorrelacion != null) {
            pedido.header("X-Id-Correlacion", idCorrelacion);
        }
        return mvc.perform(pedido).andReturn();
    }

    private static MockHttpServletRequestBuilder conClave(MockHttpServletRequestBuilder pedido, String clave) {
        return pedido.header("X-Api-Key", clave);
    }

    private JsonNode cuerpo(MvcResult r) throws Exception {
        return json.readTree(r.getResponse().getContentAsByteArray());
    }

    private static List<String> campos(JsonNode error) {
        List<String> campos = new ArrayList<>();
        error.get("errores").forEach(e -> campos.add(e.get("campo").asText()));
        return campos;
    }

    private int contar(String tabla) {
        return jdbc.queryForObject("SELECT count(*) FROM " + tabla, Integer.class);
    }

    /** Un lote del contrato v1 (CONTRACT.md §2). */
    @SafeVarargs
    private static Map<String, Object> lote(String loteId, Map<String, Object>... mensajes) {
        Map<String, Object> lote = new LinkedHashMap<>();
        lote.put("versionContrato", "1.0");
        lote.put("loteId", loteId);
        lote.put("fuente", "discord");
        lote.put("modo", "historial");
        lote.put("servidorId", "1554157903701741700");
        lote.put("generadoEn", "2026-09-29T15:00:00.000Z");
        lote.put("mensajes", new ArrayList<>(List.of(mensajes)));
        return lote;
    }

    /** Un mensaje completo del contrato v1 (CONTRACT.md §7), con la cantidad de 🎉 que se pida. */
    private static Map<String, Object> mensaje(String id, int reacciones) {
        Map<String, Object> autor = new LinkedHashMap<>(Map.of(
                "id", "sim-ana-perez", "idDiscord", "1554160711800717417", "nombreUsuario", "Ana Pérez",
                "nombreVisible", "Ana Pérez", "tipo", "persona", "rol", "miembro"));
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", id);
        m.put("canal", Map.of("id", "1554158212742127821", "nombre", "dudas"));
        m.put("hilo", null);
        m.put("fecha", "2026-09-28T18:56:30.331Z");
        m.put("tipo", "mensaje");
        m.put("tipoDiscord", 0);
        m.put("esSimulado", true);
        m.put("autor", autor);
        m.put("textoOriginal", "como instalo pyhton en windows??");
        m.put("tieneTexto", true);
        m.put("tieneBloqueCodigo", false);
        m.put("enlaces", List.of());
        m.put("menciones", Map.of("usuarios", List.of(), "roles", List.of(), "todos", false));
        m.put("mencionaAlBot", false);
        m.put("respondeA", null);
        m.put("adjuntos", List.of());
        Map<String, Object> reaccion = new LinkedHashMap<>();
        reaccion.put("emoji", "🎉");
        reaccion.put("emojiId", null);  // emoji estándar
        reaccion.put("cantidad", reacciones);
        m.put("reacciones", List.of(reaccion));
        m.put("fijado", false);
        m.put("editado", false);
        m.put("editadoEn", null);
        m.put("stickers", List.of());
        m.put("vistasPrevias", List.of());
        m.put("encuesta", null);
        return m;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> primerMensaje(Map<String, Object> lote) {
        return ((List<Map<String, Object>>) lote.get("mensajes")).get(0);
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> autorDe(Map<String, Object> mensaje) {
        return (Map<String, Object>) mensaje.get("autor");
    }
}
