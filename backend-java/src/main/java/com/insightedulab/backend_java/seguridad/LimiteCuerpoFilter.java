package com.insightedulab.backend_java.seguridad;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Set;

/**
 * Tope del cuerpo de cada pedido (seguridad.max-bytes-cuerpo), antes de leerlo.
 * Se exige Content-Length en POST, PUT y PATCH: sin él no se sabe el tamaño hasta leerlo entero.
 * Los clientes que usamos (httpx en Python, RestClient en Java) lo envían siempre.
 * Corre después de la API key: a un pedido sin clave no se le dice nada de su tamaño.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 20)
public class LimiteCuerpoFilter extends OncePerRequestFilter {

    private static final Set<String> CON_CUERPO = Set.of("POST", "PUT", "PATCH");

    private final long maxBytes;
    private final RespuestaError respuestaError;

    public LimiteCuerpoFilter(SeguridadProperties propiedades, RespuestaError respuestaError) {
        this.maxBytes = propiedades.maxBytesCuerpo();
        this.respuestaError = respuestaError;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        if (CON_CUERPO.contains(request.getMethod())) {
            long largo = request.getContentLengthLong();
            if (largo < 0) {
                respuestaError.escribir(request, response, HttpServletResponse.SC_LENGTH_REQUIRED,
                        "LONGITUD_REQUERIDA", "Falta la cabecera Content-Length.");
                return;
            }
            if (largo > maxBytes) {
                respuestaError.escribir(request, response, HttpServletResponse.SC_REQUEST_ENTITY_TOO_LARGE,
                        "CUERPO_DEMASIADO_GRANDE", "El cuerpo supera el máximo de " + maxBytes + " bytes.");
                return;
            }
        }
        chain.doFilter(request, response);
    }
}
