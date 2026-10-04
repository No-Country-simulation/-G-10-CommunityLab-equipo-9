package com.insightedulab.backend_java.client;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightedulab.backend_java.error.ErrorApi;
import com.insightedulab.backend_java.seguridad.IdCorrelacionFilter;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;

import java.io.IOException;
import java.util.List;
import java.util.Map;

/**
 * Cliente de la IA (contrato Java ↔ IA v1):
 * POST /v1/procesar con un Lote del contrato v1, POST /v1/generar con un logro (Agente-Mod, T06)
 * y POST /v1/faq con las dudas de la semana (FAQ semanal, T06b).
 *
 * <ul>
 *   <li>200 → {@link RespuestaIa}, {@link RespuestaGenerar} o {@link RespuestaFaqSemanal}.</li>
 *   <li>422 → {@link IaRechazoException}: el lote está mal armado (error nuestro, no pasajero).</li>
 *   <li>Otro error HTTP, tiempo agotado (30 s; 150 s en /v1/faq) o IA caída → {@link IaNoDisponibleException} (pasajero).</li>
 * </ul>
 */
@Component
public class NlpDataClient {

    public static final String RUTA_PROCESAR = "/v1/procesar";
    public static final String RUTA_GENERAR = "/v1/generar";
    public static final String RUTA_FAQ = "/v1/faq";

    private final RestClient iaRestClient;
    private final RestClient iaRestClientFaq;
    private final ObjectMapper objectMapper;

    /** iaRestClientFaq: el mismo armado, con un tiempo de lectura mayor (la FAQ puede tardar más de 30 s). */
    public NlpDataClient(@Qualifier("iaRestClient") RestClient iaRestClient,
                         @Qualifier("iaRestClientFaq") RestClient iaRestClientFaq, ObjectMapper objectMapper) {
        this.iaRestClient = iaRestClient;
        this.iaRestClientFaq = iaRestClientFaq;
        this.objectMapper = objectMapper;
    }

    public RespuestaIa procesar(Map<String, Object> lote, String idCorrelacion) {
        RespuestaIa respuesta = enviar(iaRestClient, RUTA_PROCESAR, lote, idCorrelacion, RespuestaIa.class);
        if (respuesta == null || respuesta.resultados() == null) {
            throw new IaNoDisponibleException("La IA respondió sin resultados");
        }
        return respuesta;
    }

    /** El Agente-Mod: post de LinkedIn y caso de éxito de un logro (§9 del contrato). Mismas cabeceras y tiempos. */
    public RespuestaGenerar generar(Map<String, Object> pedido, String idCorrelacion) {
        RespuestaGenerar respuesta = enviar(iaRestClient, RUTA_GENERAR, pedido, idCorrelacion, RespuestaGenerar.class);
        if (respuesta == null || respuesta.estado() == null) {
            throw new IaNoDisponibleException("La IA respondió sin resultado");
        }
        return respuesta;
    }

    /** La FAQ semanal (§10 del contrato). Mismas cabeceras y excepciones; su propio tiempo de lectura. */
    public RespuestaFaqSemanal faq(Map<String, Object> pedido, String idCorrelacion) {
        RespuestaFaqSemanal respuesta = enviar(iaRestClientFaq, RUTA_FAQ, pedido, idCorrelacion, RespuestaFaqSemanal.class);
        if (respuesta == null || respuesta.estado() == null) {
            throw new IaNoDisponibleException("La IA respondió sin resultado");
        }
        return respuesta;
    }

    private <T> T enviar(RestClient cliente, String ruta, Map<String, Object> cuerpo, String idCorrelacion, Class<T> tipo) {
        try {
            return cliente.post()
                    .uri(ruta)
                    .header(IdCorrelacionFilter.CABECERA, idCorrelacion)
                    .body(cuerpo)
                    .retrieve()
                    .onStatus(estado -> estado.value() == 422, (pedido, r) -> {
                        throw new IaRechazoException(erroresDe(r.getBody().readAllBytes()));
                    })
                    .onStatus(HttpStatusCode::isError, (pedido, r) -> {
                        throw new IaNoDisponibleException("La IA respondió HTTP " + r.getStatusCode().value());
                    })
                    .body(tipo);
        } catch (ResourceAccessException e) {
            // Conexión rechazada o tiempo agotado
            throw new IaNoDisponibleException("No se pudo hablar con la IA: " + e.getMostSpecificCause().getClass().getSimpleName(), e);
        }
    }

    private List<ErrorApi.ErrorCampo> erroresDe(byte[] cuerpo) {
        try {
            ErrorApi error = objectMapper.readValue(cuerpo, ErrorApi.class);
            return error.errores() == null ? List.of() : error.errores();
        } catch (IOException e) {
            return List.of();  // 422 sin el formato común: no se sabe qué mensaje falló
        }
    }
}
