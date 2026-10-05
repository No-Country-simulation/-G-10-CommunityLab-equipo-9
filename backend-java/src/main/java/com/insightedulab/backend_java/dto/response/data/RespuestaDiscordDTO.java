package com.insightedulab.backend_java.dto.response.data;

import lombok.Data;

import java.util.List;

@Data
public class RespuestaDiscordDTO {
    private String loteId;
    private List<RespuestaIndividualDTO> respuestas;
}
