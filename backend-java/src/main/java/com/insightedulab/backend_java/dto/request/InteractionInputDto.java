package com.insightedulab.backend_java.dto.request;

import com.insightedulab.backend_java.model.enums.ClasificacionSentimiento;
import com.insightedulab.backend_java.model.enums.TipoAutor;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class InteractionInputDto {

    @NotBlank(message = "El ID de Discord es obligatorio")
    private String discordId;

    private String channelId;

    @NotBlank(message = "El ID del autor es obligatorio")
    private String authorId;

    private String authorUsername;
    private String autorNombre;
    private String autorRol;

    @NotBlank(message = "El texto del mensaje no puede estar vacío")
    private String textoMensaje;

    @NotNull(message = "El tipo de autor es obligatorio")
    private TipoAutor tipoAutor;

    private ClasificacionSentimiento clasificacionSentimiento;

    private Instant timestampMensaje;
}