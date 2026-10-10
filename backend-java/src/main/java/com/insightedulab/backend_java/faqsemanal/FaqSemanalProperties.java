package com.insightedulab.backend_java.faqsemanal;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.time.ZoneId;

/**
 * Propiedades "faq.*" de application.properties (T06b, DEC-99). El horario está en faq.cron, que lee la tarea.
 *
 * @param habilitada        si corren las tareas programadas (las pruebas las apagan)
 * @param alArrancar        corre una vez al encender Java (para la demo: FAQ_SEMANAL_AL_ARRANCAR)
 * @param retrasoArranqueMs cuánto espera después de encender, para que la IA termine de cargar el Agente FAQ
 * @param zona              zona horaria del horario y de la semana (2026-W40)
 * @param dias              cuántos días hacia atrás se juntan las dudas
 * @param maxIntentos       al llegar aquí, un fallo es definitivo (estado = ERROR)
 * @param reservaSegundos   cuánto dura la reserva; tiene que superar la espera a la IA (faq.tiempo-lectura-s)
 * @param maxDudas          cuántas dudas viajan como máximo (la IA acepta hasta 200)
 */
@ConfigurationProperties(prefix = "faq")
public record FaqSemanalProperties(Boolean habilitada, Boolean alArrancar, Long retrasoArranqueMs, String zona,
                                   Integer dias, Integer maxIntentos, Integer reservaSegundos, Integer maxDudas) {

    public FaqSemanalProperties {
        habilitada = habilitada == null || habilitada;
        alArrancar = alArrancar != null && alArrancar;
        retrasoArranqueMs = retrasoArranqueMs == null ? 90_000L : retrasoArranqueMs;
        zona = zona == null || zona.isBlank() ? "America/Bogota" : zona.strip();
        dias = dias == null || dias < 1 ? 7 : dias;
        maxIntentos = maxIntentos == null ? 3 : maxIntentos;
        reservaSegundos = reservaSegundos == null ? 300 : reservaSegundos;
        maxDudas = maxDudas == null ? 200 : Math.min(maxDudas, 200);
    }

    public ZoneId zonaId() {
        return ZoneId.of(zona);
    }
}
