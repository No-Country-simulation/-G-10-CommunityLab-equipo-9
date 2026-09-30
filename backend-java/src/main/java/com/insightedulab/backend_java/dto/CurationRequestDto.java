package com.insightedulab.backend_java.dto;

import com.insightedulab.backend_java.model.enums.TipoAutor;
import lombok.Data;

@Data
public class CurationRequestDto {
    private String postLinkedin;
    private String temaFaq;
    private String preguntaFaq;
    private String respuestaFaq;
    private TipoAutor tipoAutorRespuesta;
    private Boolean fueEditadoPorHumano;
    private Integer tiempoCuraduriaSeg;
}