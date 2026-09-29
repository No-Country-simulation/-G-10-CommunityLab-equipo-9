package com.insightedulab.backend_java.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CommunityProcessResponseDto {
    private String status;
    private String mensaje;
    private String loteId;
    private Integer totalMensajesRecibidos;
    private Instant recibidoEn;
}
