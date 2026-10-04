package com.insightedulab.backend_java;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightedulab.backend_java.client.IaNoDisponibleException;
import com.insightedulab.backend_java.client.IaRechazoException;
import com.insightedulab.backend_java.client.NlpDataClient;
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
        cliente = new NlpDataClient(RestClientConfig.configurar(builder, "http://ia:8000", "clave-ia").build(),
                new ObjectMapper());
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
}
