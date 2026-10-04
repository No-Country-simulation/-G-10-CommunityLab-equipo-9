package com.insightedulab.backend_java;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightedulab.backend_java.clasificacion.ClasificacionService;
import com.insightedulab.backend_java.client.IaNoDisponibleException;
import com.insightedulab.backend_java.client.NlpDataClient;
import com.insightedulab.backend_java.client.RespuestaIa;
import com.insightedulab.backend_java.controller.LoteController;
import com.insightedulab.backend_java.controller.MensajeEnVivoController;
import com.insightedulab.backend_java.dto.lote.LoteEntrada;
import com.insightedulab.backend_java.error.ProhibidoException;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository.DatosMensaje;
import com.insightedulab.backend_java.model.enums.AutorRol;
import com.insightedulab.backend_java.model.enums.AutorTipo;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import java.net.URI;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Puerta en vivo del bot, POST /api/v1/mensajes/en-vivo (T05), contra PostgreSQL real
 * y con la IA simulada (Mockito, como en ClasificacionTest). Pasa por los filtros de la API key.
 * ⚠️ Vacían las tablas: solo corren en una base *_test.
 */
@SpringBootTest(properties = {
        "seguridad.api-keys.ingesta=" + EnVivoApiTest.CLAVE_INGESTA,
        "seguridad.api-keys.bot=" + EnVivoApiTest.CLAVE_BOT,
        "clasificacion.habilitada=false",  // las pruebas llaman a procesarTanda() cuando lo necesitan
        "clasificacion.max-intentos=3",
})
@AutoConfigureMockMvc
class EnVivoApiTest {

    static final String CLAVE_INGESTA = "clave-de-prueba-ingesta-0123456789";
    static final String CLAVE_BOT = "clave-de-prueba-bot-0123456789";
    private static final String RUTA = "/api/v1/mensajes/en-vivo";
    private static final String ID = "1554205178671009863";
    private static final String TEXTO_IA = "Al instalar Python marca la casilla 'Add python.exe to PATH'.";
    private static final String FUENTE = "06_Manual_del_Estudiante_V3.pdf (Pág. 4)";

    @MockitoBean NlpDataClient ia;
    @Autowired ClasificacionService clasificacion;
    @Autowired MensajeUpsertRepository upsert;
    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;
    @Autowired ObjectMapper json;

    @BeforeEach
    void vaciarTablas() {
        String base = jdbc.queryForObject("SELECT current_database()", String.class);
        assertThat(base).as("Las pruebas solo corren en una base *_test").endsWith("_test");
        jdbc.execute("TRUNCATE borradores, mensajes, lotes_recibidos RESTART IDENTITY CASCADE");
    }

    // ── Caso 1: duda con respuesta encontrada ──

    @Test
    void dudaConRespuestaEncontradaDaResponderYSeGuardaLaRespuesta() throws Exception {
        iaResponde(id -> duda(id, new RespuestaIa.Respuesta(TEXTO_IA, true, List.of(FUENTE), null)));

        JsonNode orden = cuerpo(enviar(enVivo("vivo-1", mensaje(ID, 1))));

        assertThat(orden.get("versionContratoBot").asText()).isEqualTo("1.0");
        assertThat(orden.get("discordId").asText()).isEqualTo(ID);
        assertThat(orden.get("orden").asText()).isEqualTo("RESPONDER");
        // Tal cual, sin pie de fuentes: el Agente FAQ ya cita en el texto el documento que usó
        assertThat(orden.get("texto").asText()).isEqualTo(TEXTO_IA);
        assertThat(orden.get("reaccion").isNull()).isTrue();
        Map<String, Object> f = fila(ID);
        assertThat(f).containsEntry("estado_clasificacion", "OK").containsEntry("intencion", "PREGUNTA_FAQ")
                .containsEntry("tema", "herramientas_entorno").containsEntry("intentos_clasificacion", 1)
                .containsEntry("reservado_hasta", null)
                .containsEntry("respuesta_estado", "RESPONDIDA").containsEntry("respuesta_texto", TEXTO_IA);
        assertThat(json.readTree(f.get("respuesta_fuentes").toString())).isEqualTo(json.valueToTree(List.of(FUENTE)));
        assertThat(f.get("respondido_en")).isNotNull();
    }

