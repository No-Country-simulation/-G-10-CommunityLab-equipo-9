package com.insightedulab.backend_java.seguridad;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.Map;

/**
 * Propiedades "seguridad.*" de application.properties.
 *
 * @param apiKeys        cliente → clave (ingesta; después bot y panel). Las vacías no cuentan
 * @param maxBytesCuerpo tope del cuerpo de cada pedido
 */
@ConfigurationProperties(prefix = "seguridad")
public record SeguridadProperties(Map<String, String> apiKeys, Long maxBytesCuerpo) {

    public SeguridadProperties {
        apiKeys = apiKeys == null ? Map.of() : Map.copyOf(apiKeys);
        maxBytesCuerpo = maxBytesCuerpo == null ? 5L * 1024 * 1024 : maxBytesCuerpo;
    }

    // Nunca imprimir las claves (por ejemplo, si alguien registra este objeto)
    @Override
    public String toString() {
        return "SeguridadProperties[clientes=" + apiKeys.keySet() + ", maxBytesCuerpo=" + maxBytesCuerpo + "]";
    }
}
