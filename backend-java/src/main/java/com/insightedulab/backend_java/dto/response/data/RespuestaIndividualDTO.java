package com.insightedulab.backend_java.dto.response.data;

import lombok.Data;

@Data
public class RespuestaIndividualDTO {

    private String mensajeId;
    private String channelId;
    private String textoRespuesta;
    private boolean requiereHumano;
    private String intencion;
}
