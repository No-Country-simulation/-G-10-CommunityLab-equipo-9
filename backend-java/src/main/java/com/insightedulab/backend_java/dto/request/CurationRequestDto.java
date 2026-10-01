package com.insightedulab.backend_java.dto.request;

import com.insightedulab.backend_java.model.enums.TipoAutor;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CurationRequestDto {

    @NotBlank(message = "El post de LinkedIn es obligatorio")
    private String postLinkedin;

    @NotBlank(message = "El tema de la FAQ es obligatorio")
    private String temaFaq;

    @NotBlank(message = "La pregunta de la FAQ es obligatoria")
    private String preguntaFaq;

    @NotBlank(message = "La respuesta de la FAQ es obligatoria")
    private String respuestaFaq;

    @NotNull(message = "El tipo de autor de la respuesta es obligatorio")
    private TipoAutor tipoAutorRespuesta;

    private Boolean fueEditadoPorHumano;

    private Integer tiempoCuraduriaSeg;
}