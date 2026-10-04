package com.insightedulab.backend_java;

import com.insightedulab.backend_java.clasificacion.ClasificacionRepository;
import com.insightedulab.backend_java.clasificacion.ClasificacionRepository.Pendiente;
import com.insightedulab.backend_java.clasificacion.ClasificacionService;
import com.insightedulab.backend_java.clasificacion.ClasificacionService.Resumen;
import com.insightedulab.backend_java.client.IaNoDisponibleException;
import com.insightedulab.backend_java.client.IaRechazoException;
import com.insightedulab.backend_java.client.NlpDataClient;
import com.insightedulab.backend_java.client.RespuestaIa;
import com.insightedulab.backend_java.error.ErrorApi.ErrorCampo;
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
import java.util.ArrayList;
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
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

/**
 * Clasificación en segundo plano (T04) contra PostgreSQL real, con la IA simulada (Mockito).
 * ⚠️ Vacían las tablas: solo corren en una base *_test.
 */
@SpringBootTest(properties = {
        "clasificacion.habilitada=false",  // la tarea programada no corre: las pruebas llaman a procesarTanda()
        "clasificacion.tanda=5",
        "clasificacion.max-intentos=3",
})
class ClasificacionTest {

    private static final String SERVIDOR = "1554157903701741700";

    @MockitoBean NlpDataClient ia;
    @Autowired ClasificacionService servicio;
    @Autowired ClasificacionRepository repo;
    @Autowired MensajeUpsertRepository upsert;
    @Autowired JdbcTemplate jdbc;

    @BeforeEach
    void vaciarTablas() {
        String base = jdbc.queryForObject("SELECT current_database()", String.class);
        assertThat(base).as("Las pruebas solo corren en una base *_test").endsWith("_test");
        jdbc.execute("TRUNCATE borradores, mensajes, lotes_recibidos RESTART IDENTITY CASCADE");
    }

    // ── Caso 1: la IA responde OK ──

    @Test
    void tresPendientesQuedanOkConSusEtiquetas() {
        pendientes("101", "102", "103");
        iaResponde(id -> ok(id));

        Resumen r = servicio.procesarTanda();

        assertThat(r.tomados()).isEqualTo(3);
        assertThat(r.ok()).isEqualTo(3);
        for (String id : List.of("101", "102", "103")) {
            Map<String, Object> fila = fila(id);
            assertThat(fila.get("estado_clasificacion")).isEqualTo("OK");
            assertThat(fila.get("intencion")).isEqualTo("TESTIMONIO");
            assertThat(fila.get("confianza")).isEqualTo(0.9);
            assertThat(fila.get("sentimiento")).isEqualTo("POSITIVO");
            assertThat(fila.get("tema")).isEqualTo("empleo");
            assertThat(fila.get("metodo_clasificacion")).isEqualTo("llm");
            assertThat(fila.get("intentos_clasificacion")).isEqualTo(1);
            assertThat(fila.get("clasificado_en")).isNotNull();
            assertThat(fila.get("reservado_hasta")).isNull();
        }
    }

    @Test
    void elLoteQueRecibeLaIaEsElContratoV1ConLasCajas() {
        pendientes("101", "102");
        iaResponde(id -> ok(id));

        servicio.procesarTanda();

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> lote = ArgumentCaptor.forClass(Map.class);
        ArgumentCaptor<String> idCorrelacion = ArgumentCaptor.forClass(String.class);
        verify(ia).procesar(lote.capture(), idCorrelacion.capture());
        Map<String, Object> enviado = lote.getValue();
        assertThat(enviado.get("versionContrato")).isEqualTo("1.0");
        assertThat(enviado.get("fuente")).isEqualTo("discord");
        assertThat(enviado.get("modo")).isEqualTo("historial");
        assertThat(enviado.get("servidorId")).isEqualTo(SERVIDOR);
        assertThat((String) enviado.get("loteId")).startsWith("clasif-").isEqualTo(idCorrelacion.getValue());
        assertThat((String) enviado.get("generadoEn")).matches("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{3}Z");
        // Las cajas tal cual se guardaron, del mensaje más antiguo al más nuevo
        assertThat(cajas(enviado)).extracting(c -> c.get("id")).containsExactly("101", "102");
        assertThat(cajas(enviado).get(0)).isEqualTo(caja("101", "texto 101"));
    }

