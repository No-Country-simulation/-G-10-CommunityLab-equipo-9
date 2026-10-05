package com.insightedulab.backend_java;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightedulab.backend_java.client.NlpDataClient;
import com.insightedulab.backend_java.controller.DashboardController;
import com.insightedulab.backend_java.dashboard.DashboardService;
import com.insightedulab.backend_java.error.ProhibidoException;
import com.insightedulab.backend_java.model.enums.AutorRol;
import com.insightedulab.backend_java.model.enums.AutorTipo;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository.DatosMensaje;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import java.net.URI;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/**
 * Puertas del dashboard (T08, PANEL_JAVA_v1.md §7) contra PostgreSQL real, con datos armados en cada prueba.
 * ⚠️ Vacían las tablas: solo corren en una base *_test.
 */
// Las mismas propiedades (y el mismo @MockitoBean) que CuraduriaApiTest, en el mismo orden: así Spring reutiliza
// ese contexto. Cada contexto distinto abre su propio grupo de conexiones, y con uno más PostgreSQL se queda sin
// conexiones ("too many clients"). La zona del dashboard es la de application.properties (America/Bogota)
@SpringBootTest(properties = {
        "seguridad.api-keys.ingesta=" + CuraduriaApiTest.CLAVE_INGESTA,
        "seguridad.api-keys.bot=" + CuraduriaApiTest.CLAVE_BOT,
        "seguridad.api-keys.panel=" + CuraduriaApiTest.CLAVE_PANEL,
        "clasificacion.habilitada=false",
        "generacion.habilitada=false",
        "faq.habilitada=false",
        "clasificacion.max-intentos=3",
        "generacion.max-intentos=3",
})
@AutoConfigureMockMvc
class DashboardApiTest {

    static final String CLAVE_INGESTA = CuraduriaApiTest.CLAVE_INGESTA;
    static final String CLAVE_BOT = CuraduriaApiTest.CLAVE_BOT;
    static final String CLAVE_PANEL = CuraduriaApiTest.CLAVE_PANEL;
    private static final ZoneId BOGOTA = ZoneId.of("America/Bogota");
    private static final String SCRIPT = "<script>alert(1)</script> ¿cómo instalo python?";

    @MockitoBean NlpDataClient ia;  // el dashboard no usa la IA: que ninguna prueba la llame de verdad
    @Autowired DashboardService dashboard;
    @Autowired MensajeUpsertRepository upsert;
    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;
    @Autowired ObjectMapper json;

    private final AtomicLong ids = new AtomicLong(1000);

    @BeforeEach
    void vaciarTablas() {
        String base = jdbc.queryForObject("SELECT current_database()", String.class);
        assertThat(base).as("Las pruebas solo corren en una base *_test").endsWith("_test");
        jdbc.execute("TRUNCATE faq_semanas, borradores, mensajes, lotes_recibidos RESTART IDENTITY CASCADE");
    }

    // ── Caso 1: sentimiento por día y por semana ──

