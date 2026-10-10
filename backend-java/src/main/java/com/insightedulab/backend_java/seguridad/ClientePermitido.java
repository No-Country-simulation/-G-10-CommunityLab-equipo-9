package com.insightedulab.backend_java.seguridad;

import com.insightedulab.backend_java.error.ProhibidoException;

/**
 * Segunda capa de DEC-70 (auditoría de T05): cada controlador exige su cliente, aunque ApiKeyFilter ya lo
 * haya revisado. Si una forma rara de escribir la ruta llegara a pasar el filtro, el controlador igual responde 403.
 * El cliente lo deja ApiKeyFilter en el atributo {@link ApiKeyFilter#ATRIBUTO_CLIENTE} del pedido.
 */
public final class ClientePermitido {

    public static final String INGESTA = "ingesta";
    public static final String BOT = "bot";
    public static final String PANEL = "panel";

    private ClientePermitido() {
    }

    /** @throws ProhibidoException si el cliente del pedido no es el esperado (o no hay cliente) */
    public static void exigir(String esperado, String cliente) {
        if (!esperado.equals(cliente)) {
            throw new ProhibidoException();
        }
    }
}
