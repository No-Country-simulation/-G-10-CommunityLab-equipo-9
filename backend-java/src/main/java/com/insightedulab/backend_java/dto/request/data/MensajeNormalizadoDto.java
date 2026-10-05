package com.insightedulab.backend_java.dto.request.data;

import lombok.Data;

@Data
public class MensajeNormalizadoDto {
    private String discordId;
    private String textoMensaje;
    private String mensajeId;          // Mapea con discordId
    private String autorId;            // Mapea con authorId
    private String autorUsername;      // Mapea con authorUsername
    private String autorNombre;        // <--- Añadido para persistir en la entidad
    private String autorRol;           // <--- Añadido para persistir en la entidad
    private String channelId;          // Canal de origen
    private String contenido;          // Mapea con textoMensaje
    private String timestamp;          // Marca de tiempo
    private boolean esBot;
}
