package com.insightedulab.backend_java.linkedin;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Propiedades para la publicación directa en LinkedIn por código.
 */
@ConfigurationProperties(prefix = "linkedin")
public record LinkedinProperties(
        boolean habilitada,
        String accessToken,
        String authorUrn,
        String apiUrl
) {
    public static final String URL_DEFECTO = "https://api.linkedin.com/rest/posts";

    public LinkedinProperties {
        if (apiUrl == null || apiUrl.isBlank()) {
            apiUrl = URL_DEFECTO;
        }
    }

    /**
     * true si la integración está habilitada y cuenta con el token de acceso y el identificador de autor.
     * Si no, la publicación se ejecuta en modo simulado para pruebas locales seguras.
     */
    public boolean estaConfigurado() {
        return habilitada
                && accessToken != null && !accessToken.isBlank()
                && authorUrn != null && !authorUrn.isBlank();
    }
}