    @Test
    void laIaRecibeElMensajeEnTiempoRealConElLoteIdDelBot() throws Exception {
        iaResponde(id -> comentario(id));
        Map<String, Object> mensaje = mensaje(ID, 1);

        enviar(enVivo("vivo-1", mensaje));

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> lote = ArgumentCaptor.forClass(Map.class);
        verify(ia).procesar(lote.capture(), anyString());
        Map<String, Object> enviado = lote.getValue();
        assertThat(enviado.get("modo")).isEqualTo("tiempoReal");
        assertThat(enviado.get("loteId")).isEqualTo("vivo-1");
        assertThat(enviado.get("servidorId")).isEqualTo("1554157903701741700");
        assertThat(cajas(enviado)).containsExactly(json.convertValue(mensaje, Map.class));
    }

    @Test
    void unaRespuestaLargaSeRecortaAlMaximoDeDiscord() throws Exception {
        iaResponde(id -> duda(id, new RespuestaIa.Respuesta("a".repeat(3000), true, List.of(FUENTE), null)));

        String texto = cuerpo(enviar(enVivo("vivo-1", mensaje(ID, 1)))).get("texto").asText();

        assertThat(texto).hasSize(2000).endsWith("…").doesNotContain("Fuente");
    }

    // ── Caso 2: duda sin respuesta, o con el tope agotado ──

    @Test
    void dudaSinRespuestaDaDerivar() throws Exception {
        iaResponde(id -> duda(id, new RespuestaIa.Respuesta("Quizás sea el PATH", false, List.of(FUENTE),
                "Fidelidad media (0.75 < 0.85).")));

        JsonNode orden = cuerpo(enviar(enVivo("vivo-1", mensaje(ID, 1))));

        assertThat(orden.get("orden").asText()).isEqualTo("DERIVAR");
        assertThat(orden.get("texto").asText()).contains("un mentor te responderá").doesNotContain("PATH");
        assertThat(fila(ID)).containsEntry("estado_clasificacion", "OK").containsEntry("respuesta_estado", "DERIVADA")
                .containsEntry("respuesta_texto", null).containsEntry("respuesta_fuentes", null);
        assertThat(fila(ID).get("respondido_en")).isNotNull();
    }

    @Test
    void dudaConElTopeAgotadoDaDerivar() throws Exception {
        iaResponde(id -> duda(id, new RespuestaIa.Respuesta("", false, List.of(),
                "Se agotó el tope de 25 s del pedido en tiempo real.")));

        JsonNode orden = cuerpo(enviar(enVivo("vivo-1", mensaje(ID, 1))));

        assertThat(orden.get("orden").asText()).isEqualTo("DERIVAR");
        assertThat(fila(ID)).containsEntry("respuesta_estado", "DERIVADA").containsEntry("intencion", "PREGUNTA_FAQ");
    }

    // ── Caso 3: testimonio y comentario ──

    @Test
    void testimonioDaReaccionarSinTexto() throws Exception {
        iaResponde(id -> new RespuestaIa.Resultado(id, "OK", "llm", "TESTIMONIO", 0.95, "MUY_POSITIVO", "empleo", "logro"));

        JsonNode orden = cuerpo(enviar(enVivo("vivo-1", mensaje(ID, 1))));

        assertThat(orden.get("orden").asText()).isEqualTo("REACCIONAR");
        assertThat(orden.get("reaccion").asText()).isEqualTo("🎉");
        assertThat(orden.get("texto").isNull()).isTrue();  // F5
        assertThat(fila(ID)).containsEntry("estado_clasificacion", "OK").containsEntry("intencion", "TESTIMONIO")
                .containsEntry("sentimiento", "MUY_POSITIVO").containsEntry("respuesta_estado", null)
                .containsEntry("respondido_en", null);
    }

    @Test
    void comentarioDaNadaYGuardaSusEtiquetas() throws Exception {
        iaResponde(id -> comentario(id));

        JsonNode orden = cuerpo(enviar(enVivo("vivo-1", mensaje(ID, 1))));

        assertThat(orden.get("orden").asText()).isEqualTo("NADA");
        assertThat(fila(ID)).containsEntry("estado_clasificacion", "OK").containsEntry("intencion", "COMENTARIO")
                .containsEntry("respuesta_estado", null);
    }

    // ── Caso 4: la IA falla ──

