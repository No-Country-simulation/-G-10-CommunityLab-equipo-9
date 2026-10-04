package com.insightedulab.backend_java.generacion;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/** Las propiedades existen aunque la tarea programada esté apagada: el servicio las necesita igual. */
@Configuration
@EnableConfigurationProperties(GeneracionProperties.class)
public class GeneracionConfig {
}
