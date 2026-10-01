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

    @NotBlank(message = "El tipo de servidor es obligatorio")
    private String tipoServidor;

    @NotEmpty(message = "La lista de interacciones no puede estar vacía")
    @Valid // Asegura que también se validen los campos internos de cada InteractionInputDto
    private List<InteractionInputDto> interacciones;
}
