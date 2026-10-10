package com.insightedulab.backend_java.oci;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.net.URI;
import java.time.DateTimeException;
import java.time.ZoneId;

/**
 * Propiedades "oci.*" de application.properties (T09).
 *
 * @param habilitada            si la tarea programada corre (las pruebas la apagan: ver el pom.xml)
 * @param intervaloMs           espera entre el fin de una tanda y el inicio de la siguiente
 * @param tanda                 cuántas subidas se hacen por vez (una tras otra: cada una puede tardar hasta 35 s)
 * @param maxIntentos           al llegar aquí, un fallo es definitivo (estado = ERROR)
 * @param reservaSegundos       cuánto dura la reserva; tiene que superar la tanda entera en el peor caso
 * @param esperaReintentoSegundos tras un fallo, la subida espera esto multiplicado por los intentos que lleva
 * @param zona                  la zona horaria de la fecha que lleva el nombre del objeto
 * @param par                   la URL PAR del bucket (una credencial: nunca se escribe en un registro)
 */
@ConfigurationProperties(prefix = "oci")
public record OciProperties(Boolean habilitada, Long intervaloMs, Integer tanda, Integer maxIntentos,
                            Integer reservaSegundos, Integer esperaReintentoSegundos, String zona, Par par) {

    /** Cómo está la PAR: lo único que se puede decir de ella en el registro. */
    public enum EstadoPar {
        /** No hay PAR: es una elección (por ejemplo, en desarrollo), no un error de cada borrador */
        SIN_PAR,
        /** Hay algo, pero no es una PAR de bucket de OCI (no empieza con https://objectstorage. o no termina en /o/) */
        FORMA_INVALIDA,
        LISTA
    }

    /** La URL PAR. Su toString la oculta: un registro o una excepción que la imprima no la filtra. */
    public record Par(String url) {
        @Override
        public String toString() {
            return "Par[oculta]";
        }
    }

    public OciProperties {
        habilitada = habilitada == null || habilitada;
        intervaloMs = intervaloMs == null ? 30_000L : intervaloMs;
        tanda = tanda == null ? 10 : tanda;
        maxIntentos = maxIntentos == null ? 5 : maxIntentos;
        reservaSegundos = reservaSegundos == null ? 420 : reservaSegundos;
        esperaReintentoSegundos = esperaReintentoSegundos == null ? 60 : esperaReintentoSegundos;
        zona = zona == null || zona.isBlank() ? "America/Bogota" : zona.strip();
        try {
            ZoneId.of(zona);  // que un error de escritura falle al arrancar y no en la primera subida
        } catch (DateTimeException e) {
            throw new IllegalArgumentException("oci.zona no es una zona horaria válida: " + zona, e);
        }
        par = par == null ? new Par("") : par;
    }

    /** La PAR sin espacios, o "" si no hay. Solo para el cliente de OCI. */
    String parUrl() {
        return par.url() == null ? "" : par.url().strip();
    }

    /** 📘 Una PAR de bucket es https://objectstorage.<región>.oraclecloud.com/p/<secreto>/n/<espacio>/b/<bucket>/o/ */
    public EstadoPar estadoPar() {
        String url = parUrl();
        if (url.isEmpty()) {
            return EstadoPar.SIN_PAR;
        }
        if (!url.startsWith("https://objectstorage.") || !url.endsWith("/o/")) {
            return EstadoPar.FORMA_INVALIDA;
        }
        try {
            URI.create(url);  // sin mostrar el mensaje de la excepción: lleva la URL
        } catch (IllegalArgumentException e) {
            return EstadoPar.FORMA_INVALIDA;
        }
        return EstadoPar.LISTA;
    }

    public ZoneId zonaHoraria() {
        return ZoneId.of(zona);
    }
}
