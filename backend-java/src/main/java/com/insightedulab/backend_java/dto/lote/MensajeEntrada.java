package com.insightedulab.backend_java.dto.lote;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;

/**
 * Los campos de un mensaje del contrato v1 que van a columnas de la tabla mensajes (CONTRACT.md §3 y §5).
 * El resto del mensaje no se tipa aquí: viaja entero en la caja.
 * Los valores cerrados se validan como texto para devolver un 422 claro, no un error de lectura.
 */
public record MensajeEntrada(
        @NotNull(message = "es obligatorio")
        @Pattern(regexp = ID_DISCORD, message = "debe ser un ID de Discord (solo dígitos)")
        String id,

        @NotNull(message = "es obligatorio") @Valid
        Canal canal,

        @NotNull(message = "es obligatorio") @Valid
        Autor autor,

        @NotNull(message = "es obligatorio")
        @Pattern(regexp = "mensaje|respuesta|avisoSistema|otro", message = "debe ser mensaje, respuesta, avisoSistema u otro")
        String tipo,

        @NotNull(message = "es obligatorio")
        Boolean esSimulado,

        @NotNull(message = "es obligatorio")
        @Pattern(regexp = FECHA_UTC, message = "debe ser una fecha UTC como 2026-09-28T18:56:30.331Z")
        String fecha,

        @Pattern(regexp = ID_DISCORD, message = "debe ser un ID de Discord o null")
        String respondeA,

        @NotNull(message = "es obligatorio (puede ser \"\")")
        String textoOriginal
) {
    public static final String ID_DISCORD = "\\d{1,30}";
    public static final String FECHA_UTC = "\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{3}Z";

    public record Canal(
            @NotNull(message = "es obligatorio")
            @Pattern(regexp = ID_DISCORD, message = "debe ser un ID de Discord (solo dígitos)")
            String id
    ) {}

    public record Autor(
            @NotBlank(message = "es obligatorio")
            String id,

            @NotNull(message = "es obligatorio")
            @Pattern(regexp = "persona|botPropio|otroBot", message = "debe ser persona, botPropio u otroBot")
            String tipo,

            @NotNull(message = "es obligatorio")
            @Pattern(regexp = "miembro|mentor|staff", message = "debe ser miembro, mentor o staff")
            String rol
    ) {}
}
