package com.insightedulab.backend_java.seguridad;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.UUID;
import java.util.regex.Pattern;

/**
 * Primer filtro: le da a cada pedido un id de correlación (el de la cabecera X-Id-Correlacion,
 * o uno nuevo). Va en todos los errores, en la respuesta y en el registro, para seguir un envío
 * de punta a punta.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class IdCorrelacionFilter extends OncePerRequestFilter {

    public static final String CABECERA = "X-Id-Correlacion";
    private static final String ATRIBUTO = IdCorrelacionFilter.class.getName();
    // Solo letras, números y guiones: un valor raro podría falsear líneas del registro
    private static final Pattern VALIDO = Pattern.compile("[A-Za-z0-9._-]{1,100}");

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String recibido = request.getHeader(CABECERA);
        String id = recibido != null && VALIDO.matcher(recibido).matches() ? recibido : UUID.randomUUID().toString();
        request.setAttribute(ATRIBUTO, id);
        response.setHeader(CABECERA, id);
        MDC.put("idCorrelacion", id);
        try {
            chain.doFilter(request, response);
        } finally {
            MDC.remove("idCorrelacion");
        }
    }

    /** El id de este pedido. */
    public static String de(HttpServletRequest request) {
        Object id = request.getAttribute(ATRIBUTO);
        return id != null ? id.toString() : UUID.randomUUID().toString();
    }
}
