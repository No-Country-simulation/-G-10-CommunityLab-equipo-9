package com.insightedulab.backend_java.seguridad;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightedulab.backend_java.error.ErrorApi;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

/** Escribe un ErrorApi desde un filtro, donde todavía no actúa el manejador global de errores. */
@Component
public class RespuestaError {

    private final ObjectMapper objectMapper;

    public RespuestaError(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public void escribir(HttpServletRequest request, HttpServletResponse response, int estado,
                         String codigo, String mensaje) throws IOException {
        response.setStatus(estado);
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        objectMapper.writeValue(response.getOutputStream(),
                ErrorApi.de(codigo, mensaje, IdCorrelacionFilter.de(request)));
    }
}
