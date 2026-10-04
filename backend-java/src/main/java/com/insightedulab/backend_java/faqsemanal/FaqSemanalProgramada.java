package com.insightedulab.backend_java.faqsemanal;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.TaskScheduler;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;

import java.time.Instant;
import java.util.function.Supplier;

/**
 * Las tareas programadas de la FAQ semanal (T06b, DEC-99):
 * <ul>
 *   <li>una vez por semana, en el horario de faq.cron (por defecto, el lunes a las 8:00 en faq.zona);</li>
 *   <li>cada faq.reintento-ms, reintenta una semana que falló (con la misma ventana de dudas);</li>
 *   <li>si faq.al-arrancar=true, una vez al encender Java, después de faq.retraso-arranque-ms (para la demo).</li>
 * </ul>
 * Nunca hay dos FAQ de la misma semana: lo garantiza la tabla faq_semanas (V5).
 * Se apaga con faq.habilitada=false (las pruebas lo hacen). Lleva su propio @EnableScheduling.
 */
@Configuration
@EnableScheduling
@ConditionalOnProperty(prefix = "faq", name = "habilitada", havingValue = "true", matchIfMissing = true)
public class FaqSemanalProgramada {

    private static final Logger log = LoggerFactory.getLogger(FaqSemanalProgramada.class);

    private final FaqSemanalService servicio;
    private final FaqSemanalProperties propiedades;
    private final TaskScheduler planificador;

    public FaqSemanalProgramada(FaqSemanalService servicio, FaqSemanalProperties propiedades,
                                TaskScheduler planificador) {
        this.servicio = servicio;
        this.propiedades = propiedades;
        this.planificador = planificador;
    }

    @Scheduled(cron = "${faq.cron:0 0 8 * * MON}", zone = "${faq.zona:America/Bogota}")
    public void semanal() {
        correr("semanal", () -> servicio.ejecutar(Instant.now()));
    }

    @Scheduled(fixedDelayString = "${faq.reintento-ms:1800000}", initialDelayString = "${faq.reintento-ms:1800000}")
    public void reintentar() {
        correr("reintento", servicio::reintentar);
    }

    /** FAQ_SEMANAL_AL_ARRANCAR: corre una sola vez, en otro hilo, para no frenar el arranque. */
    @EventListener(ApplicationReadyEvent.class)
    public void alArrancar() {
        if (propiedades.alArrancar()) {
            log.info("FAQ semanal: se arma una vez al encender, en {} s", propiedades.retrasoArranqueMs() / 1000);
            planificador.schedule(() -> correr("al encender", () -> servicio.ejecutar(Instant.now())),
                    Instant.now().plusMillis(propiedades.retrasoArranqueMs()));
        }
    }

    private void correr(String disparador, Supplier<FaqSemanalService.Resultado> tarea) {
        try {
            FaqSemanalService.Resultado r = tarea.get();
            if (r != null) {
                // Solo números: nunca textos de alumnos ni el borrador (S11)
                log.info("FAQ semanal ({}) {}: {} · dudas {}, repetidas {}, con respuesta {} · {} ms", disparador,
                        r.semana(), r.estado(), r.dudas(), r.repetidas(), r.conRespuesta(), r.duracionMs());
            }
        } catch (RuntimeException e) {
            // La reserva vence sola: el reintento la vuelve a tomar
            log.error("FAQ semanal ({}): falló", disparador, e);
        }
    }
}
