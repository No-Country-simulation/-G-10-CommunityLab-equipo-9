package com.insightedulab.backend_java.model.enums;

/**
 * Tipo de autor, con los nombres exactos del contrato v1 (CONTRACT.md §5).
 * Van en camelCase a propósito: así se guardan en la base y así los lee Jackson del JSON.
 */
public enum AutorTipo {
    persona,
    botPropio,
    otroBot
}
