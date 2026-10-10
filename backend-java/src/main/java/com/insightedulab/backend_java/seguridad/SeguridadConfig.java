package com.insightedulab.backend_java.seguridad;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(SeguridadProperties.class)
public class SeguridadConfig {
}
