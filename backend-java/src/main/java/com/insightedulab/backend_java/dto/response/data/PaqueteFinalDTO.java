package com.insightedulab.backend_java.dto.response.data;

import lombok.Data;

import java.util.List;

@Data
public class PaqueteFinalDTO {
    private String loteId;
    private String logId;
    private String tipoServidor;
    private String tipoAutorRespuesta;
    private String clasificacionSentimiento;
    private String respuestaAi;
    private String postLinkedin;
    private String temaFaq;
    private String preguntaFaq;
    private String respuestaFaq;
    private Integer tokensIn;
    private Integer tokensOut;
    private Double similitudPromedio;
    private Boolean fueEditadoPorHumano;
    private ResumenLoteDTO resumenLote;
    private List<Object> activosGenerados;
    private List<String> requierenHumano; // Cambiado a List<String> para que matchee con List.of()
}