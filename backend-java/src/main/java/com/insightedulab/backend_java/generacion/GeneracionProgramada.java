package com.insightedulab.backend_java.generacion;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;

/**
 * La tarea programada de T06 (DEC-80): cada {@code generacion.intervalo-ms} pide a la IA los borradores
 * de una tanda de logros. fixedDelay espera a que termine la tanda anterior; entre dos Java, SKIP LOCKED.
 * Se apaga con generacion.habilitada=false (las pruebas lo hacen).
 * Lleva su propio @EnableScheduling: corre aunque la clasificación esté apagada.
 */
@Configuration
@EnableScheduling
@ConditionalOnProperty(prefix = "generacion", name = "habilitada", havingValue = "true", matchIfMissing = true)
public class GeneracionProgramada {

    private static final Logger log = LoggerFactory.getLogger(GeneracionProgramada.class);

    private final GeneracionService servicio;

    public GeneracionProgramada(GeneracionService servicio) {
        this.servicio = servicio;
    }

    @Scheduled(fixedDelayString = "${generacion.intervalo-ms:60000}",
               initialDelayString = "${generacion.retraso-inicial-ms:45000}")
    public void generar() {
        try {
            GeneracionService.Resumen r = servicio.procesarTanda();
            if (r.tomados() > 0) {
                // Solo números: nunca textos de alumnos ni borradores (S11)
                log.info("Generación: tomados {}, generados {}, no publicables {}, ERROR {}, reintento {}, cambiaron {} · {} ms",
                        r.tomados(), r.generados(), r.noPublicables(), r.error(), r.reintento(), r.cambiaron(),
                        r.duracionMs());
            }
        } catch (RuntimeException e) {
            // Las reservas vencen solas: la próxima ejecución los vuelve a tomar
            log.error("Generación: la tanda falló", e);
        }
    }
}
