package com.insightedulab.backend_java.dto.request;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CommunityProcessRequestDto {

    @NotBlank(message = "El ID del lote no puede estar vacío")
    private String loteId;

    private String origen; // Agregado para coincidir con Python

    @NotBlank(message = "El servidor es obligatorio")
    private String servidor; // Cambiado de tipoServidor a servidor

    @NotEmpty(message = "La lista de interacciones no can not be empty")
    @Valid
    private List<InteractionInputDto> mensajes; // Cambiado de interacciones a mensajes para que el JSON mande "mensajes"
}
