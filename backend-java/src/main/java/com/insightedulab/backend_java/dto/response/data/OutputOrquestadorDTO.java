package com.insightedulab.backend_java.dto.response.data;

import lombok.Data;

@Data
public class OutputOrquestadorDTO {
    private String loteId;
    private RespuestaDiscordDTO respuestaDiscord;
    private PaqueteFinalDTO paqueteFinal;
    private LogEjecucionDTO logEjecucion;
}