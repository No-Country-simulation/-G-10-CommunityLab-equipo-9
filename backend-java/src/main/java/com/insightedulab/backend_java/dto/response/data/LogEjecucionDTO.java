package com.insightedulab.backend_java.dto.response.data;

import lombok.Data;

import java.util.List;

@Data
public class LogEjecucionDTO {
    private String loteId;
    private String timestampInicio;
    private String timestampFin;
    private long duracionTotalMs;
    private int tokensTotales;
    private List<Object> sublogs;
    private List<String> errores;
}
