package com.insightedulab.backend_java.oci;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import java.net.URI;

/**
 * Sube un archivo al bucket de OCI con una URL PAR (T09, N7).
 *
 * <p>📘 Con una PAR de bucket se sube así: {@code PUT <PAR><nombre-del-objeto>}, con el archivo en el cuerpo
 * (la PAR termina en {@code /o/}).
 *
 * <p>La URL PAR es una credencial: quien la tenga puede escribir en el bucket. Por eso este cliente no la
 * escribe nunca, ni completa ni recortada, ni en un mensaje de error: solo el código HTTP o la clase del
 * error. Tampoco registra las excepciones de la llamada, porque su mensaje lleva la URL.
 */
@Component
public class OciClient {

    private final RestClient http;
    private final String par;

    public OciClient(@Qualifier("ociRestClient") RestClient http, OciProperties propiedades) {
        this.http = http;
        this.par = propiedades.parUrl();
    }

    /**
     * Sube {@code json} como {@code objeto} (por ejemplo, {@code generados/FAQ/2026-10-05/borrador-3.json}).
     * Si el objeto ya existe, queda el contenido nuevo (🔎 la documentación de Oracle no lo aclara: se
     * comprueba en la prueba real).
     *
     * @throws OciException si OCI no responde 2xx, no responde a tiempo o la PAR no sirve
     */
    public void subir(String objeto, byte[] json) {
        URI destino;
        try {
            destino = URI.create(par + objeto);
        } catch (IllegalArgumentException e) {
            throw new OciException("La PAR no forma una URL válida con el nombre del objeto");
        }
        try {
            http.put()
                    .uri(destino)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(json)
                    .retrieve()
                    .onStatus(estado -> !estado.is2xxSuccessful(), (pedido, respuesta) -> {
                        throw new OciException("OCI respondió HTTP " + respuesta.getStatusCode().value());
                    })
                    .toBodilessEntity();
        } catch (ResourceAccessException e) {
            // Conexión rechazada o tiempo agotado. El mensaje de e lleva la URL: solo se dice la clase
            throw new OciException("No se pudo hablar con OCI: " + e.getMostSpecificCause().getClass().getSimpleName());
        } catch (RestClientException e) {
            throw new OciException("Falló la llamada a OCI: " + e.getClass().getSimpleName());
        }
    }
}
