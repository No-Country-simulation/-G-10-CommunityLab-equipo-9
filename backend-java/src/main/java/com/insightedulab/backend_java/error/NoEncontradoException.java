package com.insightedulab.backend_java.error;

/** Lo pedido no existe: 404 (F13). Para las puertas del panel y de borradores que vienen después. */
public class NoEncontradoException extends RuntimeException {

    public NoEncontradoException(String mensaje) {
        super(mensaje);
    }
}
