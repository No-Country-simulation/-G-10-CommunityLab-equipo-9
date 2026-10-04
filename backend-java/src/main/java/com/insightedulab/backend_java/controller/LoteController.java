package com.insightedulab.backend_java.controller;

import com.insightedulab.backend_java.dto.lote.LoteEntrada;
import com.insightedulab.backend_java.dto.lote.ReciboLote;
import com.insightedulab.backend_java.seguridad.ApiKeyFilter;
import com.insightedulab.backend_java.seguridad.ClientePermitido;
import com.insightedulab.backend_java.service.LoteService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Puerta de lotes: la ingesta (send_batch.py) envía aquí el contrato v1 tal cual (D8).
 * Exige X-Api-Key (ApiKeyFilter) y solo la puede usar el cliente "ingesta" (DEC-70). Responde 200 con el recibo, también si el lote ya se había recibido.
 */
@RestController
@RequestMapping("/api/v1/lotes")
public class LoteController {

    private final LoteService loteService;

    public LoteController(LoteService loteService) {
        this.loteService = loteService;
    }

    @PostMapping
    public ReciboLote recibir(@RequestAttribute(name = ApiKeyFilter.ATRIBUTO_CLIENTE, required = false) String cliente,
                              @RequestBody LoteEntrada lote) {
        ClientePermitido.exigir(ClientePermitido.INGESTA, cliente);  // segunda capa, además del filtro
        return loteService.recibir(lote);
    }
}
