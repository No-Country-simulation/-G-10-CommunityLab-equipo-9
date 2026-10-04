package com.insightedulab.backend_java.clasificacion;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/** Las propiedades existen aunque la tarea programada esté apagada: el servicio las necesita igual. */
@Configuration
@EnableConfigurationProperties(ClasificacionProperties.class)
public class ClasificacionConfig {
}
