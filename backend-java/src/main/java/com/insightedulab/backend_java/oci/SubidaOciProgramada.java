package com.insightedulab.backend_java.oci;

import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;

/**
 * La tarea programada de T09 (DEC-127): cada {@code oci.intervalo-ms} sube a OCI los borradores que faltan.
 * fixedDelay espera a que termine la tanda anterior; entre dos Java, SKIP LOCKED.
 * Se apaga con oci.habilitada=false (el pom.xml lo hace en todas las pruebas, para que ninguna suba nada al
 * bucket real aunque el .env tenga una PAR).
 * Lleva su propio @EnableScheduling: corre aunque las otras tareas estén apagadas.
 */
@Configuration
@EnableScheduling
@ConditionalOnProperty(prefix = "oci", name = "habilitada", havingValue = "true", matchIfMissing = true)
public class SubidaOciProgramada {

    private static final Logger log = LoggerFactory.getLogger(SubidaOciProgramada.class);

    private final SubidaOciService servicio;

    public SubidaOciProgramada(SubidaOciService servicio) {
        this.servicio = servicio;
    }

    /** Al arrancar: valida la PAR (sin mostrarla) y deja el aviso en el registro, una sola vez. */
    @PostConstruct
    void validarAlArrancar() {
        if (servicio.listo()) {
            log.info("OCI: hay una PAR con la forma esperada; la subida de borradores está activa");
        }
    }

    @Scheduled(fixedDelayString = "${oci.intervalo-ms:30000}",
               initialDelayString = "${oci.retraso-inicial-ms:30000}")
    public void subir() {
        try {
            SubidaOciService.Resumen r = servicio.procesarTanda();
            if (r.tomadas() > 0) {
                // Solo números: nunca la PAR ni textos (S11)
                log.info("Subida a OCI: tomadas {}, subidas {}, reintento {}, ERROR {} · {} ms",
                        r.tomadas(), r.subidas(), r.reintento(), r.error(), r.duracionMs());
            }
        } catch (RuntimeException e) {
            // Las reservas vencen solas: la próxima ejecución las vuelve a tomar. Aquí solo llegan errores de la base:
            // el servicio ya atrapó todo lo que viene de OCI (cuyos mensajes sí podrían llevar la PAR)
            log.error("Subida a OCI: la tanda falló", e);
        }
    }
}
