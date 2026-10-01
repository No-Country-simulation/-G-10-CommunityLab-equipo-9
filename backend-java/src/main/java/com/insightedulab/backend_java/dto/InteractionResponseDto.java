package com.insightedulab.backend_java.dto;

import com.insightedulab.backend_java.model.enums.ClasificacionSentimiento;
import com.insightedulab.backend_java.model.enums.TipoAutor;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class InteractionResponseDto {
    private Long id;
    private String discordId;
    private String channelId;
    private String authorId;
    private String authorUsername;
    private String autorNombre;
    private String autorRol;
    private String textoMensaje;
    private TipoAutor tipoAutor;
    private ClasificacionSentimiento clasificacionSentimiento;
    private Instant timestampMensaje;
    // Omitimos la referencia a PackageResult para romper el ciclo por completo
}