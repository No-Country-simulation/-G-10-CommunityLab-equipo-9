package com.insightedulab.backend_java.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CommunityProcessRequestDto {
    private String loteId;
    private String tipoServidor;
    private List<InteractionInputDto> interacciones;
}
