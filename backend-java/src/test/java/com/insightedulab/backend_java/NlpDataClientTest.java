package com.insightedulab.backend_java;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightedulab.backend_java.client.IaNoDisponibleException;
import com.insightedulab.backend_java.client.IaRechazoException;
import com.insightedulab.backend_java.client.NlpDataClient;
import com.insightedulab.backend_java.client.RespuestaFaqSemanal;
import com.insightedulab.backend_java.client.RespuestaGenerar;
import com.insightedulab.backend_java.client.RespuestaIa;
import com.insightedulab.backend_java.config.RestClientConfig;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import java.net.SocketTimeoutException;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.jsonPath;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withException;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

/** El cliente HTTP de la IA, con un servidor simulado: no hace falta Spring ni la base. */
class NlpDataClientTest {

    private static final String URL = "http://ia:8000/v1/procesar";
    private static final Map<String, Object> LOTE = Map.of("loteId", "clasif-1", "mensajes", java.util.List.of());

    private MockRestServiceServer ia;
    private NlpDataClient cliente;

    @BeforeEach
    void armar() {
        RestClient.Builder builder = RestClient.builder();
        ia = MockRestServiceServer.bindTo(builder).build();
        // El mismo armado que usa la aplicación (URL y cabeceras), con el servidor simulado
        RestClient rest = RestClientConfig.configurar(builder, "http://ia:8000", "clave-ia").build();
        cliente = new NlpDataClient(rest, rest, new ObjectMapper());  // en la aplicación, la FAQ usa otro tiempo
    }

    @Test
    void enviaElLoteConLaClaveYElIdDeCorrelacionYLeeLaRespuesta() {
        ia.expect(requestTo(URL)).andExpect(method(HttpMethod.POST))
                .andExpect(header("X-Api-Key", "clave-ia"))
                .andExpect(header("X-Id-Correlacion", "clasif-1"))
                .andExpect(jsonPath("$.loteId").value("clasif-1"))
                .andRespond(withSuccess("""
                        {"versionContratoIa":"1.0","loteId":"clasif-1",
                         "resultados":[{"discordId":"101","estado":"OK","metodo":"llm","intencion":"TESTIMONIO",
                                        "confianza":0.95,"sentimiento":"MUY_POSITIVO","tema":"empleo",
                                        "razon":"logro","respuesta":null}],
                         "metricas":{"duracionMs":1200,"tokensIn":500,"tokensOut":60}}
                        """, MediaType.APPLICATION_JSON));

        RespuestaIa r = cliente.procesar(LOTE, "clasif-1");

        assertThat(r.resultados()).hasSize(1);
        RespuestaIa.Resultado resultado = r.resultados().get(0);
        assertThat(resultado.ok()).isTrue();
        assertThat(resultado.tema()).isEqualTo("empleo");
        assertThat(resultado.confianza()).isEqualTo(0.95);
        ia.verify();
    }

    // ── T06: POST /v1/generar, con las mismas cabeceras y el mismo manejo de errores ──

    @Test
    void generarEnviaElPedidoConLaClaveYLeeLaRespuesta() {
        ia.expect(requestTo("http://ia:8000/v1/generar")).andExpect(method(HttpMethod.POST))
                .andExpect(header("X-Api-Key", "clave-ia"))
                .andExpect(header("X-Id-Correlacion", "gen-1"))
                .andExpect(jsonPath("$.pedidoId").value("gen-1"))
                .andRespond(withSuccess("""
                        {"versionContratoIa":"1.0","pedidoId":"gen-1","discordId":"101","estado":"OK",
                         "publicable":true,"motivo":"Es una contratación.","postLinkedin":"post","casoExito":"caso",
                         "metricas":{"duracionMs":6120,"tokensIn":1450,"tokensOut":520}}
                        """, MediaType.APPLICATION_JSON));

        RespuestaGenerar r = cliente.generar(Map.of("pedidoId", "gen-1"), "gen-1");

        assertThat(r.ok()).isTrue();
        assertThat(r.publicable()).isTrue();
        assertThat(r.postLinkedin()).isEqualTo("post");
        assertThat(r.metricas().tokensIn()).isEqualTo(1450);
        ia.verify();
    }

    @Test
    void generarCon500Y422LanzaLasMismasExcepciones() {
        ia.expect(requestTo("http://ia:8000/v1/generar")).andRespond(withStatus(HttpStatus.INTERNAL_SERVER_ERROR));
        assertThatThrownBy(() -> cliente.generar(Map.of(), "gen-1")).isInstanceOf(IaNoDisponibleException.class);

        ia.reset();
        ia.expect(requestTo("http://ia:8000/v1/generar")).andRespond(withStatus(HttpStatus.UNPROCESSABLE_ENTITY)
                .contentType(MediaType.APPLICATION_JSON)
                .body("{\"codigo\":\"CONTRATO_INVALIDO\",\"mensaje\":\"x\",\"errores\":[],\"idCorrelacion\":\"gen-1\"}"));
        assertThatThrownBy(() -> cliente.generar(Map.of(), "gen-1")).isInstanceOf(IaRechazoException.class);
    }

