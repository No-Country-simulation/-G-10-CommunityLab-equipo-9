package com.insightedulab.backend_java.linkedin;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.ResourceAccessException;

import java.net.SocketTimeoutException;

/**
 * Servicio encargado de gestionar la publicación de posts en LinkedIn.
 * Admite modo real (con credenciales de la API) y modo simulado (para desarrollo local).
 *
 * <p>T13 (DEC-160): el resultado es un estado que Java guarda en el borrador (V9). Los motivos de un ERROR son
 * textos fijos armados aquí: nunca el mensaje de una excepción ni el cuerpo de la respuesta de LinkedIn.</p>
 */
@Service
public class LinkedinService {

    private static final Logger log = LoggerFactory.getLogger(LinkedinService.class);

    public static final int MAX_CARACTERES_LINKEDIN = 3000;
    /** El largo máximo de linkedin_post_id en la V9: un identificador más largo no es un URN de LinkedIn */
    static final int MAX_ID_POST = 200;

    /** Qué pasa al aprobar un post (decisión 2b de T13). El panel lo muestra antes de aprobar */
    public static final String MODO_APAGADO = "APAGADO";
    public static final String MODO_SIMULADO = "SIMULADO";
    public static final String MODO_REAL = "REAL";

    private final LinkedinClient cliente;
    private final LinkedinProperties propiedades;

    public LinkedinService(LinkedinClient cliente, LinkedinProperties propiedades) {
        this.cliente = cliente;
        this.propiedades = propiedades;
    }

    /**
     * APAGADO (LINKEDIN_HABILITADA=false), REAL (encendido con token y autor) o SIMULADO (encendido sin token o
     * sin autor). La misma regla que usa {@link #publicarBorrador}. Solo el modo: nunca el token ni el autor.
     */
    public String modo() {
        if (!propiedades.habilitada()) {
            return MODO_APAGADO;
        }
        return propiedades.estaConfigurado() ? MODO_REAL : MODO_SIMULADO;
    }

    /**
     * Publica un borrador aprobado en LinkedIn.
     *
     * @param borradorId ID del borrador aprobado
     * @param texto      Texto final validado para el post
     * @return El estado para guardar: PUBLICADO, SIMULADO, APAGADO o ERROR (con un motivo fijo)
     */
    public LinkedinPostResponse publicarBorrador(long borradorId, String texto) {
        if (!propiedades.habilitada()) {
            log.info("Publicación en LinkedIn deshabilitada por configuración (borrador {})", borradorId);
            return new LinkedinPostResponse(LinkedinPostResponse.APAGADO, null, null);
        }

        if (texto == null || texto.isBlank()) {
            log.warn("El borrador {} no contiene texto para publicar en LinkedIn", borradorId);
            return LinkedinPostResponse.error("Texto vacío");
        }

        if (texto.length() > MAX_CARACTERES_LINKEDIN) {
            log.warn("El borrador {} excede el límite de {} caracteres de LinkedIn ({}): no se publica",
                    borradorId, MAX_CARACTERES_LINKEDIN, texto.length());
            return LinkedinPostResponse.error("Pasa de 3.000 caracteres");
        }

        // 1. Modo real: credenciales configuradas
        if (propiedades.estaConfigurado()) {
            try {
                LinkedinPostRequest request = LinkedinPostRequest.paraTexto(propiedades.authorUrn(), texto);
                log.info("Enviando post a LinkedIn API para author {} (borrador {})", propiedades.authorUrn(), borradorId);
                String idPost = cliente.publicar(request);
                log.info("✅ Post publicado en LinkedIn exitosamente. ID: {}", idPost);
                return new LinkedinPostResponse(LinkedinPostResponse.PUBLICADO, idValido(idPost), null);
            } catch (LinkedinHttpException e) {
                return fallo(borradorId, "LinkedIn respondió HTTP " + e.estado());
            } catch (ResourceAccessException e) {
                return fallo(borradorId, e.getCause() instanceof SocketTimeoutException
                        ? "LinkedIn no respondió a tiempo" : "No se pudo conectar con LinkedIn");
            } catch (RuntimeException e) {
                // Solo la clase: el mensaje podría traer datos de la respuesta
                log.error("❌ Error al publicar post de borrador {} en LinkedIn ({})", borradorId,
                        e.getClass().getSimpleName());
                return LinkedinPostResponse.error("Falló la publicación en LinkedIn");
            }
        }

        // 2. Modo simulado: sin credenciales en .env (entorno local)
        log.info("📢 [LinkedIn SIMULADO] Borrador {} aprobado. Post listo para publicar:", borradorId);
        log.info("   Autor: {}", (propiedades.authorUrn() != null && !propiedades.authorUrn().isBlank()) ? propiedades.authorUrn() : "urn:li:person:simulado");
        // Solo el largo: los registros nunca llevan textos de alumnos (AGENTS.md §4)
        log.info("   Texto: {} caracteres", texto.length());
        log.info("   (Para publicar en vivo, completa LINKEDIN_ACCESS_TOKEN y LINKEDIN_AUTHOR_URN en tu .env)");

        return new LinkedinPostResponse(LinkedinPostResponse.SIMULADO, null, null);
    }

    private static LinkedinPostResponse fallo(long borradorId, String motivo) {
        log.error("❌ Error al publicar post de borrador {} en LinkedIn: {}", borradorId, motivo);
        return LinkedinPostResponse.error(motivo);
    }

    /** El URN tal cual, o null si falta o es demasiado largo para ser uno (no cabría en la V9). */
    private static String idValido(String idPost) {
        return idPost == null || idPost.isBlank() || idPost.length() > MAX_ID_POST ? null : idPost;
    }
}
