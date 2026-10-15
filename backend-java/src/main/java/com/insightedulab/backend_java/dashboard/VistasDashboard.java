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

    /**
     * derivada: el bot avisó que respondería un mentor, y nadie contestó todavía.
     * servidorId y canalId (T12): para armar el enlace https://discord.com/channels/servidor/canal/discordId.
     */
    public record DudaSinResponder(long mensajeId, String discordId, Instant fecha, String tema, boolean derivada,
                                   String canal, String autorNombre, String texto, String servidorId,
                                   String canalId) {}

    /** total puede ser mayor que dudas.size(): la lista tiene un tope. */
    public record DudasSinResponder(Periodo periodo, int horas, boolean excluirOtro, long total,
                                    List<DudaSinResponder> dudas) {}

    // ── Vista Comunidad (T12) ──

    /**
     * total: los alumnos que escribieron alguna vez hasta el fin del período; activos: en los últimos 7 y 30 días;
     * dudas: sus PREGUNTA_FAQ (OK) del período.
     */
    public record Alumnos(long total, long activos7Dias, long activos30Dias, long dudas) {}

    /**
     * Las dudas de personas del período: respondidas y derivadas por el bot, y las que llegaron por lote sin pasar
     * por él. segundosMediana: del mensaje a la decisión del bot (respondida o derivada); null si no hubo ninguna.
     */
    public record Bot(long respondidas, long derivadas, long sinPasarPorElBot, Double segundosMediana) {}

    public record TemaCantidad(String tema, long cantidad) {}

    /** derivadasPorTema: lo que el bot no encontró en los PDF, es decir, lo que falta en los documentos. */
    public record Comunidad(Periodo periodo, Alumnos alumnos, Bot bot, List<TemaCantidad> derivadasPorTema) {}

    // ── Vista Contenido (T12) ──

    /** Los pendientes de hoy (no dependen del período), por tipo, y la fecha del más antiguo (null si no hay). */
    public record PorRevisar(long total, Map<String, Long> porTipo, Instant masAntiguo) {}

    /** La mediana de tiempo_curaduria_seg de lo revisado en el período, con su n; null si n = 0. */
    public record Revision(String tipo, Double medianaSeg, long n) {}

    public record Aprobacion(long aprobados, long rechazados) {}

    /**
     * Los logros (TESTIMONIO, OK, de personas) del período y qué pasó con ellos: publicables según la IA
     * (GENERADO), no publicables, y cuántos tienen su post aprobado.
     */
    public record Embudo(long logros, long publicables, long noPublicables, long conPostAprobado) {}

    /** Una semana (inicio = el lunes) con cuántos borradores se aprobaron, también los ceros. */
    public record SemanaCantidad(LocalDate inicio, long cantidad) {}

    /** La mediana de horas del mensaje del logro a la aprobación de su post, con su n; null si n = 0. */
    public record LogroAAprobacion(Double medianaHoras, long n) {}

    public record Contenido(Periodo periodo, PorRevisar porRevisar, List<Revision> revision, Aprobacion aprobacion,
                            Embudo embudo, List<SemanaCantidad> aprobadosPorSemana, LogroAAprobacion logroAAprobacion,
                            long mensajesDePersonas, long activosOci) {}
}
