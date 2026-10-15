package com.insightedulab.backend_java.linkedin;

/**
 * LinkedIn respondió con un código que no es 2xx. Lleva solo el código: nunca el cuerpo de la respuesta, que
 * podría traer datos que no deben quedar en la base ni en el registro (T13).
 */
public class LinkedinHttpException extends RuntimeException {

    private final int estado;

    public LinkedinHttpException(int estado) {
        super("LinkedIn respondió HTTP " + estado);
        this.estado = estado;
    }

    public int estado() {
        return estado;
    }
}