    @Test
    void un422EsUnRechazoConLosCamposQueFallan() {
        ia.expect(requestTo(URL)).andRespond(withStatus(HttpStatus.UNPROCESSABLE_ENTITY)
                .contentType(MediaType.APPLICATION_JSON)
                .body("""
                        {"codigo":"CONTRATO_INVALIDO","mensaje":"El lote no cumple el contrato v1.",
                         "errores":[{"campo":"mensajes.2.autor.tipo","problema":"Input should be ..."}],
                         "idCorrelacion":"clasif-1"}
                        """));

        assertThatThrownBy(() -> cliente.procesar(LOTE, "clasif-1"))
                .isInstanceOf(IaRechazoException.class)
                .satisfies(e -> assertThat(((IaRechazoException) e).getErrores())
                        .extracting(c -> c.campo()).containsExactly("mensajes.2.autor.tipo"));
    }

    @Test
    void un500EsUnFalloPasajero() {
        ia.expect(requestTo(URL)).andRespond(withStatus(HttpStatus.INTERNAL_SERVER_ERROR));

        assertThatThrownBy(() -> cliente.procesar(LOTE, "clasif-1"))
                .isInstanceOf(IaNoDisponibleException.class).hasMessageContaining("500");
    }

    @Test
    void unaClaveRechazadaEsUnFalloPasajero() {
        ia.expect(requestTo(URL)).andRespond(withStatus(HttpStatus.UNAUTHORIZED));

        assertThatThrownBy(() -> cliente.procesar(LOTE, "clasif-1"))
                .isInstanceOf(IaNoDisponibleException.class).hasMessageContaining("401");
    }

    @Test
    void unTiempoAgotadoEsUnFalloPasajero() {
        ia.expect(requestTo(URL)).andRespond(withException(new SocketTimeoutException("Read timed out")));

        assertThatThrownBy(() -> cliente.procesar(LOTE, "clasif-1"))
                .isInstanceOf(IaNoDisponibleException.class).hasMessageContaining("SocketTimeoutException");
    }

    @Test
    void losTiemposSonLosDeD4() {
        assertThat(RestClientConfig.TIEMPO_CONEXION).hasSeconds(5);
        assertThat(RestClientConfig.TIEMPO_LECTURA).hasSeconds(30);
    }

    // ── T06b: POST /v1/faq ──

    @Test
    void faqEnviaElPedidoConLaClaveYLeeLosGrupos() {
        ia.expect(requestTo("http://ia:8000/v1/faq")).andExpect(method(HttpMethod.POST))
                .andExpect(header("X-Api-Key", "clave-ia"))
                .andExpect(header("X-Id-Correlacion", "faq-1"))
                .andExpect(jsonPath("$.semana").value("2026-W40"))
                .andRespond(withSuccess("""
                        {"versionContratoIa":"1.0","pedidoId":"faq-1","semana":"2026-W40","estado":"OK",
                         "texto":"# Preguntas frecuentes","motivo":"1 preguntas repetidas, 1 con respuesta.",
                         "grupos":[{"pregunta":"¿Plazo?","personas":3,"respondida":true,"origen":"agenteFaq",
                                    "fuentes":["Reglamento.pdf (Pág. 4)"],"motivo":null}],
                         "metricas":{"duracionMs":38250,"tokensIn":2210,"tokensOut":240}}
                        """, MediaType.APPLICATION_JSON));

        RespuestaFaqSemanal r = cliente.faq(Map.of("semana", "2026-W40"), "faq-1");

        assertThat(r.ok()).isTrue();
        assertThat(r.grupos()).hasSize(1);
        assertThat(r.grupos().get(0).personas()).isEqualTo(3);
        assertThat(r.grupos().get(0).fuentes()).containsExactly("Reglamento.pdf (Pág. 4)");
        assertThat(r.metricas().tokensIn()).isEqualTo(2210);
        ia.verify();
    }

    @Test
    void faqCon500Y422LanzaLasMismasExcepciones() {
        ia.expect(requestTo("http://ia:8000/v1/faq")).andRespond(withStatus(HttpStatus.INTERNAL_SERVER_ERROR));
        assertThatThrownBy(() -> cliente.faq(Map.of(), "faq-1")).isInstanceOf(IaNoDisponibleException.class);

        ia.reset();
        ia.expect(requestTo("http://ia:8000/v1/faq")).andRespond(withStatus(HttpStatus.UNPROCESSABLE_ENTITY)
                .contentType(MediaType.APPLICATION_JSON)
                .body("{\"codigo\":\"CONTRATO_INVALIDO\",\"mensaje\":\"x\",\"errores\":[],\"idCorrelacion\":\"faq-1\"}"));
        assertThatThrownBy(() -> cliente.faq(Map.of(), "faq-1")).isInstanceOf(IaRechazoException.class);
    }

    @Test
    void laFaqEsperaMasQueElTopeDeLaIa() {
        // La IA corta /v1/faq a los 120 s (FAQ_SEMANAL_TOPE_S): Java tiene que esperar más
        assertThat(RestClientConfig.TIEMPO_LECTURA_FAQ_S).isEqualTo(150).isGreaterThan(120);
    }
}
