package com.insightedulab.backend_java.oci;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

import java.time.Duration;

/**
 * Conexión de Java con OCI (T09). Las propiedades existen aunque la tarea programada esté apagada:
 * el servicio las necesita igual.
 * El RestClient no lleva baseUrl: la URL PAR es una credencial y la arma el cliente en cada subida.
 */
@Configuration
@EnableConfigurationProperties(OciProperties.class)
public class OciConfig {

    public static final Duration TIEMPO_CONEXION = Duration.ofSeconds(5);
    public static final Duration TIEMPO_LECTURA = Duration.ofSeconds(30);

    @Bean
    public RestClient ociRestClient() {
        SimpleClientHttpRequestFactory tiempos = new SimpleClientHttpRequestFactory();
        tiempos.setConnectTimeout(TIEMPO_CONEXION);
        tiempos.setReadTimeout(TIEMPO_LECTURA);
        return RestClient.builder().requestFactory(tiempos).build();
    }
}
