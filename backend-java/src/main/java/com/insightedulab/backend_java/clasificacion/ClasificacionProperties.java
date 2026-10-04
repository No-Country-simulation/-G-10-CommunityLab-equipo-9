package com.insightedulab.backend_java.clasificacion;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Propiedades "clasificacion.*" de application.properties.
 *
 * @param habilitada     si la tarea programada corre (las pruebas la apagan)
 * @param intervaloMs    espera entre el fin de una tanda y el inicio de la siguiente
 * @param tanda          cuántos mensajes PENDIENTE se envían a la IA por vez (T02: uno tras otro, 1 a 3 s cada uno)
 * @param maxIntentos    al llegar aquí, un ERROR de la IA en un mensaje es definitivo
 * @param reservaSegundos cuánto dura la reserva de una tanda; tiene que superar los 30 s de espera a la IA
 */
@ConfigurationProperties(prefix = "clasificacion")
public record ClasificacionProperties(
        Boolean habilitada, Long intervaloMs, Integer tanda, Integer maxIntentos, Integer reservaSegundos) {

    public ClasificacionProperties {
        habilitada = habilitada == null || habilitada;
        intervaloMs = intervaloMs == null ? 30_000L : intervaloMs;
        tanda = tanda == null ? 5 : tanda;
        maxIntentos = maxIntentos == null ? 3 : maxIntentos;
        reservaSegundos = reservaSegundos == null ? 120 : reservaSegundos;
    }
}