    @Test
    void sentimientoPorDiaCuentaSoloOkDePersonasConSentimiento() throws Exception {
        etiquetado("ana", Instant.parse("2026-09-28T15:00:00Z"), "COMENTARIO", "POSITIVO", "comunidad");
        // 03:00 UTC del 29 son las 22:00 del 28 en Bogotá: cuenta el 28
        etiquetado("beto", Instant.parse("2026-09-29T03:00:00Z"), "COMENTARIO", "NEGATIVO", "comunidad");
        etiquetado("ana", Instant.parse("2026-09-30T15:00:00Z"), "COMENTARIO", "NEUTRO", "comunidad");
        // Lo que no cuenta
        String pendiente = mensaje("ana", Instant.parse("2026-09-28T16:00:00Z"));
        String error = etiquetado("ana", Instant.parse("2026-09-28T17:00:00Z"), "COMENTARIO", "POSITIVO", "comunidad");
        jdbc.update("UPDATE mensajes SET estado_clasificacion = 'ERROR' WHERE discord_id = ?", error);
        etiquetado(AutorTipo.botPropio, AutorRol.miembro, "bot", Instant.parse("2026-09-28T18:00:00Z"),
                "OTRO", "POSITIVO", "comunidad");
        etiquetado("ana", Instant.parse("2026-09-28T19:00:00Z"), "OTRO", null, null);
        etiquetado("ana", Instant.parse("2026-10-10T15:00:00Z"), "COMENTARIO", "POSITIVO", "comunidad");  // fuera
        assertThat(pendiente).isNotNull();

        JsonNode r = pedir("/api/v1/dashboard/sentimiento?desde=2026-09-28&hasta=2026-10-01&agrupar=dia");

        assertThat(r.get("agrupar").asText()).isEqualTo("dia");
        JsonNode puntos = r.get("puntos");
        assertThat(puntos).hasSize(4);  // también los días sin mensajes
        assertThat(puntos.get(0).get("inicio").asText()).isEqualTo("2026-09-28");
        assertThat(cantidades(puntos.get(0))).containsEntry("POSITIVO", 1L).containsEntry("NEGATIVO", 1L)
                .containsEntry("NEUTRO", 0L).containsEntry("MUY_POSITIVO", 0L).containsEntry("MUY_NEGATIVO", 0L);
        assertThat(cantidades(puntos.get(1)).values()).containsOnly(0L);
        assertThat(cantidades(puntos.get(2))).containsEntry("NEUTRO", 1L);
        assertThat(cantidades(puntos.get(3)).values()).containsOnly(0L);
    }

    @Test
    void sentimientoPorSemanaEmpiezaElLunesYPuedeExcluirElTemaOtro() throws Exception {
        etiquetado("ana", Instant.parse("2026-09-28T15:00:00Z"), "COMENTARIO", "POSITIVO", "comunidad");  // lunes
        etiquetado("ana", Instant.parse("2026-10-04T15:00:00Z"), "COMENTARIO", "POSITIVO", "otro");       // domingo
        etiquetado("beto", Instant.parse("2026-10-05T15:00:00Z"), "COMENTARIO", "NEGATIVO", "comunidad"); // lunes

        JsonNode todo = pedir("/api/v1/dashboard/sentimiento?desde=2026-09-30&hasta=2026-10-06&agrupar=semana");
        JsonNode sinOtro = pedir("/api/v1/dashboard/sentimiento?desde=2026-09-30&hasta=2026-10-06&agrupar=semana&excluirOtro=true");

        // Las semanas se nombran por su lunes, aunque el período empiece un miércoles
        assertThat(todo.get("puntos")).hasSize(2);
        assertThat(todo.get("puntos").get(0).get("inicio").asText()).isEqualTo("2026-09-28");
        assertThat(cantidades(todo.get("puntos").get(0))).containsEntry("POSITIVO", 1L);  // el del 28 queda fuera del período
        assertThat(cantidades(todo.get("puntos").get(1))).containsEntry("NEGATIVO", 1L);
        assertThat(cantidades(sinOtro.get("puntos").get(0))).containsEntry("POSITIVO", 0L);
        assertThat(sinOtro.get("excluirOtro").asBoolean()).isTrue();
    }

    // ── Caso 2: temas con el período anterior ──