    @Test
    void siLaIaFallaDaNadaYLoClasificaLaSiguienteVueltaEnSegundoPlano() throws Exception {
        when(ia.procesar(any(), anyString())).thenThrow(new IaNoDisponibleException("La IA respondió HTTP 500"));

        MvcResult r = enviar(enVivo("vivo-1", mensaje(ID, 1)));

        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(cuerpo(r).get("orden").asText()).isEqualTo("NADA");
        assertThat(fila(ID)).containsEntry("estado_clasificacion", "PENDIENTE").containsEntry("intentos_clasificacion", 1)
                .containsEntry("reservado_hasta", null).containsEntry("respuesta_estado", null);

        // La IA vuelve: la tarea en segundo plano lo toma enseguida, en modo historial
        iaResponde(id -> comentario(id));
        assertThat(clasificacion.procesarTanda().ok()).isEqualTo(1);
        assertThat(fila(ID)).containsEntry("estado_clasificacion", "OK").containsEntry("intentos_clasificacion", 2);
    }

    @Test
    void unErrorDeLaIaEnElMensajeDaNadaYSumaUnIntento() throws Exception {
        iaResponde(id -> new RespuestaIa.Resultado(id, "ERROR", "llm", null, null, null, null, "El LLM no respondió en 20 s."));

        JsonNode orden = cuerpo(enviar(enVivo("vivo-1", mensaje(ID, 1))));

        assertThat(orden.get("orden").asText()).isEqualTo("NADA");
        assertThat(fila(ID)).containsEntry("estado_clasificacion", "PENDIENTE").containsEntry("intentos_clasificacion", 1)
                .containsEntry("reservado_hasta", null).containsEntry("intencion", null);
    }

    @Test
    void siElMensajeCambioMientrasLaIaPensabaNoSeResponde() throws Exception {
        when(ia.procesar(any(), anyString())).thenAnswer(inv -> {
            // Mientras la IA "piensa", llega el lote de la hora con el texto editado
            upsert.upsert(datos(ID, "texto editado"));
            return respuesta(inv.getArgument(0), id -> duda(id, new RespuestaIa.Respuesta(TEXTO_IA, true, List.of(FUENTE), null)));
        });

        JsonNode orden = cuerpo(enviar(enVivo("vivo-1", mensaje(ID, 1))));

        assertThat(orden.get("orden").asText()).isEqualTo("NADA");
        assertThat(fila(ID)).containsEntry("estado_clasificacion", "PENDIENTE").containsEntry("reservado_hasta", null)
                .containsEntry("respuesta_estado", null).containsEntry("intencion", null);
    }

    // ── Caso 5: la clasificación en segundo plano no lo toma mientras se procesa en vivo ──

    @Test
    void mientrasLaPuertaEnVivoEsperaALaIaLaTareaEnSegundoPlanoNoLoToma() throws Exception {
        List<ClasificacionService.Resumen> vueltas = new ArrayList<>();
        when(ia.procesar(any(), anyString())).thenAnswer(inv -> {
            vueltas.add(clasificacion.procesarTanda());  // corre justo mientras la IA "piensa"
            return respuesta(inv.getArgument(0), this::comentario);
        });

        enviar(enVivo("vivo-1", mensaje(ID, 1)));

        assertThat(vueltas).hasSize(1);
        assertThat(vueltas.get(0).tomados()).isZero();
        verify(ia, times(1)).procesar(any(), anyString());  // una sola llamada a la IA
        assertThat(clasificacion.procesarTanda().tomados()).isZero();  // y después ya está OK
    }

    // ── Caso 6: el mismo mensaje dos veces ──

    @Test
    void elMismoMensajeDosVecesNoSeVuelveAResponder() throws Exception {
        iaResponde(id -> duda(id, new RespuestaIa.Respuesta(TEXTO_IA, true, List.of(FUENTE), null)));
        assertThat(cuerpo(enviar(enVivo("vivo-1", mensaje(ID, 1)))).get("orden").asText()).isEqualTo("RESPONDER");

        JsonNode segunda = cuerpo(enviar(enVivo("vivo-2", mensaje(ID, 1))));

        assertThat(segunda.get("orden").asText()).isEqualTo("NADA");
        verify(ia, times(1)).procesar(any(), anyString());
        assertThat(contar("mensajes")).isEqualTo(1);
    }

