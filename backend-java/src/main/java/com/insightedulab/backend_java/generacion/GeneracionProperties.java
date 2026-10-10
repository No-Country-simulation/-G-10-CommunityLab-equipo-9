package com.insightedulab.backend_java.generacion;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Propiedades "generacion.*" de application.properties (T06).
 *
 * @param habilitada      si la tarea programada corre (las pruebas la apagan)
 * @param intervaloMs     espera entre el fin de una tanda y el inicio de la siguiente
 * @param tanda           cuántos logros se envían por vez (uno tras otro: cada uno es una llamada al LLM)
 * @param maxIntentos     al llegar aquí, un fallo es definitivo (generacion_estado = ERROR)
 * @param reservaSegundos cuánto dura la reserva; tiene que superar los 30 s de espera a la IA por cada logro de la tanda
 * @param maxRespuestas   cuántas respuestas del logro viajan en el pedido (la IA acepta hasta 20)
 */
@ConfigurationProperties(prefix = "generacion")
public record GeneracionProperties(Boolean habilitada, Long intervaloMs, Integer tanda, Integer maxIntentos,
                                   Integer reservaSegundos, Integer maxRespuestas) {

    public GeneracionProperties {
        habilitada = habilitada == null || habilitada;
        intervaloMs = intervaloMs == null ? 60_000L : intervaloMs;
        tanda = tanda == null ? 3 : tanda;
        maxIntentos = maxIntentos == null ? 3 : maxIntentos;
        reservaSegundos = reservaSegundos == null ? 180 : reservaSegundos;
        maxRespuestas = maxRespuestas == null ? 20 : Math.min(maxRespuestas, 20);
    }
}
