package com.insightedulab.backend_java.dashboard;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

/**
 * Lo que devuelven las puertas del dashboard (T08, PANEL_JAVA_v1.md §7). Todo es de solo lectura.
 * Las fechas de período (desde, hasta, inicio) son días en la zona del dashboard (dashboard.zona).
 */
public final class VistasDashboard {

    private VistasDashboard() {
    }

    /** El período pedido, ya validado: desde y hasta incluidos. */
    public record Periodo(LocalDate desde, LocalDate hasta) {}

    public record Totales(Periodo periodo, long mensajes, long personasActivas, long dudas, long logros,
                          long sinClasificar, long borradoresPendientes) {}

    /** Un día o una semana (inicio = el lunes) con la cantidad de cada sentimiento, también los ceros. */
    public record PuntoSentimiento(LocalDate inicio, Map<String, Long> cantidades) {}

    public record Sentimiento(Periodo periodo, String agrupar, boolean excluirOtro, List<PuntoSentimiento> puntos) {}

    /** variacion = actual − anterior: positiva si el tema subió. */
    public record TemaTendencia(String tema, long actual, long anterior, long variacion) {}

    public record Temas(Periodo periodo, Periodo periodoAnterior, boolean excluirOtro, List<TemaTendencia> temas) {}

    public record PersonaDesercion(String nombre, Instant ultimoMensaje, long diasSinEscribir, long mensajes) {}

    public record Desercion(int dias, List<PersonaDesercion> personas) {}

    /**
     * motivo: MUY_NEGATIVO (uno en el período) o DOS_DE_TRES (2 negativos entre sus últimos 3 mensajes), DEC-121.
     * Sin textos: el CM ve quién, no qué escribió.
     */
    public record PersonaFrustracion(String nombre, List<String> motivos, long negativosEnPeriodo,
                                     long negativosEnUltimos3, Instant ultimoNegativo) {}

    public record Frustracion(Periodo periodo, List<PersonaFrustracion> personas) {}

    /** derivada: el bot avisó que respondería un mentor, y nadie contestó todavía. */
    public record DudaSinResponder(long mensajeId, String discordId, Instant fecha, String tema, boolean derivada,
                                   String canal, String autorNombre, String texto) {}

    /** total puede ser mayor que dudas.size(): la lista tiene un tope. */
    public record DudasSinResponder(Periodo periodo, int horas, boolean excluirOtro, long total,
                                    List<DudaSinResponder> dudas) {}
}
