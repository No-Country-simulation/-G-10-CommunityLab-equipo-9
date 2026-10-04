package com.insightedulab.backend_java.curaduria;

import com.insightedulab.backend_java.curaduria.CuraduriaRepository.Estado;
import com.insightedulab.backend_java.curaduria.VistasPanel.DetalleBorrador;
import com.insightedulab.backend_java.curaduria.VistasPanel.ListaBorradores;
import com.insightedulab.backend_java.curaduria.VistasPanel.ListaErrores;
import com.insightedulab.backend_java.curaduria.VistasPanel.PedidoAprobar;
import com.insightedulab.backend_java.curaduria.VistasPanel.PedidoEditar;
import com.insightedulab.backend_java.curaduria.VistasPanel.PedidoRechazar;
import com.insightedulab.backend_java.curaduria.VistasPanel.Reintento;
import com.insightedulab.backend_java.error.ConflictoException;
import com.insightedulab.backend_java.error.DatoInvalidoException;
import com.insightedulab.backend_java.error.NoEncontradoException;
import com.insightedulab.backend_java.model.enums.EstadoBorrador;
import com.insightedulab.backend_java.model.enums.TipoBorrador;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.regex.Pattern;

/**
 * Reglas del panel de curaduría (T07, contrato docs/contratos/PANEL_JAVA_v1.md):
 * <ul>
 *   <li>solo se editan, aprueban o rechazan borradores PENDIENTE (si no, 409);</li>
 *   <li>dos personas a la vez: gana la primera y la otra recibe 409 (la guarda está en el UPDATE);</li>
 *   <li>D6: un post o un caso de éxito no se aprueba sin consentimiento (422);</li>
 *   <li>el usuario lo envía el panel en X-Usuario. Java confía en él porque solo el panel tiene la clave,
 *       pero lo valida: así no llega cualquier texto a la base ni al registro.</li>
 * </ul>
 * El registro nunca lleva textos de alumnos ni de la IA (S11): solo ids, tipos y el usuario del panel.
 */
@Service
public class CuraduriaService {

    public static final Pattern USUARIO_VALIDO = Pattern.compile("[A-Za-z0-9._-]{1,40}");
    static final int MAX_TEXTO = 20_000;
    static final int MAX_MOTIVO = 500;
    /** Una semana: más que eso es un error del panel, no una revisión */
    static final int MAX_TIEMPO_SEG = 7 * 24 * 3600;
    static final int LIMITE_POR_DEFECTO = 100;
    static final int LIMITE_MAXIMO = 500;
    static final int LIMITE_ERRORES = 200;

    private static final Logger log = LoggerFactory.getLogger(CuraduriaService.class);

    private final CuraduriaRepository repo;

    public CuraduriaService(CuraduriaRepository repo) {
        this.repo = repo;
    }

    public ListaBorradores listar(String estado, String tipo, Integer limite) {
        String e = estado == null || estado.isBlank() ? EstadoBorrador.PENDIENTE.name() : valorDe(EstadoBorrador.class, "estado", estado);
        String t = tipo == null || tipo.isBlank() ? null : valorDe(TipoBorrador.class, "tipo", tipo);
        if (TipoBorrador.RESPUESTA_BOT.name().equals(t)) {
            throw new DatoInvalidoException("tipo", "Las respuestas del bot no pasan por el panel.");
        }
        int l = limite == null ? LIMITE_POR_DEFECTO : limite;
        if (l < 1 || l > LIMITE_MAXIMO) {
            throw new DatoInvalidoException("limite", "Tiene que estar entre 1 y " + LIMITE_MAXIMO + ".");
        }
        return new ListaBorradores(repo.listar(e, t, l));
    }

    public DetalleBorrador detalle(long id) {
        DetalleBorrador d = repo.detalle(id);
        if (d == null) {
            throw new NoEncontradoException("El borrador no existe.");
        }
        return d;
    }

    public DetalleBorrador editar(long id, String usuario, PedidoEditar pedido) {
        exigirUsuario(usuario);
        String texto = textoFinal(pedido == null ? null : pedido.textoFinal(), true);
        exigirPendiente(id);
        if (!repo.editar(id, texto)) {
            throw new ConflictoException("El borrador ya no está PENDIENTE: otra persona lo revisó.");
        }
        log.info("Borrador {} editado por {}", id, usuario);
        return detalle(id);
    }

    public DetalleBorrador aprobar(long id, String usuario, PedidoAprobar pedido) {
        exigirUsuario(usuario);
        if (pedido == null) {
            throw new DatoInvalidoException("tiempoCuraduriaSeg", "Falta el cuerpo del pedido.");
        }
        String texto = textoFinal(pedido.textoFinal(), false);
        int tiempo = tiempo(pedido.tiempoCuraduriaSeg(), true);
        boolean consentimiento = Boolean.TRUE.equals(pedido.consentimiento());
        Estado estado = exigirPendiente(id);
        if (CuraduriaRepository.requiereConsentimiento(estado.tipo()) && !consentimiento) {
            throw new DatoInvalidoException("consentimiento",
                    "Este borrador nombra a un alumno: hay que confirmar su consentimiento antes de aprobarlo (D6).");
        }
        if (!repo.aprobar(id, usuario, consentimiento, tiempo, texto)) {
            throw new ConflictoException("El borrador ya no está PENDIENTE: otra persona lo revisó.");
        }
        log.info("Borrador {} ({}) aprobado por {} en {} s{}", id, estado.tipo(), usuario, tiempo,
                texto != null ? ", con edición" : "");
        return detalle(id);
    }

