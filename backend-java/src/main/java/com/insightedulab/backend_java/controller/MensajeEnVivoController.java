package com.insightedulab.backend_java.controller;

import com.insightedulab.backend_java.dto.lote.LoteEntrada;
import com.insightedulab.backend_java.envivo.EnVivoService;
import com.insightedulab.backend_java.envivo.OrdenBot;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Puerta en vivo: el bot envía aquí cada mensaje de #dudas y #logros, como un lote del contrato v1
 * con modo tiempoReal y un solo mensaje. Responde 200 con la orden para el bot
 * (contrato Bot ↔ Java v1, docs/contratos/BOT_JAVA_v1.md).
 * Solo la puede usar el cliente "bot" (ApiKeyFilter, DEC-70).
 */
@RestController
@RequestMapping("/api/v1/mensajes/en-vivo")
public class MensajeEnVivoController {

    private final EnVivoService enVivoService;

    public MensajeEnVivoController(EnVivoService enVivoService) {
        this.enVivoService = enVivoService;
    }

    @PostMapping
    public OrdenBot recibir(@RequestBody LoteEntrada lote) {
        return enVivoService.procesar(lote);
    }
}