    @Test
    void temasComparanConElPeriodoAnteriorDeIgualLargo() throws Exception {
        // Período 2026-10-01..10-10 (10 días); el anterior es 09-21..09-30
        etiquetado("ana", Instant.parse("2026-10-02T15:00:00Z"), "PREGUNTA_FAQ", "NEUTRO", "empleo");
        etiquetado("beto", Instant.parse("2026-10-03T15:00:00Z"), "TESTIMONIO", "MUY_POSITIVO", "empleo");
        etiquetado("ana", Instant.parse("2026-09-25T15:00:00Z"), "PREGUNTA_FAQ", "NEUTRO", "empleo");
        etiquetado("ana", Instant.parse("2026-10-04T15:00:00Z"), "OTRO", "NEUTRO", "otro");
        etiquetado("ana", Instant.parse("2026-09-22T15:00:00Z"), "PREGUNTA_FAQ", "NEUTRO", "contenido_curso");
        etiquetado("beto", Instant.parse("2026-09-23T15:00:00Z"), "PREGUNTA_FAQ", "NEUTRO", "contenido_curso");
        etiquetado("beto", Instant.parse("2026-09-10T15:00:00Z"), "PREGUNTA_FAQ", "NEUTRO", "contenido_curso");  // fuera

        JsonNode r = pedir("/api/v1/dashboard/temas?desde=2026-10-01&hasta=2026-10-10");
        JsonNode sinOtro = pedir("/api/v1/dashboard/temas?desde=2026-10-01&hasta=2026-10-10&excluirOtro=true");

        assertThat(r.get("periodoAnterior").get("desde").asText()).isEqualTo("2026-09-21");
        assertThat(r.get("periodoAnterior").get("hasta").asText()).isEqualTo("2026-09-30");
        Map<String, long[]> temas = temas(r);
        assertThat(temas.keySet()).containsExactly("empleo", "otro", "contenido_curso");
        assertThat(temas.get("empleo")).containsExactly(2, 1, 1);
        assertThat(temas.get("otro")).containsExactly(1, 0, 1);
        assertThat(temas.get("contenido_curso")).containsExactly(0, 2, -2);
        assertThat(temas(sinOtro).keySet()).containsExactly("empleo", "contenido_curso");
    }

    // ── Caso 3: deserción ──

    @Test
    void desercionCon14YCon3Dias() throws Exception {
        Instant ahora = Instant.now();
        mensaje("camila", ahora.minus(Duration.ofDays(25)));
        etiquetado("camila", ahora.minus(Duration.ofDays(20)), "COMENTARIO", "NEUTRO", "comunidad");
        mensaje("diego", ahora.minus(Duration.ofDays(5)));
        mensaje("elena", ahora.minus(Duration.ofDays(1)));
        etiquetado(AutorTipo.persona, AutorRol.mentor, "andres", ahora.minus(Duration.ofDays(30)), "COMENTARIO", "NEUTRO", "comunidad");
        etiquetado(AutorTipo.botPropio, AutorRol.miembro, "bot", ahora.minus(Duration.ofDays(30)), "OTRO", null, null);

        JsonNode con14 = pedir("/api/v1/dashboard/desercion");
        JsonNode con3 = pedir("/api/v1/dashboard/desercion?dias=3");

        assertThat(con14.get("dias").asInt()).isEqualTo(14);
        assertThat(nombres(con14.get("personas"))).containsExactly("Camila");
        JsonNode camila = con14.get("personas").get(0);
        assertThat(camila.get("mensajes").asLong()).isEqualTo(2);
        assertThat(camila.get("diasSinEscribir").asLong()).isEqualTo(20);
        assertThat(nombres(con3.get("personas"))).containsExactly("Camila", "Diego");  // el más antiguo primero
    }

    // ── Caso 4: frustración (DEC-121) ──

