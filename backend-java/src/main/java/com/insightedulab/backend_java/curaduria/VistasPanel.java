package com.insightedulab.backend_java.curaduria;

import java.time.Instant;
import java.util.List;

/**
 * Lo que entra y sale por las puertas del panel (contrato Panel ↔ Java v1, docs/contratos/PANEL_JAVA_v1.md).
 * Los nombres de campo van en camelCase, como en los otros contratos.
 */
public final class VistasPanel {

    private VistasPanel() {
    }

    // ── Respuestas ──

    /** Un renglón de la lista de borradores: lo justo para elegir cuál abrir. */
    public record ResumenBorrador(long id, String tipo, String estado, Instant creadoEn, String extracto,
                                  String autorNombre, String canal, String semana,
                                  String revisadoPor, Instant revisadoEn) {}

    public record ListaBorradores(List<ResumenBorrador> borradores) {}

    /** El mensaje de Discord que le dio origen (posts y casos de éxito). La FAQ no tiene: junta muchas dudas. */
    public record Origen(String discordId, String canal, Instant fecha, String texto, String autorNombre) {}

    /** La semana de la FAQ (T06b) y lo que dijo la IA al armarla. */
    public record SemanaFaq(String semana, Instant desde, Instant hasta, String motivo) {}

    /**
     * Si el borrador ya está en OCI (T09): el estado de cada subida, PENDIENTE, SUBIDO o ERROR, o null si todavía
     * no se encoló. Solo el estado: nunca la ruta del objeto ni la URL PAR. {@code aprobados} es null en lo que
     * no está aprobado: a esa carpeta solo va lo aprobado (F11).
     */
    public record EstadoOci(String generados, String aprobados) {}

    public record DetalleBorrador(long id, String tipo, String estado, boolean requiereConsentimiento,
                                  String textoIa, String textoFinal, boolean consentimientoConfirmado,
                                  Instant creadoEn, String aprobadoPor, Instant aprobadoEn,
                                  Integer tiempoCuraduriaSeg, String rechazadoPor, Instant rechazadoEn,
                                  String motivoRechazo, String motivoIa, Origen origen, SemanaFaq faq,
                                  EstadoOci oci) {}

    /** Un mensaje que quedó en ERROR, en la clasificación (T04) o en la generación (T06). */
    public record MensajeEnError(long mensajeId, String discordId, String canal, Instant fecha, String autorNombre,
                                 String extracto, int intentos, String motivo) {}

    public record ListaErrores(List<MensajeEnError> clasificacion, List<MensajeEnError> generacion) {}

    public record Reintento(long mensajeId, String etapa, String estado) {}

    // ── Pedidos ──

    public record PedidoEditar(String textoFinal) {}

    /** textoFinal es opcional: si viene, se guarda la edición y se aprueba en el mismo paso. */
    public record PedidoAprobar(Boolean consentimiento, Integer tiempoCuraduriaSeg, String textoFinal) {}

    public record PedidoRechazar(String motivo, Integer tiempoCuraduriaSeg) {}
}
