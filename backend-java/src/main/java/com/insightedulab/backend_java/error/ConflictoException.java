package com.insightedulab.backend_java.error;

/**
 * El pedido es correcto, pero el estado ya no lo permite: 409 (T07). Por ejemplo, aprobar un borrador que
 * otra persona aprobó o rechazó un momento antes, o reintentar un mensaje que ya no está en ERROR.
 */
public class ConflictoException extends RuntimeException {

    public ConflictoException(String mensaje) {
        super(mensaje);
    }
}
