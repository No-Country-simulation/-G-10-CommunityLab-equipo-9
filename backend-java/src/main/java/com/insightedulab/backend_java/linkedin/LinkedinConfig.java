package com.insightedulab.backend_java.linkedin;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

import java.time.Duration;

/**
 * Configuración del cliente HTTP para la API de LinkedIn.
 */
@Configuration
@EnableConfigurationProperties(LinkedinProperties.class)
public class LinkedinConfig {

    public static final Duration TIEMPO_CONEXION = Duration.ofSeconds(5);
    public static final Duration TIEMPO_LECTURA = Duration.ofSeconds(15);

    @Bean
    public RestClient linkedinRestClient() {
        SimpleClientHttpRequestFactory tiempos = new SimpleClientHttpRequestFactory();
        tiempos.setConnectTimeout(TIEMPO_CONEXION);
        tiempos.setReadTimeout(TIEMPO_LECTURA);
        return RestClient.builder().requestFactory(tiempos).build();
    }
}
