package com.insightedulab.backend_java.controller;

import com.insightedulab.backend_java.dto.request.CommunityProcessRequestDto;
import com.insightedulab.backend_java.dto.request.InteractionInputDto;
import com.insightedulab.backend_java.dto.response.data.OutputOrquestadorDTO;
import com.insightedulab.backend_java.model.enums.ClasificacionSentimiento;
import com.insightedulab.backend_java.model.enums.TipoAutor;
import com.insightedulab.backend_java.service.OrquestadorPersistenceService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.List;


@RestController
@RequestMapping("/api/v1/orquestador")
public class OrquestadorTestController {

    private final OrquestadorPersistenceService persistenceService;

    public OrquestadorTestController(OrquestadorPersistenceService persistenceService) {
        this.persistenceService = persistenceService;
    }

    @PostMapping("/ejecutar")
    public ResponseEntity<OutputOrquestadorDTO> probarProcesamiento() {
        // 1. Creamos un mensaje con todos los campos requeridos por Python completos
        InteractionInputDto mensajePrueba = InteractionInputDto.builder()
                .discordId("123456789")
                .channelId("channel-discord-99")
                .authorId("user-123")
                .authorUsername("christian_dev")
                .autorNombre("Christian")
                .autorRol("Developer")
                .textoMensaje("Hola, esto es una prueba del orquestador") // <- Este es el nombre real en tu DTO
                .tipoAutor(TipoAutor.AI) // Ajusta según tu enum existente
                .clasificacionSentimiento(ClasificacionSentimiento.NEUTRO) // Opcional según tu lógica
                .timestampMensaje(Instant.now()) // Es un Instant, no un String
                .build();

        // 2. Armamos el lote completo
        CommunityProcessRequestDto inputDto = CommunityProcessRequestDto.builder()
                .loteId("lote-test-001")
                .origen("Discord")
                .servidor("Discord_ONE_G10")
                .mensajes(List.of(mensajePrueba)) // Usando la lista de interacciones ya armada con mensajePrueba
                .build();

        // 3. Ejecutamos el flujo que llama a FastAPI y guarda en PostgreSQL
        OutputOrquestadorDTO resultado = persistenceService.procesarYGuardarLote(inputDto);

        return ResponseEntity.ok(resultado);
    }
}