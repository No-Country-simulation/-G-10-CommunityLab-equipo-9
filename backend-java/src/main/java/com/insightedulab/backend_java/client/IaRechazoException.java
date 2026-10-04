package com.insightedulab.backend_java.client;

import com.insightedulab.backend_java.error.ErrorApi;

import java.util.List;

/**
 * La IA respondió 422: el lote que armó Java no cumple el contrato. Es un error de nuestro lado,
 * no pasajero: reintentarlo igual daría lo mismo.
 */
public class IaRechazoException extends RuntimeException {

    private final transient List<ErrorApi.ErrorCampo> errores;

    public IaRechazoException(List<ErrorApi.ErrorCampo> errores) {
        super("La IA rechazó el lote (422) con " + errores.size() + " errores de contrato");
        this.errores = List.copyOf(errores);
    }

    public List<ErrorApi.ErrorCampo> getErrores() {
        return errores;
    }
}
