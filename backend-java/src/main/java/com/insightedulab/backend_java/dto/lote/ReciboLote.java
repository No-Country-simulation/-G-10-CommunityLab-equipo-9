package com.insightedulab.backend_java.dto.lote;

import com.insightedulab.backend_java.model.LoteRecibido;

import java.time.Instant;

/**
 * Lo que responde POST /api/v1/lotes. Con yaRecibido = true es el mismo recibo que se dio
 * la primera vez: reenviar un lote es seguro.
 */
public record ReciboLote(
        String loteId,
        int total,
        int nuevos,
        int actualizados,
        int sinCambios,
        Instant recibidoEn,
        boolean yaRecibido
) {
    public static ReciboLote de(LoteRecibido lote, boolean yaRecibido) {
        return new ReciboLote(
                lote.getLoteId(),
                lote.getTotal(),
                lote.getNuevos(),
                lote.getActualizados(),
                lote.getTotal() - lote.getNuevos() - lote.getActualizados(),
                lote.getRecibidoEn(),
                yaRecibido);
    }
}
