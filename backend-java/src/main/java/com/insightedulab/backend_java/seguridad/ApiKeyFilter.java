package com.insightedulab.backend_java.seguridad;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.util.UrlPathHelper;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * S1: todo pedido necesita la cabecera X-Api-Key con la clave de un cliente conocido,
 * salvo /actuator/health (lo usa el healthcheck de Docker).
 *
 * <ul>
 *   <li>Por defecto se exige en todas las rutas: una puerta nueva queda protegida sin acordarse de nada.</li>
 *   <li>Se comparan huellas SHA-256 con MessageDigest.isEqual, que tarda lo mismo acierte o no:
 *       así no se puede adivinar la clave midiendo tiempos.</li>
 *   <li>La clave nunca se escribe en el registro; solo el nombre del cliente.</li>
 *   <li>DEC-70: cada clave abre solo su puerta. Una ruta de {@link #CLIENTE_POR_RUTA} con la clave de otro
 *       cliente recibe 403, antes de leer el cuerpo. Si se filtra una clave, el daño queda en su puerta.
 *       La ruta se compara normalizada, y cada controlador vuelve a revisar el cliente (dos capas).</li>
 * </ul>
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 10)
public class ApiKeyFilter extends OncePerRequestFilter {

    public static final String CABECERA = "X-Api-Key";
    public static final String ATRIBUTO_CLIENTE = "clienteApi";
    private static final Logger log = LoggerFactory.getLogger(ApiKeyFilter.class);

    /** Las rutas que solo puede usar un cliente. Las demás las puede usar cualquier cliente conocido. */
    static final Map<String, String> CLIENTE_POR_RUTA = Map.of(
            "/api/v1/lotes", ClientePermitido.INGESTA,
            "/api/v1/mensajes/en-vivo", ClientePermitido.BOT);

    private final Map<String, byte[]> huellasPorCliente = new LinkedHashMap<>();
    private final RespuestaError respuestaError;

    public ApiKeyFilter(SeguridadProperties propiedades, RespuestaError respuestaError) {
        this.respuestaError = respuestaError;
        propiedades.apiKeys().forEach((cliente, clave) -> {
            if (clave != null && !clave.isBlank()) {
                huellasPorCliente.put(cliente, huella(clave.strip()));
            }
        });
        if (huellasPorCliente.isEmpty()) {
            log.warn("No hay ninguna API key configurada (API_KEY_INGESTA, API_KEY_BOT): se rechaza todo salvo /actuator/health.");
        } else {
            log.info("API keys configuradas para: {}", huellasPorCliente.keySet());
        }
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String ruta = request.getRequestURI().substring(request.getContextPath().length());
        return ruta.equals("/actuator/health") || ruta.startsWith("/actuator/health/");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String cliente = clienteDe(request.getHeader(CABECERA));
        if (cliente == null) {
            log.warn("Pedido rechazado sin API key válida: {} {}", request.getMethod(), request.getRequestURI());
            respuestaError.escribir(request, response, HttpServletResponse.SC_UNAUTHORIZED,
                    "NO_AUTORIZADO", "Falta la cabecera X-Api-Key o la clave no es válida.");
            return;
        }
        String ruta = rutaNormalizada(request);
        String duenio = CLIENTE_POR_RUTA.get(ruta);
        if (duenio != null && !duenio.equals(cliente)) {
            log.warn("Pedido rechazado: el cliente {} no puede usar {} {}", cliente, request.getMethod(), ruta);
            respuestaError.escribir(request, response, HttpServletResponse.SC_FORBIDDEN,
                    "PROHIBIDO", "Esta clave no puede usar esta ruta.");
            return;
        }
        request.setAttribute(ATRIBUTO_CLIENTE, cliente);
        chain.doFilter(request, response);
    }

    /**
     * La ruta como la resuelve Spring para elegir el controlador, no la cruda (auditoría de T05):
     * sin lo que va después de ";", decodificada (%73 → s) y sin barras dobles. Con la ruta cruda,
     * "/api/v1/lotes;x=1" o "/api/v1/lote%73" no coincidían con el mapa y llegaban al controlador.
     * La segunda capa de defensa es que cada controlador exige además su cliente ({@link ClientePermitido}).
     */
    static String rutaNormalizada(HttpServletRequest request) {
        return UrlPathHelper.defaultInstance.getPathWithinApplication(request);
    }

    /** El cliente dueño de la clave, o null. Recorre todas las claves para tardar siempre lo mismo. */
    private String clienteDe(String clave) {
        if (clave == null || clave.isBlank()) {
            return null;
        }
        byte[] recibida = huella(clave.strip());
        String encontrado = null;
        for (Map.Entry<String, byte[]> e : huellasPorCliente.entrySet()) {
            if (MessageDigest.isEqual(recibida, e.getValue())) {
                encontrado = e.getKey();
            }
        }
        return encontrado;
    }

    private static byte[] huella(String clave) {
        try {
            return MessageDigest.getInstance("SHA-256").digest(clave.getBytes(StandardCharsets.UTF_8));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("La JVM no tiene SHA-256", e);
        }
    }
}
