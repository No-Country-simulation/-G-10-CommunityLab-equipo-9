package com.insightedulab.backend_java.controller;

import com.insightedulab.backend_java.dto.CommunityProcessRequestDto;
import com.insightedulab.backend_java.dto.CommunityProcessResponseDto;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;

@RestController
@RequestMapping("/api/v1/community")
public class CommunityController {

    /**
     * Endpoint oficial para recibir y validar el lote de mensajes de Discord.
     */
    @PostMapping("/process")
    public ResponseEntity<CommunityProcessResponseDto> processBatch(@RequestBody CommunityProcessRequestDto request) {
        // 1. Validación de entrada
        if (request == null || request.getInteracciones() == null || request.getInteracciones().isEmpty()) {
            CommunityProcessResponseDto errorResponse = CommunityProcessResponseDto.builder()
                    .status("error")
                    .mensaje("El lote recibido no contiene interacciones válidas para procesar")
                    .loteId(request != null ? request.getLoteId() : null)
                    .totalMensajesRecibidos(0)
                    .build();
            return ResponseEntity.badRequest().body(errorResponse);
        }

        int total = request.getInteracciones().size();

        // TODO (Módulo 3): Conectar aquí el Service de procesamiento de negocio e IA

        // 2. Respuesta formal tipada para Discord
        CommunityProcessResponseDto response = CommunityProcessResponseDto.builder()
                .status("exitoso")
                .mensaje("Lote recibido y validado correctamente")
                .loteId(request.getLoteId())
                .totalMensajesRecibidos(total)
                .recibidoEn(Instant.now())
                .build();

        return ResponseEntity.ok(response);
    }
}


