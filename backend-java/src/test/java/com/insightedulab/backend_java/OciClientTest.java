package com.insightedulab.backend_java;

import com.insightedulab.backend_java.oci.OciClient;
import com.insightedulab.backend_java.oci.OciException;
import com.insightedulab.backend_java.oci.OciProperties;
import com.insightedulab.backend_java.oci.OciProperties.EstadoPar;
import com.insightedulab.backend_java.oci.OciProperties.Par;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import java.io.IOException;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withException;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

/**
 * El cliente de OCI (T09) con un servidor simulado: no hace falta Spring ni la base. Comprueba el PUT que pide
 * la documentación de Oracle y, sobre todo, que ningún error deje escapar la URL PAR (una credencial).
 */
class OciClientTest {

    static final String SECRETO = "SECRETOdeLaPAR-0123456789abcdef";
    static final String PAR = "https://objectstorage.us-test-1.oraclecloud.com/p/" + SECRETO
            + "/n/espacio-de-prueba/b/bucket-de-prueba/o/";
    private static final String OBJETO = "generados/POST_LINKEDIN/2026-10-04/borrador-12.json";

    private MockRestServiceServer oci;
    private OciClient cliente;

    @BeforeEach
    void armar() {
        RestClient.Builder builder = RestClient.builder();
        oci = MockRestServiceServer.bindTo(builder).build();
        cliente = new OciClient(builder.build(), propiedades(PAR));
    }

    @Test
    void subeConPutALaParMasElNombreDelObjetoConElJsonEnElCuerpo() {
        byte[] json = "{\"id\":12,\"textoIa\":\"hola 🎉\"}".getBytes(StandardCharsets.UTF_8);
        oci.expect(requestTo(PAR + OBJETO)).andExpect(method(HttpMethod.PUT))
                .andExpect(header("Content-Type", "application/json"))
                .andExpect(content().bytes(json))
                .andRespond(withSuccess());

        cliente.subir(OBJETO, json);

        oci.verify();
    }

    @Test
    void cualquierRespuesta2xxEsExito() {
        oci.expect(requestTo(PAR + OBJETO)).andRespond(withStatus(HttpStatus.CREATED));

        cliente.subir(OBJETO, new byte[]{'{', '}'});

        oci.verify();
    }

    @ParameterizedTest
    @ValueSource(ints = {400, 401, 403, 404, 409, 500, 503})
    void unaRespuestaDeErrorEsUnaOciExceptionConElCodigoYSinLaPar(int codigo) {
        oci.expect(requestTo(PAR + OBJETO)).andRespond(withStatus(HttpStatus.valueOf(codigo)));

        assertThatThrownBy(() -> cliente.subir(OBJETO, new byte[]{'{', '}'}))
                .isInstanceOf(OciException.class)
                .hasMessage("OCI respondió HTTP " + codigo)
                .satisfies(e -> assertThat(e.getCause()).isNull());
    }

    @Test
    void unaRedireccionNoEsExito() {
        // Si la PAR estuviera mal armada, un 3xx no puede contarse como "subido"
        oci.expect(requestTo(PAR + OBJETO)).andRespond(withStatus(HttpStatus.FOUND));

        assertThatThrownBy(() -> cliente.subir(OBJETO, new byte[]{'{', '}'}))
                .isInstanceOf(OciException.class).hasMessage("OCI respondió HTTP 302");
    }

    @Test
    void siOciNoRespondeElErrorDiceLaClaseYNuncaLaPar() {
        // El mensaje que arma Spring en este caso SÍ lleva la URL completa: por eso no se usa
        oci.expect(requestTo(PAR + OBJETO)).andRespond(withException(new SocketTimeoutException("Read timed out")));

        assertThatThrownBy(() -> cliente.subir(OBJETO, new byte[]{'{', '}'}))
                .isInstanceOf(OciException.class)
                .hasMessage("No se pudo hablar con OCI: SocketTimeoutException")
                .satisfies(e -> {
                    assertThat(e.getCause()).as("la causa original lleva la URL").isNull();
                    assertThat(e.getMessage()).doesNotContain(SECRETO).doesNotContain("objectstorage");
                });
    }

