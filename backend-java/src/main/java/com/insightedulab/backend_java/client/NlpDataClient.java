package com.insightedulab.backend_java.client;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class NlpDataClient {

    private static final Logger log = LoggerFactory.getLogger(NlpDataClient.class);
    private final RestClient nlpRestClient;

    public NlpDataClient(
            RestClient.Builder restClientBuilder,
            @Value("${python.nlp.service.url:http://localhost:8000}") String nlpServiceUrl
    ) {
        this.nlpRestClient = restClientBuilder
                .baseUrl(nlpServiceUrl)
                .build();
    }

    /**
     * A la espera de confimacion para continuar
     * Envía la estructura completa (datos + historialTransacciones) hacia FastAPI
     */

}