    @Test
    void unResultadoPorReglaSeGuardaSinSentimientoNiTema() {
        pendientes("101");
        iaResponde(id -> new RespuestaIa.Resultado(id, "OK", "regla", "OTRO", 1.0, null, null, "bot"));

        servicio.procesarTanda();

        assertThat(fila("101")).containsEntry("estado_clasificacion", "OK").containsEntry("metodo_clasificacion", "regla")
                .containsEntry("sentimiento", null).containsEntry("tema", null);
    }

    // ── Caso 2: ERROR en 1 de 3; al tercer error queda ERROR ──

    @Test
    void unErrorDeLaIaSumaIntentosHastaQuedarEnError() {
        pendientes("101", "102", "103");
        iaResponde(id -> id.equals("102") ? error(id) : ok(id));

        servicio.procesarTanda();
        assertThat(fila("102")).containsEntry("estado_clasificacion", "PENDIENTE").containsEntry("intentos_clasificacion", 1);
        assertThat(fila("101").get("estado_clasificacion")).isEqualTo("OK");

        servicio.procesarTanda();
        assertThat(fila("102")).containsEntry("estado_clasificacion", "PENDIENTE").containsEntry("intentos_clasificacion", 2);

        Resumen tercera = servicio.procesarTanda();
        assertThat(tercera.error()).isEqualTo(1);
        Map<String, Object> f = fila("102");
        assertThat(f).containsEntry("estado_clasificacion", "ERROR").containsEntry("intentos_clasificacion", 3);
        assertThat(f.get("intencion")).isNull();  // F4: sin etiquetas inventadas
        assertThat(f.get("reservado_hasta")).isNull();
    }

    // ── Caso 3: falla toda la llamada ──

    @Test
    void siLaIaNoRespondeNingunoCambiaDeEstadoYSumanIntentos() {
        pendientes("101", "102");
        when(ia.procesar(any(), anyString())).thenThrow(new IaNoDisponibleException("La IA respondió HTTP 500"));

        for (int vuelta = 1; vuelta <= 4; vuelta++) {
            Resumen r = servicio.procesarTanda();
            assertThat(r.reintento()).isEqualTo(2);
            for (String id : List.of("101", "102")) {
                assertThat(fila(id)).containsEntry("estado_clasificacion", "PENDIENTE")
                        .containsEntry("intentos_clasificacion", vuelta).containsEntry("reservado_hasta", null);
            }
        }
    }

    // ── Caso 4: el mensaje cambió mientras la IA lo procesaba ──

    @Test
    void siElMensajeCambioMientrasTantoNoSeGuardaElResultadoViejo() {
        pendientes("101", "102");
        when(ia.procesar(any(), anyString())).thenAnswer(inv -> {
            // Mientras la IA "piensa", llega el lote de la hora con el texto editado
            upsert.upsert(datos("102", "texto editado"));
            return respuesta(inv.getArgument(0), this::ok);
        });

        Resumen r = servicio.procesarTanda();

        assertThat(r.ok()).isEqualTo(1);
        assertThat(r.cambiaron()).isEqualTo(1);
        Map<String, Object> f = fila("102");
        assertThat(f).containsEntry("estado_clasificacion", "PENDIENTE").containsEntry("texto", "texto editado")
                .containsEntry("intentos_clasificacion", 0).containsEntry("reservado_hasta", null);
        assertThat(f.get("intencion")).isNull();
        // En la siguiente vuelta se clasifica el texto nuevo
        servicio.procesarTanda();
        assertThat(fila("102").get("estado_clasificacion")).isEqualTo("OK");
    }

    // ── Caso 5: OK y ERROR no se vuelven a enviar ──

    @Test
    void losMensajesOkOErrorNoSeVuelvenAEnviar() {
        pendientes("101", "102");
        jdbc.update("UPDATE mensajes SET estado_clasificacion = 'OK' WHERE discord_id = '101'");
        jdbc.update("UPDATE mensajes SET estado_clasificacion = 'ERROR' WHERE discord_id = '102'");

        assertThat(servicio.procesarTanda().tomados()).isZero();
        verifyNoInteractions(ia);
    }