    @Test
    void frustracionUnMuyNegativoODosNegativosDeLosUltimosTres() throws Exception {
        Instant ahora = Instant.now();
        // Un MUY_NEGATIVO en el período, aunque después esté contenta
        etiquetado("ana", dias(ahora, 6), "COMENTARIO", "MUY_NEGATIVO", "comunidad");
        etiquetado("ana", dias(ahora, 5), "COMENTARIO", "POSITIVO", "comunidad");
        etiquetado("ana", dias(ahora, 4), "COMENTARIO", "POSITIVO", "comunidad");
        etiquetado("ana", dias(ahora, 3), "COMENTARIO", "POSITIVO", "comunidad");
        // 2 negativos entre sus últimos 3
        etiquetado("beto", dias(ahora, 5), "COMENTARIO", "NEGATIVO", "comunidad");
        etiquetado("beto", dias(ahora, 4), "COMENTARIO", "POSITIVO", "comunidad");
        etiquetado("beto", dias(ahora, 3), "COMENTARIO", "NEGATIVO", "comunidad");
        // 1 negativo de los últimos 3 (el otro negativo es el cuarto más reciente): sin alerta
        etiquetado("caro", dias(ahora, 6), "COMENTARIO", "NEGATIVO", "comunidad");
        etiquetado("caro", dias(ahora, 5), "COMENTARIO", "NEGATIVO", "comunidad");
        etiquetado("caro", dias(ahora, 4), "COMENTARIO", "POSITIVO", "comunidad");
        etiquetado("caro", dias(ahora, 3), "COMENTARIO", "NEUTRO", "comunidad");
        // Un mentor con MUY_NEGATIVO no es una alerta (las alertas son de alumnos)
        etiquetado(AutorTipo.persona, AutorRol.mentor, "andres", dias(ahora, 2), "COMENTARIO", "MUY_NEGATIVO", "comunidad");
        // Un MUY_NEGATIVO sin clasificar OK no cuenta
        String pendiente = etiquetado("dani", dias(ahora, 2), "COMENTARIO", "MUY_NEGATIVO", "comunidad");
        jdbc.update("UPDATE mensajes SET estado_clasificacion = 'PENDIENTE' WHERE discord_id = ?", pendiente);

        JsonNode r = pedir("/api/v1/dashboard/frustracion");

        JsonNode personas = r.get("personas");
        assertThat(nombres(personas)).containsExactly("Beto", "Ana");  // el último negativo más reciente primero
        JsonNode beto = personas.get(0);
        assertThat(beto.get("motivos")).hasSize(1);
        assertThat(beto.get("motivos").get(0).asText()).isEqualTo("DOS_DE_TRES");
        assertThat(beto.get("negativosEnUltimos3").asLong()).isEqualTo(2);
        assertThat(beto.get("negativosEnPeriodo").asLong()).isEqualTo(2);
        assertThat(personas.get(1).get("motivos").get(0).asText()).isEqualTo("MUY_NEGATIVO");
        // Sin textos en la lista
        assertThat(personas.toString()).doesNotContain("texto");
    }

    @Test
    void unMuyNegativoFueraDelPeriodoNoEsAlertaSiLosUltimosTresEstanBien() throws Exception {
        etiquetado("ana", Instant.parse("2026-08-01T15:00:00Z"), "COMENTARIO", "MUY_NEGATIVO", "comunidad");
        etiquetado("ana", Instant.parse("2026-09-28T15:00:00Z"), "COMENTARIO", "POSITIVO", "comunidad");
        etiquetado("ana", Instant.parse("2026-09-29T15:00:00Z"), "COMENTARIO", "POSITIVO", "comunidad");
        etiquetado("ana", Instant.parse("2026-09-30T15:00:00Z"), "COMENTARIO", "POSITIVO", "comunidad");

        JsonNode r = pedir("/api/v1/dashboard/frustracion?desde=2026-09-01&hasta=2026-09-30");

        assertThat(r.get("personas")).isEmpty();
    }

    // ── Caso 5: dudas sin responder (DEC-123) ──

