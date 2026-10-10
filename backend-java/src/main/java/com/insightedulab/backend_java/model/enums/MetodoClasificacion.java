package com.insightedulab.backend_java.model.enums;

/**
 * Quién decidió las etiquetas, con los nombres exactos del contrato Java ↔ IA v1 (campo "metodo").
 * Van en camelCase a propósito, como AutorTipo: así se guardan en la base y así los lee Jackson.
 */
public enum MetodoClasificacion {
    llm,           // el modelo de lenguaje
    palabrasClave, // respaldo sin LLM, solo si se eligió por configuración
    regla          // no pasó por el LLM: bot, aviso del sistema o mensaje sin texto
}
