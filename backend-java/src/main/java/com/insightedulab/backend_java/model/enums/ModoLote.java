package com.insightedulab.backend_java.model.enums;

/** De dónde viene el lote, con los nombres exactos del contrato v1 (CONTRACT.md §5). */
public enum ModoLote {
    historial,  // ingesta por lotes, cada hora
    tiempoReal  // bot en vivo
}
