package com.insightedulab.backend_java;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightedulab.backend_java.client.NlpDataClient;
import com.insightedulab.backend_java.curaduria.CuraduriaService;
import com.insightedulab.backend_java.curaduria.VistasPanel.EstadoOci;
import com.insightedulab.backend_java.curaduria.VistasPanel.PedidoAprobar;
import com.insightedulab.backend_java.curaduria.VistasPanel.PedidoRechazar;
import com.insightedulab.backend_java.model.enums.AutorRol;
import com.insightedulab.backend_java.model.enums.AutorTipo;
import com.insightedulab.backend_java.oci.OciClient;
import com.insightedulab.backend_java.oci.OciProperties;
import com.insightedulab.backend_java.oci.OciProperties.Par;
import com.insightedulab.backend_java.oci.SubidaOciProgramada;
import com.insightedulab.backend_java.oci.SubidaOciRepository;
import com.insightedulab.backend_java.oci.SubidaOciRepository.Subida;
import com.insightedulab.backend_java.oci.SubidaOciService;
import com.insightedulab.backend_java.oci.SubidaOciService.Resumen;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository.DatosMensaje;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.springframework.context.ApplicationContext;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.client.ClientHttpRequest;
import org.springframework.http.client.ClientHttpResponse;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.mock.http.client.MockClientHttpRequest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.client.ExpectedCount;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.test.web.client.ResponseCreator;
import org.springframework.test.web.client.response.MockRestResponseCreators;
import org.springframework.web.client.RestClient;

import java.io.IOException;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.Callable;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.function.Function;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

/**
 * La subida de los borradores a OCI (T09) contra PostgreSQL real, con el servidor de OCI simulado
 * (MockRestServiceServer). La tarea programada está apagada en todas las pruebas (pom.xml): aquí se arma el
 * servicio a mano con una PAR de mentira y se llama a procesarTanda().
 * ⚠️ Vacían las tablas: solo corren en una base *_test.
 */
// Las mismas propiedades (y el mismo @MockitoBean y @AutoConfigureMockMvc) que CuraduriaApiTest, en el mismo orden:
// así Spring reutiliza su contexto y su grupo de conexiones, en vez de abrir otro (AGENTS.md §5)
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
@ExtendWith(OutputCaptureExtension.class)
class SubidaOciTest {

    private static final String SECRETO = OciClientTest.SECRETO;
    private static final String PAR = OciClientTest.PAR;
    private static final String SERVIDOR = "1554157903701741700";
    private static final String USUARIO = "harrison";
    private static final String LOGRO = "me contrataron!!! empiezo el lunes como QA trainee";
    private static final String POST = "🎉 Camila empieza su primer trabajo en tecnología… #CommunityLab";
    private static final String CASO = "Situación: … Logro: … En sus palabras: \"me contrataron\"";
    private static final String FAQ = "Preguntas frecuentes de la semana…";

    /** Lo que recibió el servidor simulado de OCI. */
    record Peticion(HttpMethod metodo, String uri, String contentType, byte[] cuerpo) {
        String texto() {
            return new String(cuerpo, StandardCharsets.UTF_8);
        }

        /** El nombre del objeto: lo que viene después de la PAR. */
        String objeto() {
            return uri.substring(PAR.length());
        }
    }

    @MockitoBean NlpDataClient ia;  // no se usa; es parte de la llave del contexto compartido
    @Autowired SubidaOciRepository repo;
    @Autowired CuraduriaService curaduria;
    @Autowired MensajeUpsertRepository upsert;
    @Autowired JdbcTemplate jdbc;
    @Autowired ObjectMapper json;
    @Autowired OciProperties propiedadesDelContexto;
    @Autowired ApplicationContext contexto;

    private final List<Peticion> peticiones = new CopyOnWriteArrayList<>();
    private volatile Function<Peticion, ResponseCreator> respuesta = p -> withSuccess();
    private volatile long demoraMs;
    private RestClient restClient;

    @BeforeEach
    void armar() {
        String base = jdbc.queryForObject("SELECT current_database()", String.class);
        assertThat(base).as("Las pruebas solo corren en una base *_test").endsWith("_test");
        jdbc.execute("TRUNCATE faq_semanas, subidas_oci, borradores, mensajes, lotes_recibidos RESTART IDENTITY CASCADE");

        RestClient.Builder builder = RestClient.builder();
        MockRestServiceServer oci = MockRestServiceServer.bindTo(builder).ignoreExpectOrder(true).build();
        oci.expect(ExpectedCount.manyTimes(), solicitud -> { }).andRespond(this::atender);
        restClient = builder.build();
    }

