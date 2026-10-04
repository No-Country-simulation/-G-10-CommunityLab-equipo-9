package com.insightedulab.backend_java.envivo;

/**
 * Lo que Java le contesta al bot (contrato Bot ↔ Java v1, docs/contratos/BOT_JAVA_v1.md).
 * Java decide (DEC-68); el bot solo cumple la orden.
 *
 * @param texto    lo que el bot publica, ya armado (RESPONDER y DERIVAR); null en las demás órdenes
 * @param reaccion el emoji que pone el bot (REACCIONAR); null en las demás órdenes
 */
public record OrdenBot(String versionContratoBot, String discordId, Orden orden, String texto, String reaccion) {

    public static final String VERSION = "1.0";

    public enum Orden {
        RESPONDER,   // duda con respaldo en los PDFs: publica el texto
        DERIVAR,     // duda sin respaldo firme (o tope agotado): avisa que responderá un mentor
        REACCIONAR,  // logro: solo una reacción, sin texto (F5)
        NADA         // comentario, otro, mensaje ya procesado o falla de Java o de la IA (DEC-67)
    }

    static OrdenBot nada(String discordId) {
        return new OrdenBot(VERSION, discordId, Orden.NADA, null, null);
    }
}
