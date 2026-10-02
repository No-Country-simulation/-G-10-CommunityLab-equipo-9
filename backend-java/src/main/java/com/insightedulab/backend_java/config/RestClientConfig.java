package com.insightedulab.backend_java.config;


import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpHeaders;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

import java.time.Duration;

@Configuration
public class RestClientConfig {

    @Value("${python.nlp.service.url}")
    private String nlpServiceUrl;

    @Bean
    public RestClient nlpRestClient(){
// Configuración de timeouts para peticiones hacia el microservicio de Python
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Duration.ofSeconds(5)); // Tiempo máximo para establecer conexión
        requestFactory.setReadTimeout(Duration.ofSeconds(15));   // Tiempo máximo esperando respuesta del NLP

        return RestClient.builder()
                .baseUrl(nlpServiceUrl)
                .requestFactory(requestFactory)
                .defaultHeader(HttpHeaders.CONTENT_TYPE, "application/json")
                .defaultHeader("Accept", "application/json")
                .build();
    }
}