package com.insightedulab.backend_java.error;

import java.util.List;

/** El cuerpo es JSON válido pero no cumple el contrato v1: se responde 422 con cada campo que falla. */
public class ContratoInvalidoException extends RuntimeException {

    private final transient List<ErrorApi.ErrorCampo> errores;

    public ContratoInvalidoException(List<ErrorApi.ErrorCampo> errores) {
        super("El lote no cumple el contrato v1 (" + errores.size() + " errores)");
        this.errores = List.copyOf(errores);
    }

    public List<ErrorApi.ErrorCampo> getErrores() {
        return errores;
    }
}
