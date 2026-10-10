package com.insightedulab.backend_java.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

import java.time.Duration;

/**
 * Conexión de Java con la IA (contrato Java ↔ IA v1, docs/contratos/JAVA_IA_v1.md).
 * Tiempos de D4 y F8: modelo 20 s < Java → IA 30 s < bot → Java 40 s.
 * La FAQ semanal (T06b) tiene su propio cliente: la IA puede tardar hasta 120 s, y Java la espera 150 s.
 */
@Configuration
public class RestClientConfig {

    public static final Duration TIEMPO_CONEXION = Duration.ofSeconds(5);
    public static final Duration TIEMPO_LECTURA = Duration.ofSeconds(30);
    /** Mayor que el tope de la IA para /v1/faq (FAQ_SEMANAL_TOPE_S, 120 s). Se cambia con faq.tiempo-lectura-s */
    public static final int TIEMPO_LECTURA_FAQ_S = 150;

    @Bean
    public RestClient iaRestClient(@Value("${python.nlp.service.url}") String urlIa,
                                   @Value("${ia.api-key:}") String apiKeyIa) {
        SimpleClientHttpRequestFactory tiempos = new SimpleClientHttpRequestFactory();
        tiempos.setConnectTimeout(TIEMPO_CONEXION);
        tiempos.setReadTimeout(TIEMPO_LECTURA);
        return configurar(RestClient.builder().requestFactory(tiempos), urlIa, apiKeyIa).build();
    }

    /** El de POST /v1/faq: mismas cabeceras, con un tiempo de lectura propio (la FAQ no tiene a nadie esperando). */
    @Bean
    public RestClient iaRestClientFaq(@Value("${python.nlp.service.url}") String urlIa,
                                      @Value("${ia.api-key:}") String apiKeyIa,
                                      @Value("${faq.tiempo-lectura-s:" + TIEMPO_LECTURA_FAQ_S + "}") int lecturaS) {
        SimpleClientHttpRequestFactory tiempos = new SimpleClientHttpRequestFactory();
        tiempos.setConnectTimeout(TIEMPO_CONEXION);
        tiempos.setReadTimeout(Duration.ofSeconds(lecturaS));
        return configurar(RestClient.builder().requestFactory(tiempos), urlIa, apiKeyIa).build();
    }

    /** URL y cabeceras comunes. Separado para que las pruebas usen el mismo armado con un servidor simulado. */
    public static RestClient.Builder configurar(RestClient.Builder builder, String urlIa, String apiKeyIa) {
        return builder
                .baseUrl(urlIa)
                .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                .defaultHeader(HttpHeaders.ACCEPT, MediaType.APPLICATION_JSON_VALUE)
                // S2: la IA exige la clave en /v1/procesar
                .defaultHeader("X-Api-Key", apiKeyIa == null ? "" : apiKeyIa.strip());
    }
}
