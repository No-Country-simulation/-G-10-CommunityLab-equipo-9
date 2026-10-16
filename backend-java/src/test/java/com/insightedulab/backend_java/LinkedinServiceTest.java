package com.insightedulab.backend_java;

import com.insightedulab.backend_java.linkedin.*;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.web.client.ResourceAccessException;

import java.net.SocketTimeoutException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

/**
 * LinkedinService sin red: el cliente HTTP es un Mockito. T13 (DEC-160): el resultado es un estado que se guarda en
 * el borrador, con motivos fijos (nunca el mensaje de una excepción), y el servicio dice en qué modo está.
 */
class LinkedinServiceTest {

    private static final LinkedinProperties APAGADA = new LinkedinProperties(false, "token", "urn:li:person:123", null);
    private static final LinkedinProperties SIN_TOKEN = new LinkedinProperties(true, "", "", null);
    private static final LinkedinProperties CON_TOKEN =
            new LinkedinProperties(true, "token_valido", "urn:li:person:harrison", null);

    @Test
    void siEstaDeshabilitadaNoPublica() {
        LinkedinClient client = Mockito.mock(LinkedinClient.class);
        LinkedinService service = new LinkedinService(client, APAGADA);

        LinkedinPostResponse resp = service.publicarBorrador(1L, "Texto del post");

        assertThat(resp).isEqualTo(new LinkedinPostResponse("APAGADO", null, null));
        Mockito.verifyNoInteractions(client);
    }

    @Test
    void siNoTieneCredencialesQuedaSimuladoSinLlamarALinkedin() {
        // Token vacío o nulo = modo simulado
        LinkedinClient client = Mockito.mock(LinkedinClient.class);
        LinkedinService service = new LinkedinService(client, SIN_TOKEN);

        LinkedinPostResponse resp = service.publicarBorrador(42L, "¡Felicidades a Camila por su nuevo trabajo!");

        assertThat(resp).isEqualTo(new LinkedinPostResponse("SIMULADO", null, null));
        Mockito.verifyNoInteractions(client);
    }

    @Test
    void siTieneCredencialesLlamaAlClienteReal() {
        LinkedinClient client = Mockito.mock(LinkedinClient.class);
        when(client.publicar(any())).thenReturn("urn:li:share:987654321");

        LinkedinPostResponse resp = new LinkedinService(client, CON_TOKEN).publicarBorrador(15L, "Post listo para LinkedIn");

        assertThat(resp).isEqualTo(new LinkedinPostResponse("PUBLICADO", "urn:li:share:987654321", null));
    }

    @Test
    void unIdentificadorDemasiadoLargoNoSeGuarda() {
        LinkedinClient client = Mockito.mock(LinkedinClient.class);
        when(client.publicar(any())).thenReturn("urn:li:share:" + "9".repeat(300));

        LinkedinPostResponse resp = new LinkedinService(client, CON_TOKEN).publicarBorrador(15L, "Post");

        assertThat(resp).isEqualTo(new LinkedinPostResponse("PUBLICADO", null, null));
    }

    @Test
    void siElClienteFallaElMotivoEsFijoYNoLlevaElMensajeDeLaExcepcion() {
        LinkedinClient client = Mockito.mock(LinkedinClient.class);
        when(client.publicar(any())).thenThrow(new RuntimeException("401 Unauthorized de LinkedIn token=abc"));

        LinkedinPostResponse resp = new LinkedinService(client, CON_TOKEN).publicarBorrador(15L, "Post con error");

        assertThat(resp).isEqualTo(new LinkedinPostResponse("ERROR", null, "Falló la publicación en LinkedIn"));
        assertThat(resp.motivo()).doesNotContain("401").doesNotContain("Unauthorized").doesNotContain("token");
    }

    @Test
    void unaRespuestaDeErrorDeLinkedinDiceSoloElCodigo() {
        LinkedinClient client = Mockito.mock(LinkedinClient.class);
        when(client.publicar(any())).thenThrow(new LinkedinHttpException(401));

        LinkedinPostResponse resp = new LinkedinService(client, CON_TOKEN).publicarBorrador(15L, "Post");

        assertThat(resp).isEqualTo(LinkedinPostResponse.error("LinkedIn respondió HTTP 401"));
    }

    @Test
    void siLinkedinNoRespondeATiempoLoDice() {
        LinkedinClient client = Mockito.mock(LinkedinClient.class);
        when(client.publicar(any())).thenThrow(new ResourceAccessException("I/O error en https://api.linkedin.com…",
                new SocketTimeoutException("Read timed out")));

        LinkedinPostResponse resp = new LinkedinService(client, CON_TOKEN).publicarBorrador(15L, "Post");

        assertThat(resp).isEqualTo(LinkedinPostResponse.error("LinkedIn no respondió a tiempo"));
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

    @Test
    void enModoSimuladoUnTextoDeMasDe3000CaracteresOVacioEsError() {
        LinkedinClient client = Mockito.mock(LinkedinClient.class);
        LinkedinService service = new LinkedinService(client, SIN_TOKEN);

        assertThat(service.publicarBorrador(99L, "A".repeat(3001)))
                .isEqualTo(LinkedinPostResponse.error("Pasa de 3.000 caracteres"));
        assertThat(service.publicarBorrador(99L, "   ")).isEqualTo(LinkedinPostResponse.error("Texto vacío"));
        assertThat(service.publicarBorrador(99L, "A".repeat(3000)).estado()).isEqualTo("SIMULADO");
        Mockito.verifyNoInteractions(client);
    }

    @Test
    void unEmojiCuentaDosCaracteresComoEnElPanel() {
        // String.length() cuenta en UTF-16: 🎉 son 2. El contador del panel cuenta igual (T13)
        LinkedinService service = new LinkedinService(Mockito.mock(LinkedinClient.class), SIN_TOKEN);

        assertThat(service.publicarBorrador(1L, "🎉".repeat(1500)).estado()).isEqualTo("SIMULADO");
        assertThat(service.publicarBorrador(1L, "🎉".repeat(1500) + "a").motivo()).isEqualTo("Pasa de 3.000 caracteres");
    }

    @Test
    void elModoSaleDeLaConfiguracionSinLlamarALinkedin() {
        LinkedinClient client = Mockito.mock(LinkedinClient.class);

        assertThat(new LinkedinService(client, APAGADA).modo()).isEqualTo("APAGADO");
        assertThat(new LinkedinService(client, SIN_TOKEN).modo()).isEqualTo("SIMULADO");
        assertThat(new LinkedinService(client, new LinkedinProperties(true, "token", "", null)).modo())
                .isEqualTo("SIMULADO");  // con token pero sin autor
        assertThat(new LinkedinService(client, CON_TOKEN).modo()).isEqualTo("REAL");
        Mockito.verifyNoInteractions(client);
    }
}
