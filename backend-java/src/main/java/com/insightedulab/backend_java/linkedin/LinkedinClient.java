package com.insightedulab.backend_java.linkedin;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.net.URI;

/**
 * Cliente HTTP directo hacia la API de LinkedIn (POST https://api.linkedin.com/rest/posts).
 */
@Component
public class LinkedinClient {

    private static final Logger log = LoggerFactory.getLogger(LinkedinClient.class);

    private final RestClient http;
    private final LinkedinProperties propiedades;

    public LinkedinClient(@Qualifier("linkedinRestClient") RestClient http, LinkedinProperties propiedades) {
        this.http = http;
        this.propiedades = propiedades;
    }

    /**
     * Envía la petición oficial a la API de LinkedIn para publicar un post.
     *
     * @param request Cuerpo con autor, texto y visibilidad
     * @return El ID / URN del post creado en LinkedIn
     */
    public String publicar(LinkedinPostRequest request) {
        URI destino = URI.create(propiedades.apiUrl());

        ResponseEntity<Void> respuesta = http.post()
                .uri(destino)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + propiedades.accessToken())
                .header("LinkedIn-Version", "202401")
                .header("X-Restli-Protocol-Version", "2.0.0")
                .contentType(MediaType.APPLICATION_JSON)
                .body(request)
                .retrieve()
                .onStatus(estado -> !estado.is2xxSuccessful(), (req, resp) -> {
                    log.error("LinkedIn API respondió HTTP {}", resp.getStatusCode().value());
                    throw new RuntimeException("LinkedIn respondió HTTP " + resp.getStatusCode().value());
                })
                .toBodilessEntity();

        String idPost = respuesta.getHeaders().getFirst("x-restli-id");
        if (idPost == null || idPost.isBlank()) {
            idPost = respuesta.getHeaders().getFirst("Location");
        }
        return idPost != null ? idPost : "urn:li:post:desconocido";
    }
}
