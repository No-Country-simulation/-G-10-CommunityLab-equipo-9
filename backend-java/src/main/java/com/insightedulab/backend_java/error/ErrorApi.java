package com.insightedulab.backend_java.error;

import java.util.List;

/**
 * Formato común de error (análisis §2), el mismo que usa la IA (docs/contratos/JAVA_IA_v1.md §7).
 * Nunca repite los datos recibidos ni detalles internos (S7).
 */
public record ErrorApi(String codigo, String mensaje, List<ErrorCampo> errores, String idCorrelacion) {

    public record ErrorCampo(String campo, String problema) {}

    public static ErrorApi de(String codigo, String mensaje, String idCorrelacion) {
        return new ErrorApi(codigo, mensaje, List.of(), idCorrelacion);
    }
}
