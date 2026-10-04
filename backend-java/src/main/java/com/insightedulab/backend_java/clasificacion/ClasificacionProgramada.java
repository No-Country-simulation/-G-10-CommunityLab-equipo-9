package com.insightedulab.backend_java.clasificacion;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;

/**
 * La tarea programada: cada {@code clasificacion.intervalo-ms} procesa una tanda de PENDIENTE.
 * fixedDelay espera a que termine la tanda anterior, así que dentro de un mismo Java nunca se superponen;
 * entre dos Java distintos los protege SKIP LOCKED.
 * Se apaga con clasificacion.habilitada=false (las pruebas lo hacen).
 */
@Configuration
@EnableScheduling
@ConditionalOnProperty(prefix = "clasificacion", name = "habilitada", havingValue = "true", matchIfMissing = true)
public class ClasificacionProgramada {

    private static final Logger log = LoggerFactory.getLogger(ClasificacionProgramada.class);

    private final ClasificacionService servicio;
    private long sinServidorAvisados = -1;

    public ClasificacionProgramada(ClasificacionService servicio) {
        this.servicio = servicio;
    }

    @Scheduled(fixedDelayString = "${clasificacion.intervalo-ms:30000}",
               initialDelayString = "${clasificacion.retraso-inicial-ms:20000}")
    public void clasificar() {
        try {
            ClasificacionService.Resumen r = servicio.procesarTanda();
            if (r.tomados() > 0) {
                log.info("Clasificación: tomados {}, OK {}, ERROR {}, reintento {}, cambiaron {} · {} ms",
                        r.tomados(), r.ok(), r.error(), r.reintento(), r.cambiaron(), r.duracionMs());
            }
            avisarSinServidor();
        } catch (RuntimeException e) {
            // Las reservas vencen solas: la próxima ejecución los vuelve a tomar
            log.error("Clasificación: la tanda falló", e);
        }
    }

    /** Avisa solo cuando cambia la cantidad, para no repetir lo mismo cada 30 s. */
    private void avisarSinServidor() {
        long sinServidor = servicio.contarSinServidor();
        if (sinServidor != sinServidorAvisados) {
            if (sinServidor > 0) {
                log.warn("Clasificación: {} mensajes PENDIENTE no tienen servidor_id (llegaron antes de V2). "
                        + "Se clasifican cuando el lote de la hora los reenvíe", sinServidor);
            }
            sinServidorAvisados = sinServidor;
        }
    }
}