    @Test
    void unMensajeQueYaClasificoElLoteDeLaHoraNoSeEnviaALaIa() throws Exception {
        upsert.upsert(datos(ID, "como instalo pyhton en windows??"));
        jdbc.update("UPDATE mensajes SET estado_clasificacion = 'OK', intencion = 'PREGUNTA_FAQ'");

        JsonNode orden = cuerpo(enviar(enVivo("vivo-1", mensaje(ID, 1))));

        assertThat(orden.get("orden").asText()).isEqualTo("NADA");
        verifyNoInteractions(ia);
    }

    // ── Caso 7: después llega el lote de la hora con el mismo mensaje ──

    @Test
    void elLoteDeLaHoraNoDuplicaNiCambiaLasEtiquetasNiLaRespuesta() throws Exception {
        iaResponde(id -> duda(id, new RespuestaIa.Respuesta(TEXTO_IA, true, List.of(FUENTE), null)));
        enviar(enVivo("vivo-1", mensaje(ID, 1)));
        Map<String, Object> antes = fila(ID);

        // Idéntico (el bot y la ingesta arman el mismo contrato) y, después, con una reacción más
        JsonNode igual = cuerpo(enviarLote(historial("lote-1", mensaje(ID, 1)), CLAVE_INGESTA));
        JsonNode conReaccion = cuerpo(enviarLote(historial("lote-2", mensaje(ID, 2)), CLAVE_INGESTA));

        assertThat(igual.get("sinCambios").asInt()).isEqualTo(1);
        assertThat(conReaccion.get("actualizados").asInt()).isEqualTo(1);
        assertThat(contar("mensajes")).isEqualTo(1);
        Map<String, Object> despues = fila(ID);
        for (String columna : List.of("estado_clasificacion", "intencion", "confianza", "sentimiento", "tema",
                "respuesta_estado", "respuesta_texto", "respondido_en")) {
            assertThat(despues.get(columna)).as(columna).isEqualTo(antes.get(columna));
        }
        assertThat(despues.get("respuesta_fuentes").toString()).isEqualTo(antes.get("respuesta_fuentes").toString());
        verify(ia, times(1)).procesar(any(), anyString());
    }

    // ── Caso 8: cada clave abre solo su puerta (DEC-70) ──

    @Test
    void sinClaveEs401() throws Exception {
        MvcResult r = mvc.perform(post(RUTA).contentType(MediaType.APPLICATION_JSON)
                .content(json.writeValueAsBytes(enVivo("vivo-1", mensaje(ID, 1))))).andReturn();

        assertThat(r.getResponse().getStatus()).isEqualTo(401);
        verifyNoInteractions(ia);
    }

    @Test
    void laClaveDeLaIngestaEnLaPuertaEnVivoEs403() throws Exception {
        MvcResult r = enviar(enVivo("vivo-1", mensaje(ID, 1)), CLAVE_INGESTA);

        assertThat(r.getResponse().getStatus()).isEqualTo(403);
        assertThat(cuerpo(r).get("codigo").asText()).isEqualTo("PROHIBIDO");
        assertThat(r.getResponse().getContentAsString()).doesNotContain(CLAVE_INGESTA);
        assertThat(contar("mensajes")).isZero();
        verifyNoInteractions(ia);
    }

    @Test
    void laClaveDelBotEnLaPuertaDeLotesEs403() throws Exception {
        MvcResult r = enviarLote(historial("lote-1", mensaje(ID, 1)), CLAVE_BOT);

        assertThat(r.getResponse().getStatus()).isEqualTo(403);
        assertThat(cuerpo(r).get("codigo").asText()).isEqualTo("PROHIBIDO");
        assertThat(contar("mensajes")).isZero();
        assertThat(contar("lotes_recibidos")).isZero();
    }

    // ── Auditoría de T05: la regla de DEC-70 no se esquiva escribiendo la ruta de otra forma ──

    @ParameterizedTest
    @ValueSource(strings = {"/api/v1/lotes;x=1", "/api/v1/lote%73", "/api//v1/lotes"})
    void laClaveDelBotNoEntraALotesConUnaRutaDisfrazada(String ruta) throws Exception {
        MvcResult r = enviarA(ruta, historial("lote-1", mensaje(ID, 1)), CLAVE_BOT);

        assertThat(r.getResponse().getStatus()).as(ruta).isEqualTo(403);
        assertThat(cuerpo(r).get("codigo").asText()).isEqualTo("PROHIBIDO");
        assertThat(contar("mensajes")).isZero();
        assertThat(contar("lotes_recibidos")).isZero();
    }