    // ── Caso 6: más pendientes que la tanda ──

    @Test
    void masPendientesQueLaTandaSeProcesanEnVariasVueltas() {
        pendientes("101", "102", "103", "104", "105", "106", "107");
        iaResponde(id -> ok(id));

        assertThat(servicio.procesarTanda().tomados()).isEqualTo(5);
        assertThat(servicio.procesarTanda().tomados()).isEqualTo(2);
        assertThat(servicio.procesarTanda().tomados()).isZero();
        verify(ia, times(2)).procesar(any(), anyString());
        assertThat(jdbc.queryForObject("SELECT count(*) FROM mensajes WHERE estado_clasificacion = 'OK'", Integer.class))
                .isEqualTo(7);
    }

    // ── Caso 7: la V2 rechaza valores fuera de las listas ──

    @Test
    void laV2RechazaTemaOSentimientoFueraDeLaLista() {
        pendientes("101");

        assertThatThrownBy(() -> jdbc.update("UPDATE mensajes SET tema = 'deportes' WHERE discord_id = '101'"))
                .isInstanceOf(DataIntegrityViolationException.class).hasMessageContaining("mensajes_tema_check");
        assertThatThrownBy(() -> jdbc.update("UPDATE mensajes SET sentimiento = 'FELIZ' WHERE discord_id = '101'"))
                .isInstanceOf(DataIntegrityViolationException.class).hasMessageContaining("mensajes_sentimiento_check");
        assertThatThrownBy(() -> jdbc.update("UPDATE mensajes SET metodo_clasificacion = 'magia' WHERE discord_id = '101'"))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    void unaEtiquetaFueraDeLaListaCuentaComoErrorDeLaIa() {
        pendientes("101");
        iaResponde(id -> new RespuestaIa.Resultado(id, "OK", "llm", "TESTIMONIO", 0.9, "POSITIVO", "deportes", "x"));

        servicio.procesarTanda();

        assertThat(fila("101")).containsEntry("estado_clasificacion", "PENDIENTE").containsEntry("intentos_clasificacion", 1)
                .containsEntry("tema", null);
    }

    // ── 422: solo el mensaje señalado suma intento ──

    @Test
    void un422PenalizaSoloAlMensajeQueLaIaSenala() {
        pendientes("101", "102", "103");
        when(ia.procesar(any(), anyString())).thenThrow(new IaRechazoException(List.of(
                new ErrorCampo("mensajes.1.autor.tipo", "Input should be 'persona', 'botPropio' or 'otroBot'"))));

        servicio.procesarTanda();

        assertThat(fila("102")).containsEntry("estado_clasificacion", "PENDIENTE").containsEntry("intentos_clasificacion", 1);
        assertThat(fila("101")).containsEntry("intentos_clasificacion", 0).containsEntry("reservado_hasta", null);
        assertThat(fila("103")).containsEntry("intentos_clasificacion", 0).containsEntry("reservado_hasta", null);

        servicio.procesarTanda();
        servicio.procesarTanda();
        assertThat(fila("102").get("estado_clasificacion")).isEqualTo("ERROR");  // no se reintenta sin fin
        assertThat(fila("101").get("estado_clasificacion")).isEqualTo("PENDIENTE");
    }

    @Test
    void un422SinIndicarElMensajePenalizaATodos() {
        pendientes("101", "102");
        when(ia.procesar(any(), anyString())).thenThrow(new IaRechazoException(List.of(new ErrorCampo("modo", "Field required"))));

        servicio.procesarTanda();

        assertThat(fila("101").get("intentos_clasificacion")).isEqualTo(1);
        assertThat(fila("102").get("intentos_clasificacion")).isEqualTo(1);
    }

    // ── Reservas y SKIP LOCKED ──

    @Test
    void unMensajeReservadoNoSeTomaHastaQueVenzaLaReserva() {
        pendientes("101");
        iaResponde(id -> ok(id));
        assertThat(repo.reservar(5, 120)).hasSize(1);  // otra ejecución lo tiene reservado

        assertThat(servicio.procesarTanda().tomados()).isZero();

        jdbc.update("UPDATE mensajes SET reservado_hasta = now() - interval '1 minute'");  // esa ejecución murió
        assertThat(servicio.procesarTanda().ok()).isEqualTo(1);
    }

    @Test
    void dosReservasAlMismoTiempoNoTomanLosMismosMensajes() throws Exception {
        pendientes("101", "102", "103", "104", "105", "106");
        ExecutorService hilos = Executors.newFixedThreadPool(2);
        CountDownLatch largada = new CountDownLatch(1);
        try {
            Callable<List<Pendiente>> reservar = () -> {
                largada.await();
                return repo.reservar(3, 120);
            };
            Future<List<Pendiente>> a = hilos.submit(reservar);
            Future<List<Pendiente>> b = hilos.submit(reservar);
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
    void losMensajesSinServidorNoSeTomanYSeCuentan() {
        upsert.upsert(new DatosMensaje("101", "c", "a", AutorTipo.persona, AutorRol.miembro, false,
                Instant.parse("2026-09-28T18:56:30.331Z"), null, "viejo", caja("101", "viejo"), "1.0", null));

        assertThat(servicio.procesarTanda().tomados()).isZero();
        assertThat(servicio.contarSinServidor()).isEqualTo(1);
        verifyNoInteractions(ia);

        // Cuando el lote de la hora lo reenvía, se completa el servidor y ya se puede clasificar
        upsert.upsert(datos("101", "viejo"));
        assertThat(servicio.contarSinServidor()).isZero();
        iaResponde(id -> ok(id));
        assertThat(servicio.procesarTanda().ok()).isEqualTo(1);
    }

    // ── Ayudas ──

    private void pendientes(String... ids) {
        for (String id : ids) {
            upsert.upsert(datos(id, "texto " + id));
        }
    }

    private static DatosMensaje datos(String id, String texto) {
        // La fecha crece con el id: así el orden "más antiguo primero" es 101, 102, ...
        Instant fecha = Instant.parse("2026-09-28T18:56:30.331Z").plusSeconds(Long.parseLong(id));
        return new DatosMensaje(id, "1554158212742127821", "sim-ana-perez", AutorTipo.persona, AutorRol.miembro,
                true, fecha, null, texto, caja(id, texto), "1.0", SERVIDOR);
    }

    private static Map<String, Object> caja(String id, String texto) {
        Map<String, Object> c = new LinkedHashMap<>();
        c.put("id", id);
        c.put("textoOriginal", texto);
        c.put("autor", Map.of("id", "sim-ana-perez", "tipo", "persona", "rol", "miembro"));
        return c;
    }

    private void iaResponde(Function<String, RespuestaIa.Resultado> porId) {
        when(ia.procesar(any(), anyString())).thenAnswer(inv -> respuesta(inv.getArgument(0), porId));
    }

    private RespuestaIa respuesta(Map<String, Object> lote, Function<String, RespuestaIa.Resultado> porId) {
        List<RespuestaIa.Resultado> resultados = new ArrayList<>();
        for (Map<String, Object> c : cajas(lote)) {
            resultados.add(porId.apply((String) c.get("id")));
        }
        return new RespuestaIa("1.0", (String) lote.get("loteId"), resultados, new RespuestaIa.Metricas(10, 100, 20));
    }

    private RespuestaIa.Resultado ok(String id) {
        return new RespuestaIa.Resultado(id, "OK", "llm", "TESTIMONIO", 0.9, "POSITIVO", "empleo", "logro");
    }

    private static RespuestaIa.Resultado error(String id) {
        return new RespuestaIa.Resultado(id, "ERROR", "llm", null, null, null, null, "El LLM no respondió en 20 s.");
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> cajas(Map<String, Object> lote) {
        return (List<Map<String, Object>>) lote.get("mensajes");
    }

    private Map<String, Object> fila(String discordId) {
        return jdbc.queryForMap("""
                SELECT estado_clasificacion, intencion, confianza, sentimiento, tema, metodo_clasificacion,
                       intentos_clasificacion, clasificado_en, reservado_hasta, texto
                  FROM mensajes WHERE discord_id = ?""", discordId);
    }

    private static Set<String> ids(List<Pendiente> pendientes) {
        Set<String> ids = new HashSet<>();
        pendientes.forEach(p -> ids.add(p.discordId()));
        return ids;
    }
}