    @Test
    void dudasSinResponderSegunLaReglaDeAtendida() throws Exception {
        Instant hace2Dias = Instant.now().minus(Duration.ofDays(2));
        String respondidaPorElBot = duda("ana", hace2Dias, "texto 1");
        jdbc.update("UPDATE mensajes SET respuesta_estado = 'RESPONDIDA' WHERE discord_id = ?", respondidaPorElBot);
        String contestadaPorOtra = duda("beto", hace2Dias.plusSeconds(1), "texto 2");
        respuesta("andres", AutorTipo.persona, AutorRol.mentor, contestadaPorOtra);
        String soloSuAutor = duda("caro", hace2Dias.plusSeconds(2), SCRIPT);
        respuesta("caro", AutorTipo.persona, AutorRol.miembro, soloSuAutor);
        String derivada = duda("dani", hace2Dias.plusSeconds(3), "texto 4");
        jdbc.update("UPDATE mensajes SET respuesta_estado = 'DERIVADA' WHERE discord_id = ?", derivada);
        respuesta("bot", AutorTipo.botPropio, AutorRol.miembro, derivada);  // el aviso del bot no la atiende
        duda("elena", Instant.now().minus(Duration.ofHours(2)), "texto reciente");  // menos de 24 h: todavía no

        JsonNode r = pedir("/api/v1/dashboard/dudas-sin-responder");

        assertThat(r.get("horas").asInt()).isEqualTo(24);
        assertThat(r.get("total").asLong()).isEqualTo(2);
        JsonNode dudas = r.get("dudas");
        assertThat(dudas).hasSize(2);
        assertThat(dudas.get(0).get("discordId").asText()).isEqualTo(soloSuAutor);
        assertThat(dudas.get(0).get("texto").asText()).isEqualTo(SCRIPT);  // tal cual: el panel lo escapa
        assertThat(dudas.get(0).get("derivada").asBoolean()).isFalse();
        assertThat(dudas.get(0).get("autorNombre").asText()).isEqualTo("Caro");
        assertThat(dudas.get(0).get("tema").asText()).isEqualTo("herramientas_entorno");
        assertThat(dudas.get(1).get("discordId").asText()).isEqualTo(derivada);
        assertThat(dudas.get(1).get("derivada").asBoolean()).isTrue();

        // Con 1 hora, la reciente también entra
        assertThat(pedir("/api/v1/dashboard/dudas-sin-responder?horas=1").get("total").asLong()).isEqualTo(3);
    }

    // ── Totales ──

    @Test
    void totalesDelPeriodo() throws Exception {
        etiquetado("ana", Instant.parse("2026-10-01T15:00:00Z"), "PREGUNTA_FAQ", "NEUTRO", "empleo");
        String logro = etiquetado("beto", Instant.parse("2026-10-02T15:00:00Z"), "TESTIMONIO", "MUY_POSITIVO", "empleo");
        mensaje("ana", Instant.parse("2026-10-03T15:00:00Z"));  // sin clasificar
        etiquetado(AutorTipo.botPropio, AutorRol.miembro, "bot", Instant.parse("2026-10-03T16:00:00Z"), "OTRO", null, null);
        etiquetado("caro", Instant.parse("2026-09-01T15:00:00Z"), "COMENTARIO", "NEUTRO", "comunidad");  // fuera
        long mensajeId = jdbc.queryForObject("SELECT id FROM mensajes WHERE discord_id = ?", Long.class, logro);
        jdbc.update("INSERT INTO borradores (mensaje_id, tipo, texto_ia) VALUES (?, 'POST_LINKEDIN', 'x'), (?, 'CASO_EXITO', 'y')",
                mensajeId, mensajeId);

        JsonNode r = pedir("/api/v1/dashboard/totales?desde=2026-10-01&hasta=2026-10-03");

        assertThat(r.get("mensajes").asLong()).isEqualTo(3);  // sin el del bot
        assertThat(r.get("personasActivas").asLong()).isEqualTo(2);
        assertThat(r.get("dudas").asLong()).isEqualTo(1);
        assertThat(r.get("logros").asLong()).isEqualTo(1);
        assertThat(r.get("sinClasificar").asLong()).isEqualTo(1);
        assertThat(r.get("borradoresPendientes").asLong()).isEqualTo(2);
    }

