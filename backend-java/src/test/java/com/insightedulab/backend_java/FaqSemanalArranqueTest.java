package com.insightedulab.backend_java;

import com.insightedulab.backend_java.faqsemanal.FaqSemanalService;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.after;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.timeout;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

/**
 * FAQ_SEMANAL_AL_ARRANCAR (T06b, DEC-99): con faq.al-arrancar=true, la FAQ corre una sola vez al encender Java.
 * El servicio es un doble: aquí se prueba solo el disparo; lo que hace el servicio lo prueba FaqSemanalTest.
 */
@SpringBootTest(properties = {
        "clasificacion.habilitada=false",
        "generacion.habilitada=false",
        "faq.habilitada=true",
        "faq.al-arrancar=true",
        // Que corra cuando la prueba ya empezó: el doble se reinicia al empezar y perdería una llamada anterior
        "faq.retraso-arranque-ms=2000",
        "faq.cron=-",               // sin el horario semanal
        "faq.reintento-ms=3600000",  // ni el reintento
})
class FaqSemanalArranqueTest {

    @MockitoBean FaqSemanalService servicio;

    @Test
    void conLaOpcionEncendidaCorreUnaSolaVezAlArrancar() {
        verify(servicio, timeout(10000).times(1)).ejecutar(any());
        verify(servicio, after(1000).times(1)).ejecutar(any());  // y no vuelve a correr
        verify(servicio, never()).reintentar();
    }
}
