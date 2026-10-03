package com.insightedulab.backend_java.model.enums;

/** Si la IA ya etiquetó el mensaje. Vuelve a PENDIENTE cuando el texto cambia y hay que reclasificar. */
public enum EstadoClasificacion {
    PENDIENTE,
    OK,
    ERROR
}