    @ParameterizedTest
    @ValueSource(strings = {"/api/v1/mensajes/en-vivo;x=1", "/api/v1/mensajes/en-viv%6F", "/api//v1/mensajes/en-vivo"})
    void laClaveDeLaIngestaNoEntraALaPuertaEnVivoConUnaRutaDisfrazada(String ruta) throws Exception {
        MvcResult r = enviarA(ruta, enVivo("vivo-1", mensaje(ID, 1)), CLAVE_INGESTA);

        assertThat(r.getResponse().getStatus()).as(ruta).isEqualTo(403);
        assertThat(cuerpo(r).get("codigo").asText()).isEqualTo("PROHIBIDO");
        assertThat(contar("mensajes")).isZero();
        verifyNoInteractions(ia);
    }

    @Test
    void elClienteCorrectoConUnPuntoYComaEnLaRutaSigueFuncionando() throws Exception {
        iaResponde(id -> comentario(id));

        MvcResult r = enviarA("/api/v1/mensajes/en-vivo;x=1", enVivo("vivo-1", mensaje(ID, 1)), CLAVE_BOT);

        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(cuerpo(r).get("orden").asText()).isEqualTo("NADA");
    }

    @Test
    void cadaControladorExigeSuClienteAunqueElFiltroNoLoFrene() {
        // Segunda capa: se llama al controlador directo, como si una ruta rara hubiera pasado el filtro
        MensajeEnVivoController enVivo = new MensajeEnVivoController(null);
        LoteController lotes = new LoteController(null);
        LoteEntrada lote = json.convertValue(enVivo("vivo-1", mensaje(ID, 1)), LoteEntrada.class);

        assertThatThrownBy(() -> enVivo.recibir("ingesta", lote)).isInstanceOf(ProhibidoException.class);
        assertThatThrownBy(() -> enVivo.recibir(null, lote)).isInstanceOf(ProhibidoException.class);
        assertThatThrownBy(() -> lotes.recibir("bot", lote)).isInstanceOf(ProhibidoException.class);
        assertThatThrownBy(() -> lotes.recibir(null, lote)).isInstanceOf(ProhibidoException.class);
    }

    // ── Caso 9: la puerta en vivo recibe un mensaje en tiempoReal ──

    @Test
    void dosMensajesEs422() throws Exception {
        MvcResult r = enviar(enVivo("vivo-1", mensaje(ID, 1), mensaje("1554205178671009864", 1)));

        assertThat(r.getResponse().getStatus()).isEqualTo(422);
        assertThat(cuerpo(r).get("codigo").asText()).isEqualTo("CONTRATO_INVALIDO");
        assertThat(cuerpo(r).get("errores").get(0).get("campo").asText()).isEqualTo("mensajes");
        assertThat(contar("mensajes")).isZero();
        verifyNoInteractions(ia);
    }

    @Test
    void modoHistorialEs422() throws Exception {
        MvcResult r = enviar(historial("vivo-1", mensaje(ID, 1)));

        assertThat(r.getResponse().getStatus()).isEqualTo(422);
        assertThat(cuerpo(r).get("errores").get(0).get("campo").asText()).isEqualTo("modo");
        assertThat(contar("mensajes")).isZero();
        verifyNoInteractions(ia);
    }

    @Test
    @SuppressWarnings("unchecked")
    void unMensajeQueNoCumpleElContratoEs422SinRepetirLosDatos() throws Exception {
        Map<String, Object> mensaje = mensaje(ID, 1);
        ((Map<String, Object>) mensaje.get("autor")).put("tipo", "HUMANO");

        MvcResult r = enviar(enVivo("vivo-1", mensaje));

        assertThat(r.getResponse().getStatus()).isEqualTo(422);
        assertThat(cuerpo(r).get("errores").get(0).get("campo").asText()).isEqualTo("mensajes[0].autor.tipo");
        assertThat(r.getResponse().getContentAsString()).doesNotContain("HUMANO");  // S7
        assertThat(contar("mensajes")).isZero();
        verifyNoInteractions(ia);
    }

