package com.insightedulab.backend_java;

import com.insightedulab.backend_java.clasificacion.ClasificacionProgramada;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import static org.assertj.core.api.Assertions.assertThat;

// La tarea programada queda creada pero no llega a correr: así se comprueba que arranca bien
@SpringBootTest(properties = {"clasificacion.retraso-inicial-ms=3600000", "generacion.retraso-inicial-ms=3600000"})
class BackendJavaApplicationTests {

	@Autowired
	ClasificacionProgramada tareaProgramada;

	@Test
	void contextLoads() {
		assertThat(tareaProgramada).isNotNull();
	}

}