    @Test
    void unaConexionRechazadaTampocoFiltraLaPar() {
        oci.expect(requestTo(PAR + OBJETO)).andRespond(withException(new IOException("Connection refused")));

        assertThatThrownBy(() -> cliente.subir(OBJETO, new byte[]{'{', '}'}))
                .isInstanceOf(OciException.class)
                .hasMessage("No se pudo hablar con OCI: IOException");
    }

    @Test
    void unaParQueNoFormaUnaUrlValidaFallaSinMostrarla() {
        String conEspacio = "https://objectstorage.us-test-1.oraclecloud.com/p/" + SECRETO + " con espacio/o/";
        OciClient malo = new OciClient(RestClient.builder().build(), propiedades(conEspacio));

        assertThatThrownBy(() -> malo.subir(OBJETO, new byte[]{'{', '}'}))
                .isInstanceOf(OciException.class)
                .hasMessage("La PAR no forma una URL válida con el nombre del objeto")
                .satisfies(e -> assertThat(e.getMessage()).doesNotContain(SECRETO));
    }

    // ── La forma de la PAR y las propiedades ──

    @Test
    void estadoPar() {
        assertThat(propiedades(PAR).estadoPar()).isEqualTo(EstadoPar.LISTA);
        assertThat(propiedades("  " + PAR + "\n").estadoPar()).as("se ignoran los espacios del .env").isEqualTo(EstadoPar.LISTA);
        assertThat(propiedades("").estadoPar()).isEqualTo(EstadoPar.SIN_PAR);
        assertThat(propiedades("   ").estadoPar()).isEqualTo(EstadoPar.SIN_PAR);
        assertThat(propiedades(null).estadoPar()).isEqualTo(EstadoPar.SIN_PAR);
        assertThat(new OciProperties(null, null, null, null, null, null, null, null).estadoPar())
                .isEqualTo(EstadoPar.SIN_PAR);
    }

    @ParameterizedTest
    @ValueSource(strings = {
            "http://objectstorage.us-test-1.oraclecloud.com/p/x/n/y/b/z/o/",   // sin https
            "https://example.com/p/x/n/y/b/z/o/",                              // no es objectstorage
            "https://objectstorage.us-test-1.oraclecloud.com/p/x/n/y/b/z/o",   // sin la barra final
            "https://objectstorage.us-test-1.oraclecloud.com/p/x/n/y/b/z/o/obj.json", // una PAR de un solo objeto
            "https://objectstorage.us-test-1.oraclecloud.com/p/x y/o/",        // con un espacio
            "no-es-una-url",
    })
    void unaParConOtraFormaEsInvalida(String url) {
        assertThat(propiedades(url).estadoPar()).isEqualTo(EstadoPar.FORMA_INVALIDA);
    }

    @Test
    void laParNoSeEscribeNiSiSeImprimenLasPropiedades() {
        OciProperties p = propiedades(PAR);

        assertThat(p.toString()).doesNotContain(SECRETO).doesNotContain("objectstorage").contains("oculta");
        assertThat(p.par().toString()).doesNotContain(SECRETO);
        assertThat(String.valueOf(p)).doesNotContain(PAR);
    }

    @Test
    void losValoresPorDefectoYUnaZonaInvalida() {
        OciProperties p = new OciProperties(null, null, null, null, null, null, null, null);

        assertThat(p.habilitada()).isTrue();
        assertThat(p.tanda()).isEqualTo(10);
        assertThat(p.maxIntentos()).isEqualTo(5);
        assertThat(p.zona()).isEqualTo("America/Bogota");
        assertThatThrownBy(() -> new OciProperties(true, 1L, 1, 1, 1, 1, "Marte/Olympus", new Par("")))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("oci.zona");
    }

    static OciProperties propiedades(String par) {
        return new OciProperties(true, 1000L, 10, 5, 420, 60, "America/Bogota", new Par(par));
    }
}
