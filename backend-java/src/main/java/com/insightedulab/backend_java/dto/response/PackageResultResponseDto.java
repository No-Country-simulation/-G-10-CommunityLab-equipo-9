package com.insightedulab.backend_java.dto.response;


import com.insightedulab.backend_java.model.enums.ClasificacionSentimiento;
import com.insightedulab.backend_java.model.enums.TipoAutor;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PackageResultResponseDto {
    private Long id;
    private String logId;
    private String loteId;
    private String tipoServidor;
    private List<InteractionResponseDto> interacciones; // Un DTO plano para las interacciones
    private TipoAutor tipoAutorRespuesta;
    private ClasificacionSentimiento clasificacionSentimiento;
    private String respuestaAi;
    private String postLinkedin;
    private String temaFaq;
    private String preguntaFaq;
    private String respuestaFaq;
    private Integer tokensIn;
    private Integer tokensOut;
    private Double similitudPromedio;
    private Boolean fueEditadoPorHumano;
    private Integer tiempoCuraduriaSeg;
    private Instant timestampInicio;
    private Instant timestampFin;
    private String statusOci;
}