package com.insightedulab.backend_java.faqsemanal;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/** Las propiedades existen aunque las tareas programadas estén apagadas: el servicio las necesita igual. */
@Configuration
@EnableConfigurationProperties(FaqSemanalProperties.class)
public class FaqSemanalConfig {
}
