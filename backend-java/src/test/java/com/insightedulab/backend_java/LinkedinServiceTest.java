package com.insightedulab.backend_java;

import com.insightedulab.backend_java.linkedin.*;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

class LinkedinServiceTest {

    @Test
    void siEstaDeshabilitadaNoPublica() {
        LinkedinProperties props = new LinkedinProperties(false, "token", "urn:li:person:123", null);
        LinkedinClient client = Mockito.mock(LinkedinClient.class);
        LinkedinService service = new LinkedinService(client, props);

        LinkedinPostResponse resp = service.publicarBorrador(1L, "Texto del post");

        assertThat(resp.publicado()).isFalse();
        assertThat(resp.mensaje()).contains("deshabilitada");
        Mockito.verifyNoInteractions(client);
    }

    @Test
    void siNoTieneCredencialesPublicaEnModoSimuladoSinFallar() {
        // Token vacío o nulo = modo simulado
        LinkedinProperties props = new LinkedinProperties(true, "", "", null);
        LinkedinClient client = Mockito.mock(LinkedinClient.class);
        LinkedinService service = new LinkedinService(client, props);

        LinkedinPostResponse resp = service.publicarBorrador(42L, "¡Felicidades a Camila por su nuevo trabajo!");

        assertThat(resp.publicado()).isTrue();
        assertThat(resp.simulado()).isTrue();
        assertThat(resp.idPost()).isEqualTo("urn:li:share:simulado-42");
        assertThat(resp.mensaje()).contains("simulada");
        Mockito.verifyNoInteractions(client);
    }

    @Test
    void siTieneCredencialesLlamaAlClienteReal() {
        LinkedinProperties props = new LinkedinProperties(true, "token_valido", "urn:li:person:harrison", null);
        LinkedinClient client = Mockito.mock(LinkedinClient.class);
        when(client.publicar(any())).thenReturn("urn:li:share:987654321");

        LinkedinService service = new LinkedinService(client, props);

        LinkedinPostResponse resp = service.publicarBorrador(15L, "Post listo para LinkedIn");

        assertThat(resp.publicado()).isTrue();
        assertThat(resp.simulado()).isFalse();
        assertThat(resp.idPost()).isEqualTo("urn:li:share:987654321");
    }

    @Test
    void siClienteRealFallaNoRevientaLaAprobacion() {
        LinkedinProperties props = new LinkedinProperties(true, "token_invalido", "urn:li:person:harrison", null);
        LinkedinClient client = Mockito.mock(LinkedinClient.class);
        when(client.publicar(any())).thenThrow(new RuntimeException("401 Unauthorized de LinkedIn"));

        LinkedinService service = new LinkedinService(client, props);

        LinkedinPostResponse resp = service.publicarBorrador(15L, "Post con error");

        assertThat(resp.publicado()).isFalse();
        assertThat(resp.simulado()).isFalse();
        assertThat(resp.mensaje()).contains("401 Unauthorized");
    }

    @Test
    void payloadEstructuraJsonOficialDeLinkedin() {
        LinkedinPostRequest req = LinkedinPostRequest.paraTexto("urn:li:organization:communitylab", "Texto de prueba");

        assertThat(req.author()).isEqualTo("urn:li:organization:communitylab");
        assertThat(req.commentary()).isEqualTo("Texto de prueba");
        assertThat(req.visibility()).isEqualTo("PUBLIC");
        assertThat(req.lifecycleState()).isEqualTo("PUBLISHED");
        assertThat(req.distribution().feedDistribution()).isEqualTo("MAIN_FEED");
    }
}