    @Test
    void elMensajeEnVivoNoSeRegistraEnLotesRecibidos() throws Exception {
        iaResponde(id -> comentario(id));

        enviar(enVivo("vivo-1", mensaje(ID, 1)));

        assertThat(contar("mensajes")).isEqualTo(1);
        assertThat(contar("lotes_recibidos")).isZero();
    }

    // ── Ayudas ──

    private MvcResult enviar(Map<String, Object> lote) throws Exception {
        return enviar(lote, CLAVE_BOT);
    }

    private MvcResult enviar(Map<String, Object> lote, String clave) throws Exception {
        return mvc.perform(post(RUTA).header("X-Api-Key", clave).contentType(MediaType.APPLICATION_JSON)
                .content(json.writeValueAsBytes(lote))).andReturn();
    }

    /** Con la ruta tal cual, sin que MockMvc la codifique (por ejemplo, para enviar %73 o ;x=1). */
    private MvcResult enviarA(String ruta, Map<String, Object> lote, String clave) throws Exception {
        return mvc.perform(post(URI.create(ruta)).header("X-Api-Key", clave).contentType(MediaType.APPLICATION_JSON)
                .content(json.writeValueAsBytes(lote))).andReturn();
    }

    private MvcResult enviarLote(Map<String, Object> lote, String clave) throws Exception {
        return mvc.perform(post("/api/v1/lotes").header("X-Api-Key", clave).contentType(MediaType.APPLICATION_JSON)
                .content(json.writeValueAsBytes(lote))).andReturn();
    }

    private JsonNode cuerpo(MvcResult r) throws Exception {
        return json.readTree(r.getResponse().getContentAsByteArray());
    }

    private int contar(String tabla) {
        return jdbc.queryForObject("SELECT count(*) FROM " + tabla, Integer.class);
    }

    private void iaResponde(Function<String, RespuestaIa.Resultado> porId) {
        // doAnswer y no when(...): when llamaría al simulador, que en algunas pruebas lanza una excepción
        doAnswer(inv -> respuesta(inv.getArgument(0), porId)).when(ia).procesar(any(), anyString());
    }

    private RespuestaIa respuesta(Map<String, Object> lote, Function<String, RespuestaIa.Resultado> porId) {
        List<RespuestaIa.Resultado> resultados = new ArrayList<>();
        for (Map<String, Object> c : cajas(lote)) {
            resultados.add(porId.apply((String) c.get("id")));
        }
        return new RespuestaIa("1.0", (String) lote.get("loteId"), resultados, new RespuestaIa.Metricas(10, 100, 20));
    }

    private static RespuestaIa.Resultado duda(String id, RespuestaIa.Respuesta respuesta) {
        return new RespuestaIa.Resultado(id, "OK", "llm", "PREGUNTA_FAQ", 0.93, "NEGATIVO", "herramientas_entorno",
                "pregunta", respuesta);
    }

    private RespuestaIa.Resultado comentario(String id) {
        return new RespuestaIa.Resultado(id, "OK", "llm", "COMENTARIO", 0.8, "POSITIVO", "comunidad", "opinión");
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> cajas(Map<String, Object> lote) {
        return (List<Map<String, Object>>) lote.get("mensajes");
    }

    private Map<String, Object> fila(String discordId) {
        return jdbc.queryForMap("""
                SELECT estado_clasificacion, intencion, confianza, sentimiento, tema, intentos_clasificacion,
                       reservado_hasta, respuesta_estado, respuesta_texto, respuesta_fuentes, respondido_en
                  FROM mensajes WHERE discord_id = ?""", discordId);
    }

    private static DatosMensaje datos(String id, String texto) {
        return new DatosMensaje(id, "1554158212742127821", "sim-ana-perez", AutorTipo.persona, AutorRol.miembro,
                true, Instant.parse("2026-09-28T18:56:30.331Z"), null, texto, mensaje(id, 1), "1.0",
                "1554157903701741700");
    }

    @SafeVarargs
    private static Map<String, Object> enVivo(String loteId, Map<String, Object>... mensajes) {
        Map<String, Object> lote = historial(loteId, mensajes);
        lote.put("modo", "tiempoReal");
        return lote;
    }

    /** Un lote del contrato v1 (CONTRACT.md §2). */
    @SafeVarargs
    private static Map<String, Object> historial(String loteId, Map<String, Object>... mensajes) {
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
        reaccion.put("emojiId", null);
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
}
