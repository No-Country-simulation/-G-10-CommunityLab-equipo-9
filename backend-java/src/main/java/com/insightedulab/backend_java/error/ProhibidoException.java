package com.insightedulab.backend_java.error;

/** La clave es válida, pero de un cliente que no puede usar esta puerta (DEC-70): 403. */
public class ProhibidoException extends RuntimeException {

    public ProhibidoException() {
        super("Esta clave no puede usar esta ruta.");
    }
}
