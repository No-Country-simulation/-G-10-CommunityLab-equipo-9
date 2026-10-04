package com.insightedulab.backend_java.dto.lote;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import java.util.List;
import java.util.Map;

/**
 * El lote del contrato v1 tal cual (D8), con los nombres en camelCase de
 * ingestion/discord/docs/CONTRACT.md §2.
 *
 * Cada mensaje llega como Map: es "la caja" que se guarda completa en mensajes.contrato.
 * Sus columnas se leen aparte con {@link MensajeEntrada}.
 */
public record LoteEntrada(
        @NotNull(message = "es obligatorio")
        @Pattern(regexp = "1\\.0", message = "debe ser \"1.0\"")
        String versionContrato,

        @NotBlank(message = "es obligatorio")
        @Size(max = 100, message = "admite como máximo 100 caracteres")
        String loteId,

        @NotNull(message = "es obligatorio")
        @Pattern(regexp = "discord", message = "debe ser \"discord\"")
        String fuente,

        @NotNull(message = "es obligatorio")
        @Pattern(regexp = "historial|tiempoReal", message = "debe ser historial o tiempoReal")
        String modo,

        @NotNull(message = "es obligatorio")
        @Pattern(regexp = MensajeEntrada.ID_DISCORD, message = "debe ser un ID de Discord (solo dígitos)")
        String servidorId,

        @NotNull(message = "es obligatorio")
        @Pattern(regexp = MensajeEntrada.FECHA_UTC, message = "debe ser una fecha UTC como 2026-09-28T18:56:30.331Z")
        String generadoEn,

        @NotEmpty(message = "debe traer al menos un mensaje")
        @Size(max = LoteEntrada.MAX_MENSAJES, message = "admite como máximo " + LoteEntrada.MAX_MENSAJES + " mensajes")
        List<Map<String, Object>> mensajes
) {
    public static final int MAX_MENSAJES = 1000;
}
