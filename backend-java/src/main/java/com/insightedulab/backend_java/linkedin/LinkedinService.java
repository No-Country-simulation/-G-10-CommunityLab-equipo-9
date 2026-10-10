package com.insightedulab.backend_java.linkedin;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * Servicio encargado de gestionar la publicación de posts en LinkedIn.
 * Admite modo real (con credenciales de la API) y modo simulado (para desarrollo local).
 */
@Service
public class LinkedinService {

    private static final Logger log = LoggerFactory.getLogger(LinkedinService.class);

    private final LinkedinClient cliente;
    private final LinkedinProperties propiedades;

    public LinkedinService(LinkedinClient cliente, LinkedinProperties propiedades) {
        this.cliente = cliente;
        this.propiedades = propiedades;
    }

    /**
     * Publica un borrador aprobado en LinkedIn.
     *
     * @param borradorId ID del borrador aprobado
     * @param texto      Texto final validado para el post
     * @return Resultado de la publicación (real o simulada)
     */
    public LinkedinPostResponse publicarBorrador(long borradorId, String texto) {
        if (!propiedades.habilitada()) {
            log.info("Publicación en LinkedIn deshabilitada por configuración (borrador {})", borradorId);
            return new LinkedinPostResponse(false, false, null, "Integración de LinkedIn deshabilitada");
        }

        if (texto == null || texto.isBlank()) {
            log.warn("El borrador {} no contiene texto para publicar en LinkedIn", borradorId);
            return new LinkedinPostResponse(false, false, null, "Texto de post vacío");
        }

        // 1. Modo real: credenciales configuradas
        if (propiedades.estaConfigurado()) {
            try {
                LinkedinPostRequest request = LinkedinPostRequest.paraTexto(propiedades.authorUrn(), texto);
                log.info("Enviando post a LinkedIn API para author {} (borrador {})", propiedades.authorUrn(), borradorId);
                String idPost = cliente.publicar(request);
                log.info("✅ Post publicado en LinkedIn exitosamente. ID: {}", idPost);
                return new LinkedinPostResponse(true, false, idPost, "Publicado exitosamente en LinkedIn");
            } catch (Exception e) {
                log.error("❌ Error al publicar post de borrador {} en LinkedIn: {}", borradorId, e.getMessage());
                return new LinkedinPostResponse(false, false, null, "Fallo al comunicar con LinkedIn: " + e.getMessage());
            }
        }

        // 2. Modo simulado: sin credenciales en .env (entorno local)
        String idSimulado = "urn:li:share:simulado-" + borradorId;
        log.info("📢 [LinkedIn SIMULADO] Borrador {} aprobado. Post listo para publicar:", borradorId);
        log.info("   Autor: {}", (propiedades.authorUrn() != null && !propiedades.authorUrn().isBlank()) ? propiedades.authorUrn() : "urn:li:person:simulado");
        log.info("   Texto ({} caracteres): {}", texto.length(), texto.replace("\n", " "));
        log.info("   (Para publicar en vivo, completa LINKEDIN_ACCESS_TOKEN y LINKEDIN_AUTHOR_URN en tu .env)");

        return new LinkedinPostResponse(true, true, idSimulado, "Publicación simulada exitosamente (faltan credenciales en .env)");
    }
}
