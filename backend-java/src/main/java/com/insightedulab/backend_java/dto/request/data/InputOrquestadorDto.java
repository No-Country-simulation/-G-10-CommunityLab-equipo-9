package com.insightedulab.backend_java.dto.request.data;

import lombok.Data;


@Data
public class InputOrquestadorDto {

    private String mensajeId;
    private String autorId;
    private String autorUsername;
    private String channelId;
    private String contenido;
    private String timestamp;
    private boolean esBot;
}