    private ClientHttpResponse atender(ClientHttpRequest solicitud) throws IOException {
        MockClientHttpRequest m = (MockClientHttpRequest) solicitud;
        Peticion p = new Peticion(m.getMethod(), m.getURI().toString(), m.getHeaders().getFirst("Content-Type"),
                m.getBodyAsBytes());
        peticiones.add(p);
        if (demoraMs > 0) {
            try {
                Thread.sleep(demoraMs);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
        return respuesta.apply(p).createResponse(solicitud);
    }

    // ── La tarea no corre sola en las pruebas ──

    @Test
    void laTareaProgramadaEstaApagadaEnLasPruebas() {
        // Si no, con una PAR real en el .env las pruebas subirían datos falsos al bucket de verdad.
        // La apaga el pom.xml (surefire): esta prueba corre con `mvn test`, como pide docs/OPERACION.md §5
        assertThat(propiedadesDelContexto.habilitada()).isFalse();
        assertThat(contexto.getBeanNamesForType(SubidaOciProgramada.class)).isEmpty();
    }

    // ── Caso 1: un borrador nuevo se sube a generados/ ──

    @Test
    void unBorradorNuevoSeSubeAGeneradosConPutJsonValidoYElNombreEsperado() throws Exception {
        long id = borrador("101", "POST_LINKEDIN", POST);
        // 03:00 UTC del 5 de octubre son las 22:00 del 4 en Bogotá: la fecha del nombre usa la zona configurada
        jdbc.update("UPDATE borradores SET creado_en = '2026-10-05T03:00:00Z' WHERE id = ?", id);

        Resumen r = servicio(PAR, 10, 5, 60).procesarTanda();

        assertThat(r.tomadas()).isEqualTo(1);
        assertThat(r.subidas()).isEqualTo(1);
        assertThat(peticiones).hasSize(1);
        Peticion p = peticiones.get(0);
        assertThat(p.metodo()).isEqualTo(HttpMethod.PUT);
        assertThat(p.contentType()).startsWith("application/json");
        assertThat(p.uri()).isEqualTo(PAR + "generados/POST_LINKEDIN/2026-10-04/borrador-" + id + ".json");
        JsonNode archivo = json.readTree(p.cuerpo());  // JSON válido
        assertThat(archivo.get("version").asText()).isEqualTo("1.0");
        assertThat(archivo.get("id").asLong()).isEqualTo(id);
        assertThat(archivo.get("tipo").asText()).isEqualTo("POST_LINKEDIN");
        assertThat(archivo.get("estado").asText()).isEqualTo("PENDIENTE");
        assertThat(archivo.get("textoIa").asText()).isEqualTo(POST);
        assertThat(archivo.get("textoFinal").isNull()).isTrue();
        assertThat(archivo.get("consentimientoConfirmado").asBoolean()).isFalse();
        assertThat(archivo.get("creadoEn").asText()).isEqualTo("2026-10-05T03:00:00Z");
        assertThat(archivo.get("motivoIa").asText()).isEqualTo("Es una contratación.");
        assertThat(archivo.get("semana").isNull()).isTrue();

        assertThat(subidas()).hasSize(1);
        assertThat(subidas().get(0)).containsEntry("carpeta", "generados").containsEntry("estado", "SUBIDO")
                .containsEntry("ruta", "generados/POST_LINKEDIN/2026-10-04/borrador-" + id + ".json")
                .containsEntry("intentos", 1).containsEntry("reservada_hasta", null).containsEntry("ultimo_error", null);
        assertThat(subidas().get(0).get("subido_en")).isNotNull();
    }

    @Test
    void correrLaTareaOtraVezNoSubeDosVecesLoMismo() {
        borrador("101", "POST_LINKEDIN", POST);
        SubidaOciService servicio = servicio(PAR, 10, 5, 60);

        servicio.procesarTanda();
        assertThat(servicio.procesarTanda().tomadas()).isZero();
        assertThat(servicio.procesarTanda().tomadas()).isZero();

        assertThat(peticiones).hasSize(1);
        assertThat(subidas()).hasSize(1);
    }

    // ── Caso 2: un borrador aprobado se sube también a aprobados/, con texto_final ──

    @Test
    void unBorradorAprobadoSeSubeTambienAAprobadosConElTextoFinal() throws Exception {
        long id = borrador("101", "POST_LINKEDIN", POST);
        SubidaOciService servicio = servicio(PAR, 10, 5, 60);
        servicio.procesarTanda();  // generados/
        assertThat(peticiones).hasSize(1);

        curaduria.aprobar(id, USUARIO, new PedidoAprobar(true, 42, "Texto editado por Marketing 🎉"));
        Resumen r = servicio.procesarTanda();

        assertThat(r.subidas()).isEqualTo(1);
        assertThat(peticiones).hasSize(2);
        Peticion p = peticiones.get(1);
        String dia = jdbc.queryForObject("SELECT (aprobado_en AT TIME ZONE 'America/Bogota')::date::text FROM borradores WHERE id = ?",
                String.class, id);
        assertThat(p.uri()).isEqualTo(PAR + "aprobados/POST_LINKEDIN/" + dia + "/borrador-" + id + ".json");
        JsonNode archivo = json.readTree(p.cuerpo());
        assertThat(archivo.get("estado").asText()).isEqualTo("APROBADO");
        assertThat(archivo.get("textoIa").asText()).isEqualTo(POST);
        assertThat(archivo.get("textoFinal").asText()).isEqualTo("Texto editado por Marketing 🎉");
        assertThat(archivo.get("consentimientoConfirmado").asBoolean()).isTrue();
        assertThat(archivo.get("aprobadoPor").asText()).isEqualTo(USUARIO);
        assertThat(archivo.get("aprobadoEn").asText()).isNotBlank();
        assertThat(archivo.get("tiempoCuraduriaSeg").asInt()).isEqualTo(42);
        assertThat(subidas()).extracting(s -> s.get("carpeta")).containsExactly("generados", "aprobados");
        assertThat(subidas()).extracting(s -> s.get("estado")).containsOnly("SUBIDO");
    }

    @Test
    void siSeApruebaAntesDeLaPrimeraSubidaSubenLasDosCarpetasConElEstadoDeAhora() throws Exception {
        long id = borrador("101", "POST_LINKEDIN", POST);
        curaduria.aprobar(id, USUARIO, new PedidoAprobar(true, 5, null));  // OCI estuvo caído: se aprobó antes

        Resumen r = servicio(PAR, 10, 5, 60).procesarTanda();

        assertThat(r.subidas()).isEqualTo(2);
        assertThat(peticiones).extracting(Peticion::objeto)
                .anyMatch(o -> o.startsWith("generados/POST_LINKEDIN/")).anyMatch(o -> o.startsWith("aprobados/POST_LINKEDIN/"));
        // Sin edición, el texto final es el de la IA (así lo guarda la aprobación)
        for (Peticion p : peticiones) {
            assertThat(json.readTree(p.cuerpo()).get("textoFinal").asText()).isEqualTo(POST);
        }
    }

    // ── Caso 3: lo rechazado o pendiente no va a aprobados/ (F11) ──

    @Test
    void unRechazadoOUnPendienteNoVanAAprobados() {
        long pendiente = borrador("101", "POST_LINKEDIN", POST);
        long rechazado = borrador("102", "POST_LINKEDIN", POST);
        long aprobado = borrador("103", "POST_LINKEDIN", POST);
        curaduria.rechazar(rechazado, USUARIO, new PedidoRechazar("No aplica", 3));
        curaduria.aprobar(aprobado, USUARIO, new PedidoAprobar(true, 9, null));

        Resumen r = servicio(PAR, 10, 5, 60).procesarTanda();

        // Los tres estuvieron en generados/; solo el aprobado está en aprobados/
        assertThat(r.subidas()).isEqualTo(4);
        assertThat(peticiones).extracting(Peticion::objeto).filteredOn(o -> o.startsWith("generados/")).hasSize(3);
        assertThat(peticiones).extracting(Peticion::objeto).filteredOn(o -> o.startsWith("aprobados/"))
                .hasSize(1).allMatch(o -> o.endsWith("borrador-" + aprobado + ".json"));
        assertThat(subidasDe(pendiente)).containsExactly("generados");
        assertThat(subidasDe(rechazado)).containsExactly("generados");
        assertThat(subidasDe(aprobado)).containsExactly("generados", "aprobados");
    }

    @Test
    void unPendienteEnAprobadosPorUnErrorNoSeSubeYQuedaEnError() {
        long id = borrador("101", "POST_LINKEDIN", POST);
        // Una fila que nunca debería existir (por ejemplo, creada a mano): la guarda de F11 tiene que frenarla
        jdbc.update("INSERT INTO subidas_oci (borrador_id, carpeta) VALUES (?, 'aprobados')", id);

        Resumen r = servicio(PAR, 10, 5, 60).procesarTanda();

        assertThat(peticiones).extracting(Peticion::objeto).noneMatch(o -> o.startsWith("aprobados/"));
        assertThat(r.error()).isEqualTo(1);
        Map<String, Object> fila = jdbc.queryForMap("SELECT * FROM subidas_oci WHERE carpeta = 'aprobados'");
        assertThat(fila).containsEntry("estado", "ERROR").containsEntry("intentos", 0);
        assertThat((String) fila.get("ultimo_error")).contains("APROBADO");
    }

    @Test
    void lasRespuestasDelBotNoSeSuben() {
        long mensaje = mensaje(logro("101"));
        jdbc.update("INSERT INTO borradores (mensaje_id, tipo, texto_ia) VALUES (?, 'RESPUESTA_BOT', 'respuesta del bot')", mensaje);

        assertThat(servicio(PAR, 10, 5, 60).procesarTanda().tomadas()).isZero();
        assertThat(peticiones).isEmpty();
    }

    // ── Los borradores que ya existían se suben la primera vez (DEC-131) ──

    @Test
    void losBorradoresQueYaExistenSeSubenLaPrimeraVezQueCorreLaTarea() {
        for (int i = 101; i <= 105; i++) {
            borrador(String.valueOf(i), "POST_LINKEDIN", POST);
        }
        long aprobado = borrador("106", "CASO_EXITO", CASO);
        curaduria.aprobar(aprobado, USUARIO, new PedidoAprobar(true, 1, null));
        long faq = faq("2026-W40");
        curaduria.aprobar(faq, USUARIO, new PedidoAprobar(false, 1, null));
        SubidaOciService servicio = servicio(PAR, 4, 5, 60);

        int tandas = 0;
        while (servicio.procesarTanda().tomadas() > 0) {
            tandas++;
        }

        assertThat(tandas).as("7 en generados/ y 2 en aprobados/, de 4 en 4").isEqualTo(3);
        assertThat(peticiones).hasSize(7 + 2);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM subidas_oci WHERE estado = 'SUBIDO'", Integer.class)).isEqualTo(9);
    }

    // ── Caso 4: un texto raro sigue dando un JSON válido (F10) ──

    @Test
    void unTextoConComillasSaltosDeLineaEmojisYBarrasDaUnJsonValido() throws Exception {
        String raro = "Dijo: \"me contrataron\"\nSegunda línea\tcon tab y barra \\ y \\n literal\r\n"
                + "emojis 🎉👩‍💻🚀, comilla ' y </script>, llaves {\"a\": [1, 2]} y un separador   de línea";
        long id = borrador("101", "POST_LINKEDIN", raro);
        jdbc.update("UPDATE borradores SET texto_final = ? WHERE id = ?", raro + " (editado)", id);

        servicio(PAR, 10, 5, 60).procesarTanda();

        Peticion p = peticiones.get(0);
        JsonNode archivo = json.readTree(p.cuerpo());
        assertThat(archivo.get("textoIa").asText()).isEqualTo(raro);
        assertThat(archivo.get("textoFinal").asText()).isEqualTo(raro + " (editado)");
        // Los emojis viajan como UTF-8, no como 🎉: el archivo se lee bien en la consola de Oracle
        assertThat(p.texto()).contains("🎉👩‍💻🚀");
        assertThat(archivo.get("motivoIa").asText()).isEqualTo("Es una contratación.");
    }

    // ── Caso 5: OCI falla ──

    @Test
    void siOciRespondeError500SumaUnIntentoYSigueHastaElMaximo() {
        long id = borrador("101", "POST_LINKEDIN", POST);
        respuesta = p -> MockRestResponseCreators.withServerError();
        SubidaOciService servicio = servicio(PAR, 10, 3, 60);

        Resumen primera = servicio.procesarTanda();

        assertThat(primera.reintento()).isEqualTo(1);
        assertThat(subidas().get(0)).containsEntry("estado", "PENDIENTE").containsEntry("intentos", 1)
                .containsEntry("ultimo_error", "OCI respondió HTTP 500").containsEntry("ruta", null);
        assertThat(subidas().get(0).get("reservada_hasta")).as("espera antes de reintentar").isNotNull();
        assertThat(servicio.procesarTanda().tomadas()).as("todavía está esperando").isZero();

        saltarLaEspera();
        assertThat(servicio.procesarTanda().reintento()).isEqualTo(1);
        assertThat(subidas().get(0)).containsEntry("estado", "PENDIENTE").containsEntry("intentos", 2);

        saltarLaEspera();
        Resumen ultima = servicio.procesarTanda();
        assertThat(ultima.error()).isEqualTo(1);
        assertThat(subidas().get(0)).containsEntry("estado", "ERROR").containsEntry("intentos", 3)
                .containsEntry("reservada_hasta", null);
        saltarLaEspera();
        assertThat(servicio.procesarTanda().tomadas()).as("ERROR no se reintenta solo").isZero();
        assertThat(peticiones).hasSize(3);
        assertThat(estadoBorrador(id)).as("el borrador no se toca").isEqualTo("PENDIENTE");
    }

    @Test
    void siOciNoRespondeTambienSumaUnIntento() {
        borrador("101", "POST_LINKEDIN", POST);
        respuesta = p -> MockRestResponseCreators.withException(new SocketTimeoutException("Read timed out"));

        Resumen r = servicio(PAR, 10, 5, 60).procesarTanda();

        assertThat(r.reintento()).isEqualTo(1);
        assertThat(subidas().get(0)).containsEntry("estado", "PENDIENTE").containsEntry("intentos", 1)
                .containsEntry("ultimo_error", "No se pudo hablar con OCI: SocketTimeoutException");
    }

    @Test
    void cadaSubidaEsIndependienteYLaDeVueltaDeUnERROREsSubirla() {
        long mala = borrador("101", "POST_LINKEDIN", POST);
        long buena = borrador("102", "POST_LINKEDIN", POST);
        respuesta = p -> p.objeto().endsWith("borrador-" + mala + ".json")
                ? MockRestResponseCreators.withStatus(HttpStatus.FORBIDDEN) : withSuccess();
        SubidaOciService servicio = servicio(PAR, 10, 1, 60);  // un solo intento: el primer fallo ya es ERROR

        Resumen r = servicio.procesarTanda();

        assertThat(r.subidas()).isEqualTo(1);
        assertThat(r.error()).isEqualTo(1);
        assertThat(estadoSubida(buena, "generados")).isEqualTo("SUBIDO");
        assertThat(estadoSubida(mala, "generados")).isEqualTo("ERROR");

        // docs/OPERACION.md §12: así se reintentan los ERROR cuando OCI vuelve
        respuesta = p -> withSuccess();
        int vueltos = jdbc.update("UPDATE subidas_oci SET estado = 'PENDIENTE', intentos = 0, ultimo_error = NULL, "
                + "reservada_hasta = NULL WHERE estado = 'ERROR'");
        assertThat(vueltos).isEqualTo(1);
        assertThat(servicio.procesarTanda().subidas()).isEqualTo(1);
        assertThat(estadoSubida(mala, "generados")).isEqualTo("SUBIDO");
    }

    @Test
    void siOciEstaCaidoGenerarYAprobarSiguenFuncionando() {
        long id = borrador("101", "POST_LINKEDIN", POST);
        respuesta = p -> MockRestResponseCreators.withServerError();
        SubidaOciService servicio = servicio(PAR, 10, 5, 60);
        servicio.procesarTanda();  // OCI falló
        int peticionesAntes = peticiones.size();

        // La aprobación no pasa por OCI: no la llama, no espera y no falla
        curaduria.aprobar(id, USUARIO, new PedidoAprobar(true, 12, "Editado"));

        assertThat(estadoBorrador(id)).isEqualTo("APROBADO");
        assertThat(peticiones).hasSize(peticionesAntes);
        // Y cuando OCI vuelve, se sube todo lo que faltaba
        respuesta = p -> withSuccess();
        saltarLaEspera();
        servicio.procesarTanda();
        assertThat(subidas()).extracting(s -> s.get("carpeta")).containsExactly("generados", "aprobados");
        assertThat(subidas()).extracting(s -> s.get("estado")).containsOnly("SUBIDO");
    }

    // ── Caso 6: dos ejecuciones a la vez ──

    @Test
    void dosReservasAlMismoTiempoNoTomanLasMismasSubidas() throws Exception {
        for (int i = 101; i <= 106; i++) {
            borrador(String.valueOf(i), "POST_LINKEDIN", POST);
        }
        repo.encolar();
        ExecutorService hilos = Executors.newFixedThreadPool(2);
        CountDownLatch largada = new CountDownLatch(1);
        try {
            Callable<List<Subida>> reservar = () -> {
                largada.await();
                return repo.reservar(3, 180);
            };
            Future<List<Subida>> a = hilos.submit(reservar);
            Future<List<Subida>> b = hilos.submit(reservar);
            largada.countDown();
            Set<Long> idsA = ids(a.get());
            Set<Long> idsB = ids(b.get());
            assertThat(idsA).doesNotContainAnyElementsOf(idsB);
            Set<Long> todos = new HashSet<>(idsA);
            todos.addAll(idsB);
            assertThat(todos).hasSize(6);
        } finally {
            hilos.shutdown();
        }
    }

    @Test
    void dosEjecucionesCompletasALaVezNoSubenDosVecesLoMismo() throws Exception {
        for (int i = 101; i <= 108; i++) {
            borrador(String.valueOf(i), "POST_LINKEDIN", POST);
        }
        demoraMs = 150;  // para que las dos ejecuciones de verdad se superpongan
        SubidaOciService servicio = servicio(PAR, 4, 5, 60);
        ExecutorService hilos = Executors.newFixedThreadPool(2);
        CountDownLatch largada = new CountDownLatch(1);
        try {
            Callable<Resumen> tanda = () -> {
                largada.await();
                return servicio.procesarTanda();
            };
            Future<Resumen> a = hilos.submit(tanda);
            Future<Resumen> b = hilos.submit(tanda);
            largada.countDown();
            assertThat(a.get().subidas() + b.get().subidas()).isEqualTo(8);
        } finally {
            hilos.shutdown();
        }

        List<String> objetos = peticiones.stream().map(Peticion::objeto).toList();
        assertThat(objetos).hasSize(8).doesNotHaveDuplicates();
        assertThat(jdbc.queryForObject("SELECT count(*) FROM subidas_oci WHERE estado = 'SUBIDO' AND intentos = 1",
                Integer.class)).isEqualTo(8);
    }

    @Test
    void unaSubidaReservadaPorOtraEjecucionNoSeTomaHastaQueVence() {
        borrador("101", "POST_LINKEDIN", POST);
        repo.encolar();
        assertThat(repo.reservar(3, 180)).hasSize(1);  // otra ejecución la tiene
        SubidaOciService servicio = servicio(PAR, 10, 5, 60);

        assertThat(servicio.procesarTanda().tomadas()).isZero();
        assertThat(peticiones).isEmpty();

        jdbc.update("UPDATE subidas_oci SET reservada_hasta = now() - interval '1 minute'");  // murió
        assertThat(servicio.procesarTanda().subidas()).isEqualTo(1);
    }

    @Test
    void laGuardaNoPisaUnaSubidaQueOtraEjecucionYaAnoto() {
        borrador("101", "POST_LINKEDIN", POST);
        repo.encolar();
        Subida s = repo.reservar(1, 180).get(0);

        assertThat(repo.subido(s.id(), "generados/POST_LINKEDIN/2026-10-04/borrador-1.json")).isTrue();

        // La ejecución lenta llega después con un fallo o con otro "subido": no cambia nada
        assertThat(repo.fallo(s.id(), "OCI respondió HTTP 500", 5, 60)).isNull();
        assertThat(repo.subido(s.id(), "otra-ruta.json")).isFalse();
        assertThat(subidas().get(0)).containsEntry("estado", "SUBIDO").containsEntry("intentos", 1)
                .containsEntry("ultimo_error", null).containsEntry("ruta", "generados/POST_LINKEDIN/2026-10-04/borrador-1.json");
    }

    // ── Caso 7: sin PAR ──

    @Test
    void sinParNoLlamaANadaAvisaUnaSolaVezYNoMarcaErrores(CapturedOutput salida) {
        borrador("101", "POST_LINKEDIN", POST);
        SubidaOciService servicio = servicio("", 10, 5, 60);

        for (int i = 0; i < 3; i++) {
            Resumen r = servicio.procesarTanda();
            assertThat(r.tomadas()).isZero();
        }
        assertThat(servicio.listo()).isFalse();

        assertThat(peticiones).isEmpty();
        assertThat(subidas()).as("no se encoló ni se marcó nada").isEmpty();
        assertThat(ocurrencias(salida, "no hay URL PAR")).isEqualTo(1);

        // Cuando después se configura la PAR, se sube lo que estaba esperando
        assertThat(servicio(PAR, 10, 5, 60).procesarTanda().subidas()).isEqualTo(1);
    }

    @ParameterizedTest
    @ValueSource(strings = {
            "http://objectstorage.us-test-1.oraclecloud.com/p/" + SECRETO + "/n/e/b/b/o/",
            "https://example.com/p/" + SECRETO + "/n/e/b/b/o/",
            "https://objectstorage.us-test-1.oraclecloud.com/p/" + SECRETO + "/n/e/b/b/o",
            "https://objectstorage.us-test-1.oraclecloud.com/p/" + SECRETO + "/n/e/b/b/o/obj.json",
    })
    void unaParConOtraFormaTampocoSubeNadaYNoSeMuestraEnElRegistro(String par, CapturedOutput salida) {
        borrador("101", "POST_LINKEDIN", POST);
        SubidaOciService servicio = servicio(par, 10, 5, 60);

        servicio.procesarTanda();
        servicio.procesarTanda();

        assertThat(peticiones).isEmpty();
        assertThat(subidas()).isEmpty();
        assertThat(ocurrencias(salida, "no parece una PAR de bucket")).isEqualTo(1);
        assertThat(salida.getAll()).doesNotContain(SECRETO).doesNotContain(par);
    }

    // ── Caso 8: el archivo no tiene datos de Discord del alumno (DEC-128) ──

    @Test
    void elJsonNoTieneNombreDeUsuarioIdsDeDiscordNiElMensajeOriginal() throws Exception {
        long id = borrador("1554243551888416798", "POST_LINKEDIN", POST);
        long caso = borrador("1554243551888416798", "CASO_EXITO", CASO);
        curaduria.aprobar(id, USUARIO, new PedidoAprobar(true, 5, null));
        curaduria.aprobar(caso, USUARIO, new PedidoAprobar(true, 5, "Texto final sin datos de Discord"));

        servicio(PAR, 10, 5, 60).procesarTanda();

        assertThat(peticiones).hasSize(4);
        Set<String> campos = Set.of("version", "id", "tipo", "estado", "textoIa", "textoFinal",
                "consentimientoConfirmado", "creadoEn", "aprobadoPor", "aprobadoEn", "tiempoCuraduriaSeg",
                "motivoIa", "semana");
        for (Peticion p : peticiones) {
            String texto = p.texto();
            // Los únicos campos son los de DEC-128: ni siquiera existe un lugar donde caiga un dato de Discord
            Set<String> encontrados = new TreeSet<>();
            json.readTree(p.cuerpo()).fieldNames().forEachRemaining(encontrados::add);
            assertThat(encontrados).containsExactlyInAnyOrderElementsOf(campos);
            assertThat(texto).doesNotContain("camila_rojas_dc")        // nombreUsuario
                    .doesNotContain("1554243551888416798")              // id del mensaje de Discord
                    .doesNotContain("888777666555444333")                // id del autor
                    .doesNotContain("1554158272867467374")               // id del canal
                    .doesNotContain(SERVIDOR)                            // id del servidor
                    .doesNotContain(LOGRO)                               // el mensaje original
                    .doesNotContain("Camila Rojas");                     // el nombre completo
        }
    }

    @Test
    void laFaqLlevaLaSemanaYElResumenYNoNecesitaConsentimiento() throws Exception {
        long id = faq("2026-W40");
        curaduria.aprobar(id, USUARIO, new PedidoAprobar(null, 20, null));

        servicio(PAR, 10, 5, 60).procesarTanda();

        assertThat(peticiones).extracting(Peticion::objeto).allMatch(o -> o.contains("/FAQ/"));
        assertThat(peticiones).hasSize(2);
        JsonNode archivo = json.readTree(peticiones.get(0).cuerpo());
        assertThat(archivo.get("tipo").asText()).isEqualTo("FAQ");
        assertThat(archivo.get("semana").asText()).isEqualTo("2026-W40");
        assertThat(archivo.get("motivoIa").asText()).isEqualTo("3 preguntas repetidas, 2 con respuesta.");
        assertThat(archivo.get("textoIa").asText()).isEqualTo(FAQ);
    }

    // ── Caso 9: el registro no tiene la URL PAR ──

    @Test
    void elRegistroNiLaBaseTienenLaUrlParEnNingunCaso(CapturedOutput salida) {
        borrador("101", "POST_LINKEDIN", POST);
        borrador("102", "POST_LINKEDIN", POST);
        borrador("103", "POST_LINKEDIN", POST);
        SubidaOciService servicio = servicio(PAR, 10, 2, 60);

        // Un éxito, un 500 y un tiempo agotado (cuyo mensaje de Spring lleva la URL completa), hasta llegar a ERROR
        respuesta = p -> switch (p.objeto().substring(p.objeto().lastIndexOf('-') + 1)) {
            case "1.json" -> withSuccess();
            case "2.json" -> MockRestResponseCreators.withServerError();
            default -> MockRestResponseCreators.withException(new SocketTimeoutException("Read timed out"));
        };
        servicio.procesarTanda();
        saltarLaEspera();
        servicio.procesarTanda();

        String registro = salida.getAll();
        assertThat(registro).contains("OCI: no se pudo subir generados/POST_LINKEDIN/").contains("OCI respondió HTTP 500")
                .contains("se agotaron los intentos");
        assertThat(registro).doesNotContain(PAR).doesNotContain(SECRETO).doesNotContain("/n/espacio-de-prueba")
                .doesNotContain("bucket-de-prueba").doesNotContain("objectstorage");
        for (Map<String, Object> fila : subidas()) {
            assertThat(String.valueOf(fila)).doesNotContain(SECRETO).doesNotContain("objectstorage");
        }
        assertThat(jdbc.queryForObject("SELECT count(*) FROM subidas_oci WHERE estado = 'ERROR'", Integer.class)).isEqualTo(2);
    }

    // ── El panel (parte opcional de la ficha) ──

    @Test
    void elDetalleDelPanelDiceElEstadoDeLasSubidasSinLaRutaNiLaPar() throws Exception {
        long id = borrador("101", "POST_LINKEDIN", POST);
        assertThat(curaduria.detalle(id).oci()).as("todavía no se encoló").isEqualTo(new EstadoOci(null, null));

        respuesta = p -> MockRestResponseCreators.withServerError();
        SubidaOciService servicio = servicio(PAR, 10, 5, 60);
        servicio.procesarTanda();
        assertThat(curaduria.detalle(id).oci()).isEqualTo(new EstadoOci("PENDIENTE", null));

        respuesta = p -> withSuccess();
        saltarLaEspera();
        servicio.procesarTanda();
        assertThat(curaduria.detalle(id).oci()).isEqualTo(new EstadoOci("SUBIDO", null));

        curaduria.aprobar(id, USUARIO, new PedidoAprobar(true, 5, null));
        servicio.procesarTanda();
        EstadoOci aprobado = curaduria.detalle(id).oci();
        assertThat(aprobado).isEqualTo(new EstadoOci("SUBIDO", "SUBIDO"));

        // Lo que sale por la puerta del panel: solo los dos estados
        String respuestaDelPanel = json.writeValueAsString(aprobado);
        assertThat(respuestaDelPanel).isEqualTo("{\"generados\":\"SUBIDO\",\"aprobados\":\"SUBIDO\"}");
        assertThat(json.writeValueAsString(curaduria.detalle(id))).doesNotContain("borrador-").doesNotContain(SECRETO)
                .doesNotContain("objectstorage");
    }

    // ── La migración V8 ──

    @Test
    void laV8NoDejaRepetirNiAnotarMal() {
        long id = borrador("101", "POST_LINKEDIN", POST);
        jdbc.update("INSERT INTO subidas_oci (borrador_id, carpeta) VALUES (?, 'generados')", id);

        assertThatThrownBy(() -> jdbc.update("INSERT INTO subidas_oci (borrador_id, carpeta) VALUES (?, 'generados')", id))
                .isInstanceOf(DataIntegrityViolationException.class);
        assertThatThrownBy(() -> jdbc.update("INSERT INTO subidas_oci (borrador_id, carpeta) VALUES (?, 'otra')", id))
                .isInstanceOf(DataIntegrityViolationException.class);
        assertThatThrownBy(() -> jdbc.update("UPDATE subidas_oci SET estado = 'LISTO'"))
                .isInstanceOf(DataIntegrityViolationException.class);
        // SUBIDO exige su ruta y su fecha (y al revés)
        assertThatThrownBy(() -> jdbc.update("UPDATE subidas_oci SET estado = 'SUBIDO'"))
                .isInstanceOf(DataIntegrityViolationException.class);
        assertThatThrownBy(() -> jdbc.update("UPDATE subidas_oci SET ruta = 'x.json'"))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    // ── Ayudas ──

    private SubidaOciService servicio(String par, int tanda, int maxIntentos, int espera) {
        OciProperties p = new OciProperties(true, 1000L, tanda, maxIntentos, 420, espera, "America/Bogota", new Par(par));
        return new SubidaOciService(repo, new OciClient(restClient, p), json, p);
    }

    /** Pasa el tiempo de espera entre intentos, sin esperar de verdad. */
    private void saltarLaEspera() {
        jdbc.update("UPDATE subidas_oci SET reservada_hasta = NULL WHERE estado = 'PENDIENTE'");
    }

    /** Un logro clasificado y con sus borradores generados, como lo deja la generación de T06. */
    private long borrador(String discordId, String tipo, String texto) {
        long mensajeId = jdbc.query("SELECT id FROM mensajes WHERE discord_id = ?", rs -> rs.next() ? rs.getLong(1) : 0L, discordId);
        if (mensajeId == 0L) {
            mensajeId = mensaje(logro(discordId));
            jdbc.update("UPDATE mensajes SET generacion_estado = 'GENERADO', generacion_motivo = 'Es una contratación.' WHERE id = ?",
                    mensajeId);
        }
        return jdbc.queryForObject("INSERT INTO borradores (mensaje_id, tipo, texto_ia) VALUES (?, ?, ?) RETURNING id",
                Long.class, mensajeId, tipo, texto);
    }

    private String logro(String discordId) {
        upsert.upsert(datos(discordId));
        jdbc.update("UPDATE mensajes SET intencion = 'TESTIMONIO', estado_clasificacion = 'OK', confianza = 0.9 WHERE discord_id = ?",
                discordId);
        return discordId;
    }

    private long mensaje(String discordId) {
        return jdbc.queryForObject("SELECT id FROM mensajes WHERE discord_id = ?", Long.class, discordId);
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

    private String estadoBorrador(long id) {
        return jdbc.queryForObject("SELECT estado FROM borradores WHERE id = ?", String.class, id);
    }

    private List<Map<String, Object>> subidas() {
        return jdbc.queryForList("SELECT * FROM subidas_oci ORDER BY id");
    }

    private List<String> subidasDe(long borradorId) {
        return jdbc.queryForList("SELECT carpeta FROM subidas_oci WHERE borrador_id = ? ORDER BY id", String.class, borradorId);
    }

    private String estadoSubida(long borradorId, String carpeta) {
        return jdbc.queryForObject("SELECT estado FROM subidas_oci WHERE borrador_id = ? AND carpeta = ?", String.class,
                borradorId, carpeta);
    }

    private static Set<Long> ids(List<Subida> subidas) {
        Set<Long> ids = new HashSet<>();
        subidas.forEach(s -> ids.add(s.id()));
        return ids;
    }

    private static int ocurrencias(CapturedOutput salida, String texto) {
        String todo = salida.getAll();
        int n = 0;
        for (int i = todo.indexOf(texto); i >= 0; i = todo.indexOf(texto, i + texto.length())) {
            n++;
        }
        return n;
    }

    /** El mensaje de Discord del logro, con los datos personales que NO tienen que llegar al bucket. */
    private static DatosMensaje datos(String id) {
        Instant fecha = Instant.parse("2026-09-28T18:56:30.331Z").plusSeconds(Math.floorMod(id.hashCode(), 100_000));
        Map<String, Object> caja = new LinkedHashMap<>();
        caja.put("id", id);
        caja.put("textoOriginal", LOGRO);
        caja.put("canal", Map.of("id", "1554158272867467374", "nombre", "logros"));
        Map<String, Object> autor = new LinkedHashMap<>();
        autor.put("id", "888777666555444333");
        autor.put("nombreVisible", "Camila Rojas");
        autor.put("nombreUsuario", "camila_rojas_dc");
        autor.put("tipo", "persona");
        autor.put("rol", "miembro");
        caja.put("autor", autor);
        return new DatosMensaje(id, "1554158272867467374", "888777666555444333", AutorTipo.persona, AutorRol.miembro,
                false, fecha, null, LOGRO, caja, "1.0", SERVIDOR);
    }
}
