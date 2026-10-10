package com.insightedulab.backend_java.error;

/**
 * Un dato del pedido no se puede aceptar: 422 (T07), con el campo que falla.
 * Por ejemplo, aprobar un post sin el consentimiento (D6) o un usuario vacío.
 */
public class DatoInvalidoException extends RuntimeException {

    private final String campo;

    public DatoInvalidoException(String campo, String problema) {
        super(problema);
        this.campo = campo;
    }

    public String getCampo() {
        return campo;
    }
}