    @Test
    void sinFechasUsaLosUltimos30DiasYSinDatosDevuelveCeros() throws Exception {
        JsonNode r = pedir("/api/v1/dashboard/totales");
        LocalDate hoy = LocalDate.now(BOGOTA);

        assertThat(r.get("periodo").get("hasta").asText()).isEqualTo(hoy.toString());
        assertThat(r.get("periodo").get("desde").asText()).isEqualTo(hoy.minusDays(29).toString());
        assertThat(r.get("mensajes").asLong()).isZero();
        assertThat(pedir("/api/v1/dashboard/sentimiento").get("puntos")).hasSize(30);
        assertThat(pedir("/api/v1/dashboard/temas").get("temas")).isEmpty();
        assertThat(pedir("/api/v1/dashboard/desercion").get("personas")).isEmpty();
        assertThat(pedir("/api/v1/dashboard/frustracion").get("personas")).isEmpty();
        assertThat(pedir("/api/v1/dashboard/dudas-sin-responder").get("total").asLong()).isZero();
    }

    // ── Caso 6: claves ──

    @Test
    void sinClaveEs401() throws Exception {
        assertThat(estado("/api/v1/dashboard/totales", null)).isEqualTo(401);
    }

    @ParameterizedTest
    @ValueSource(strings = {CLAVE_BOT, CLAVE_INGESTA})
    void lasClavesDelBotYDeLaIngestaNoAbrenElDashboard(String clave) throws Exception {
        for (String ruta : List.of("totales", "sentimiento", "temas", "desercion", "frustracion", "dudas-sin-responder")) {
            assertThat(estado("/api/v1/dashboard/" + ruta, clave)).as(ruta).isEqualTo(403);
        }
    }

    @ParameterizedTest
    @ValueSource(strings = {"/api/v1/dashboard;x=1/totales", "/api/v1/dashboar%64/totales", "/api//v1/dashboard/totales",
            "/api/v1/dashboard/dudas-sin-responder;x=1"})
    void laClaveDelBotNoEntraConUnaRutaDisfrazada(String ruta) throws Exception {
        assertThat(estado(ruta, CLAVE_BOT)).as(ruta).isEqualTo(403);
    }

    @Test
    void segundaCapaElControladorRechazaOtroCliente() {
        DashboardController controlador = new DashboardController(dashboard);
        assertThatThrownBy(() -> controlador.totales("bot", null, null)).isInstanceOf(ProhibidoException.class);
        assertThatThrownBy(() -> controlador.dudasSinResponder(null, null, null, null, false))
                .isInstanceOf(ProhibidoException.class);
    }

    // ── Caso 7: parámetros inválidos ──

    @ParameterizedTest
    @ValueSource(strings = {
            "/api/v1/dashboard/totales?desde=2026-10-05&hasta=2026-10-01",   // al revés
            "/api/v1/dashboard/temas?desde=2025-01-01&hasta=2026-10-01",     // más de 366 días
            "/api/v1/dashboard/sentimiento?desde=ayer",                      // no es una fecha
            "/api/v1/dashboard/sentimiento?agrupar=mes",
            "/api/v1/dashboard/sentimiento?excluirOtro=quizas",
            "/api/v1/dashboard/desercion?dias=0",
            "/api/v1/dashboard/desercion?dias=1000",
            "/api/v1/dashboard/dudas-sin-responder?horas=-1",
    })
    void unParametroInvalidoEs422(String ruta) throws Exception {
        assertThat(estado(ruta, CLAVE_PANEL)).as(ruta).isEqualTo(422);
    }

    @Test
    void unPeriodoDe366DiasSiSeAcepta() throws Exception {
        assertThat(estado("/api/v1/dashboard/temas?desde=2025-10-01&hasta=2026-10-01", CLAVE_PANEL)).isEqualTo(200);
    }

    // ── Ayudas ──

    private JsonNode pedir(String ruta) throws Exception {
        MvcResult r = mvc.perform(get(URI.create(ruta)).header("X-Api-Key", CLAVE_PANEL)).andReturn();
        assertThat(r.getResponse().getStatus()).as(ruta).isEqualTo(200);
        return json.readTree(r.getResponse().getContentAsByteArray());
    }