    public DetalleBorrador rechazar(long id, String usuario, PedidoRechazar pedido) {
        exigirUsuario(usuario);
        String motivo = pedido == null ? null : limpiar(pedido.motivo());
        if (motivo != null && motivo.isBlank()) {
            motivo = null;
        }
        if (motivo != null && motivo.length() > MAX_MOTIVO) {
            throw new DatoInvalidoException("motivo", "Tiene más de " + MAX_MOTIVO + " caracteres.");
        }
        Integer tiempo = pedido == null || pedido.tiempoCuraduriaSeg() == null ? null
                : tiempo(pedido.tiempoCuraduriaSeg(), false);
        Estado estado = exigirPendiente(id);
        if (!repo.rechazar(id, usuario, motivo, tiempo)) {
            throw new ConflictoException("El borrador ya no está PENDIENTE: otra persona lo revisó.");
        }
        log.info("Borrador {} ({}) rechazado por {}", id, estado.tipo(), usuario);
        return detalle(id);
    }

    public ListaErrores errores() {
        return new ListaErrores(repo.erroresClasificacion(LIMITE_ERRORES), repo.erroresGeneracion(LIMITE_ERRORES));
    }

    /** DEC-111: la clasificación en ERROR vuelve a PENDIENTE con sus intentos en 0. */
    public Reintento reintentarClasificacion(long mensajeId, String usuario) {
        exigirUsuario(usuario);
        if (!repo.reintentarClasificacion(mensajeId)) {
            throw noReintentable(mensajeId, "clasificación");
        }
        log.info("Mensaje {}: clasificación devuelta a la cola por {}", mensajeId, usuario);
        return new Reintento(mensajeId, "clasificacion", "PENDIENTE");
    }

    /** DEC-111: la generación en ERROR vuelve a "sin generar" con sus intentos en 0. */
    public Reintento reintentarGeneracion(long mensajeId, String usuario) {
        exigirUsuario(usuario);
        if (!repo.reintentarGeneracion(mensajeId)) {
            throw noReintentable(mensajeId, "generación");
        }
        log.info("Mensaje {}: generación devuelta a la cola por {}", mensajeId, usuario);
        return new Reintento(mensajeId, "generacion", "SIN_GENERAR");
    }

    // ── Validaciones ──

    static void exigirUsuario(String usuario) {
        if (usuario == null || usuario.isBlank()) {
            throw new DatoInvalidoException("X-Usuario", "Falta el usuario del panel.");
        }
        if (!USUARIO_VALIDO.matcher(usuario).matches()) {
            throw new DatoInvalidoException("X-Usuario",
                    "El usuario solo puede tener letras sin tilde, números, '.', '_' y '-' (hasta 40).");
        }
    }

    private Estado exigirPendiente(long id) {
        Estado estado = repo.estado(id);
        if (estado == null) {
            throw new NoEncontradoException("El borrador no existe.");
        }
        if (!EstadoBorrador.PENDIENTE.name().equals(estado.estado())) {
            throw new ConflictoException("El borrador ya está " + estado.estado() + ": solo se cambian los PENDIENTE.");
        }
        return estado;
    }

    private RuntimeException noReintentable(long mensajeId, String etapa) {
        if (!repo.existeMensaje(mensajeId)) {
            return new NoEncontradoException("El mensaje no existe.");
        }
        return new ConflictoException("La " + etapa + " de este mensaje ya no está en ERROR.");
    }

    /** El texto editado, sin caracteres NUL (PostgreSQL no los acepta, T03). null si es opcional y no vino. */
    private static String textoFinal(String texto, boolean obligatorio) {
        if (texto == null) {
            if (obligatorio) {
                throw new DatoInvalidoException("textoFinal", "Falta el texto.");
            }
            return null;
        }
        String limpio = limpiar(texto);
        if (limpio.isBlank()) {
            throw new DatoInvalidoException("textoFinal", "El texto está vacío.");
        }
        if (limpio.length() > MAX_TEXTO) {
            throw new DatoInvalidoException("textoFinal", "Tiene más de " + MAX_TEXTO + " caracteres.");
        }
        return limpio;
    }

    private static int tiempo(Integer segundos, boolean obligatorio) {
        if (segundos == null) {
            if (obligatorio) {
                throw new DatoInvalidoException("tiempoCuraduriaSeg", "Falta el tiempo de revisión.");
            }
            return 0;
        }
        if (segundos < 0 || segundos > MAX_TIEMPO_SEG) {
            throw new DatoInvalidoException("tiempoCuraduriaSeg", "Tiene que estar entre 0 y " + MAX_TIEMPO_SEG + ".");
        }
        return segundos;
    }

    private static String limpiar(String texto) {
        return texto == null ? null : texto.replace("\u0000", "");
    }

    private static <E extends Enum<E>> String valorDe(Class<E> lista, String campo, String valor) {
        try {
            return Enum.valueOf(lista, valor).name();
        } catch (IllegalArgumentException e) {
            throw new DatoInvalidoException(campo, "No es un valor de la lista.");
        }
    }
}
