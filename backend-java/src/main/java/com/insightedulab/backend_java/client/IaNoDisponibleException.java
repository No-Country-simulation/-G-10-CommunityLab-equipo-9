package com.insightedulab.backend_java.client;

/**
 * La IA no pudo atender: 500, otro error HTTP, tiempo agotado o conexión rechazada.
 * Se trata como un fallo pasajero: los mensajes siguen PENDIENTE y se reintentan.
 */
public class IaNoDisponibleException extends RuntimeException {

    public IaNoDisponibleException(String mensaje) {
        super(mensaje);
    }

    public IaNoDisponibleException(String mensaje, Throwable causa) {
        super(mensaje, causa);
    }
}
