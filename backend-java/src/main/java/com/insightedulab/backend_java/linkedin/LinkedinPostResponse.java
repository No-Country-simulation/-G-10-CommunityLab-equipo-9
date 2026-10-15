package com.insightedulab.backend_java.linkedin;

/**
 * Resultado de mandar un post aprobado a LinkedIn. Java lo guarda en el borrador (V9, T13, DEC-160).
 *
 * @param estado PUBLICADO, SIMULADO, APAGADO o ERROR
 * @param idPost URN del post que devolvió LinkedIn (urn:li:share:…); solo en PUBLICADO
 * @param motivo en ERROR, un texto corto y fijo armado por Java ("LinkedIn respondió HTTP 401"). Nunca el mensaje
 *               de una excepción ni el cuerpo de la respuesta de LinkedIn: va a la base y al panel
 */
public record LinkedinPostResponse(
        String estado,
        String idPost,
        String motivo
) {
    public static final String PUBLICADO = "PUBLICADO";
    public static final String SIMULADO = "SIMULADO";
    public static final String APAGADO = "APAGADO";
    public static final String ERROR = "ERROR";

    public static LinkedinPostResponse error(String motivo) {
        return new LinkedinPostResponse(ERROR, null, motivo);
    }
}
