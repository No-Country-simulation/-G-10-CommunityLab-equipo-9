package com.insightedulab.backend_java.service;

import com.insightedulab.backend_java.dto.request.data.InputOrquestadorDto;
import com.insightedulab.backend_java.dto.response.data.OutputOrquestadorDTO;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;



@Service
public class OrquestadorService {

    private final RestTemplate restTemplate = new RestTemplate();

    // URL del endpoint expuesto por tu FastAPI en Python - de prueba
    // Se inicializa desde el application.properties, permitiendo modificarla sin tocar código
    @Value("${fastapi.url}")
    private String fastapiUrl;

    public OutputOrquestadorDTO enviarLoteAlOrquestador(InputOrquestadorDto payload) {
        try {
            // Configurar cabeceras HTTP asegurando el formato JSON
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            HttpEntity<InputOrquestadorDto> requestEntity = new HttpEntity<>(payload, headers);

            // Realizar la petición POST hacia FastAPI
            ResponseEntity<OutputOrquestadorDTO> response = restTemplate.postForEntity(
                    fastapiUrl,
                    requestEntity,
                    OutputOrquestadorDTO.class
            );

            return response.getBody();

        } catch (Exception e) {
            // Manejo básico de error de conexión con el motor de IA
            throw new RuntimeException("Error al comunicarse con el motor de IA en FastAPI: " + e.getMessage(), e);
        }
    }
}