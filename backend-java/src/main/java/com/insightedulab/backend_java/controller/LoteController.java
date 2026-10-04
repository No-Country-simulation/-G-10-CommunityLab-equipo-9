package com.insightedulab.backend_java.controller;

import com.insightedulab.backend_java.dto.lote.LoteEntrada;
import com.insightedulab.backend_java.dto.lote.ReciboLote;
import com.insightedulab.backend_java.service.LoteService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Puerta de lotes: la ingesta (send_batch.py) envía aquí el contrato v1 tal cual (D8).
 * Exige X-Api-Key (ApiKeyFilter). Responde 200 con el recibo, también si el lote ya se había recibido.
 */
@RestController
@RequestMapping("/api/v1/lotes")
public class LoteController {

    private final LoteService loteService;

    public LoteController(LoteService loteService) {
        this.loteService = loteService;
    }

    @PostMapping
    public ReciboLote recibir(@RequestBody LoteEntrada lote) {
        return loteService.recibir(lote);
    }
}