    private int estado(String ruta, String clave) throws Exception {
        var pedido = get(URI.create(ruta));
        if (clave != null) {
            pedido.header("X-Api-Key", clave);
        }
        return mvc.perform(pedido).andReturn().getResponse().getStatus();
    }

    private static Map<String, Long> cantidades(JsonNode punto) {
        Map<String, Long> m = new LinkedHashMap<>();
        punto.get("cantidades").fields().forEachRemaining(e -> m.put(e.getKey(), e.getValue().asLong()));
        return m;
    }

    private static Map<String, long[]> temas(JsonNode r) {
        Map<String, long[]> m = new LinkedHashMap<>();
        for (JsonNode t : r.get("temas")) {
            m.put(t.get("tema").asText(), new long[]{t.get("actual").asLong(), t.get("anterior").asLong(),
                    t.get("variacion").asLong()});
        }
        return m;
    }

    private static List<String> nombres(JsonNode personas) {
        List<String> n = new ArrayList<>();
        personas.forEach(p -> n.add(p.get("nombre").asText()));
        return n;
    }

    private static Instant dias(Instant ahora, int dias) {
        return ahora.minus(Duration.ofDays(dias));
    }

    /** Un mensaje de un alumno, sin clasificar (PENDIENTE). Devuelve su discord_id. */
    private String mensaje(String autor, Instant fecha) {
        return guardar(AutorTipo.persona, AutorRol.miembro, autor, fecha, "hola", null);
    }

    private String etiquetado(String autor, Instant fecha, String intencion, String sentimiento, String tema) {
        return etiquetado(AutorTipo.persona, AutorRol.miembro, autor, fecha, intencion, sentimiento, tema);
    }

    /** Un mensaje ya clasificado OK, con sus etiquetas. */
    private String etiquetado(AutorTipo tipo, AutorRol rol, String autor, Instant fecha, String intencion,
                              String sentimiento, String tema) {
        String id = guardar(tipo, rol, autor, fecha, "texto", null);
        jdbc.update("""
                UPDATE mensajes SET estado_clasificacion = 'OK', intencion = ?, sentimiento = ?, tema = ?, confianza = 0.9
                 WHERE discord_id = ?""", intencion, sentimiento, tema, id);
        return id;
    }

    private String duda(String autor, Instant fecha, String texto) {
        String id = guardar(AutorTipo.persona, AutorRol.miembro, autor, fecha, texto, null);
        jdbc.update("""
                UPDATE mensajes SET estado_clasificacion = 'OK', intencion = 'PREGUNTA_FAQ', sentimiento = 'NEUTRO',
                       tema = 'herramientas_entorno', confianza = 0.9 WHERE discord_id = ?""", id);
        return id;
    }

    private void respuesta(String autor, AutorTipo tipo, AutorRol rol, String respondeA) {
        guardar(tipo, rol, autor, Instant.now().minus(Duration.ofDays(1)), "respuesta", respondeA);
    }

    private String guardar(AutorTipo tipo, AutorRol rol, String autor, Instant fecha, String texto, String respondeA) {
        String id = String.valueOf(ids.incrementAndGet());
        String nombre = Character.toUpperCase(autor.charAt(0)) + autor.substring(1);
        Map<String, Object> caja = new LinkedHashMap<>();
        caja.put("id", id);
        caja.put("textoOriginal", texto);
        caja.put("respondeA", respondeA);
        caja.put("canal", Map.of("id", "1554158212742127821", "nombre", "dudas"));
        caja.put("autor", Map.of("id", "sim-" + autor, "nombreVisible", nombre, "tipo", tipo.name(), "rol", rol.name()));
        upsert.upsert(new DatosMensaje(id, "1554158212742127821", "sim-" + autor, tipo, rol, true, fecha, respondeA,
                texto, caja, "1.0", "1554157903701741700"));
        return id;
    }
}
