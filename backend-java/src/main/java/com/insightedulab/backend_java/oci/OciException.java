package com.insightedulab.backend_java.oci;

/**
 * No se pudo subir un archivo a OCI. Su mensaje es seguro para el registro y para la base:
 * solo dice el código HTTP o la clase del error, nunca la URL PAR (que es una credencial).
 */
public class OciException extends RuntimeException {

    public OciException(String mensaje) {
        super(mensaje);
    }
}
