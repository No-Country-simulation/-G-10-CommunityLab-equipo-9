package com.insightedulab.backend_java.linkedin;

/**
 * Resultado de una operación de publicación en LinkedIn.
 *
 * @param publicado true si se publicó o se simuló exitosamente
 * @param simulado true si se ejecutó en modo simulado (sin credenciales reales)
 * @param idPost URN o identificador del post retornado por LinkedIn (o generado en simulación)
 * @param mensaje detalle de la respuesta o motivo de simulación
 */
public record LinkedinPostResponse(
        boolean publicado,
        boolean simulado,
        String idPost,
        String mensaje
) {}
