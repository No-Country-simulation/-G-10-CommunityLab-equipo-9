package com.insightedulab.backend_java.envivo;

import com.insightedulab.backend_java.clasificacion.ClasificacionProperties;
import com.insightedulab.backend_java.clasificacion.ClasificacionRepository;
import com.insightedulab.backend_java.clasificacion.ClasificacionRepository.Pendiente;
import com.insightedulab.backend_java.clasificacion.LoteParaIa;
import com.insightedulab.backend_java.client.IaNoDisponibleException;
import com.insightedulab.backend_java.client.IaRechazoException;
import com.insightedulab.backend_java.client.NlpDataClient;
import com.insightedulab.backend_java.client.RespuestaIa;
import com.insightedulab.backend_java.dto.lote.LoteEntrada;
import com.insightedulab.backend_java.envivo.OrdenBot.Orden;
import com.insightedulab.backend_java.error.ContratoInvalidoException;
import com.insightedulab.backend_java.error.ErrorApi.ErrorCampo;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository.DatosMensaje;
import com.insightedulab.backend_java.service.LoteService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/**
 * Un mensaje en vivo del bot (POST /api/v1/mensajes/en-vivo, T05):
 * <ol>
 *   <li>Lo valida igual que el lote de la hora (contrato v1, sin NUL).</li>
 *   <li>En UNA transacción: lo guarda (upsert) y lo reserva. Así la clasificación en segundo plano
 *       no puede tomarlo mientras se procesa en vivo (observación de T04).</li>
 *   <li>Llama a la IA en modo tiempoReal, sin transacción abierta.</li>
 *   <li>Guarda las etiquetas y la respuesta con las guardas de T04, y le devuelve al bot una orden (DEC-68).</li>
 * </ol>
 * Si la IA falla, el mensaje queda PENDIENTE y sin reserva: lo clasifica la tarea en segundo plano
 * y el bot no responde nada (DEC-67).
 */
@Service
public class EnVivoService {

    private static final Logger log = LoggerFactory.getLogger(EnVivoService.class);

    static final String MODO = "tiempoReal";
    static final String REACCION_LOGRO = "🎉";
    static final String TEXTO_DERIVAR = "¡Gracias por tu pregunta! No encontré una respuesta segura en los "
            + "documentos del curso, así que un mentor te responderá pronto. 🙏";
    /** Discord no acepta mensajes de más de 2000 caracteres. */
    static final int MAX_CARACTERES_DISCORD = 2000;

    private final LoteService loteService;
    private final MensajeUpsertRepository upsertRepo;
    private final EnVivoRepository repo;
    private final ClasificacionRepository clasificacionRepo;
    private final LoteParaIa loteParaIa;
    private final NlpDataClient ia;
    private final ClasificacionProperties propiedades;
    private final TransactionTemplate transaccion;

    public EnVivoService(LoteService loteService, MensajeUpsertRepository upsertRepo, EnVivoRepository repo,
                         ClasificacionRepository clasificacionRepo, LoteParaIa loteParaIa, NlpDataClient ia,
                         ClasificacionProperties propiedades, TransactionTemplate transaccion) {
        this.loteService = loteService;
        this.upsertRepo = upsertRepo;
        this.repo = repo;
        this.clasificacionRepo = clasificacionRepo;
        this.loteParaIa = loteParaIa;
        this.ia = ia;
        this.propiedades = propiedades;
        this.transaccion = transaccion;
    }

    public OrdenBot procesar(LoteEntrada lote) {
        long inicio = System.nanoTime();
        exigirUnMensajeEnTiempoReal(lote);
        DatosMensaje mensaje = loteService.validarYLimpiar(lote).get(0);

        // El upsert y la reserva en la misma transacción: la fila aparece ya reservada
        Optional<Pendiente> reservado = transaccion.execute(estado -> {
            upsertRepo.upsert(mensaje);
            return repo.reservar(mensaje.discordId(), propiedades.reservaSegundos());
        });
        OrdenBot orden;
        if (reservado == null || reservado.isEmpty()) {
            log.info("En vivo {}: ya estaba clasificado, respondido o reservado; no se llama a la IA",
                    mensaje.discordId());
            orden = OrdenBot.nada(mensaje.discordId());
        } else {
            orden = clasificarYResponder(reservado.get(), lote.loteId());
        }
        // Solo IDs, la orden y el tiempo: nunca el texto del alumno (S11)
        log.info("En vivo {}: orden {} · {} ms", mensaje.discordId(), orden.orden(),
                (System.nanoTime() - inicio) / 1_000_000);
        return orden;
    }

    private OrdenBot clasificarYResponder(Pendiente m, String loteId) {
        RespuestaIa respuesta;
        try {
            respuesta = ia.procesar(loteParaIa.armar(loteId, m.servidorId(), MODO, List.of(m)), loteId);
        } catch (IaRechazoException e) {
            log.error("En vivo {}: la IA rechazó el lote (422), error de programación. Campos: {}", m.discordId(),
                    e.getErrores().stream().map(ErrorCampo::campo).toList());
            registrarError(m, null);
            return OrdenBot.nada(m.discordId());
        } catch (IaNoDisponibleException e) {
            log.warn("En vivo {}: la IA no respondió ({}). Sigue PENDIENTE para la clasificación en segundo plano",
                    m.discordId(), e.getMessage());
            sumarIntento(m);
            return OrdenBot.nada(m.discordId());
        } catch (RuntimeException e) {
            // Por ejemplo, una respuesta que no se puede leer: se trata como un fallo pasajero
            log.error("En vivo {}: falló la llamada a la IA", m.discordId(), e);
            sumarIntento(m);
            return OrdenBot.nada(m.discordId());
        }

        List<RespuestaIa.Resultado> resultados = respuesta == null || respuesta.resultados() == null
                ? List.of() : respuesta.resultados();
        RespuestaIa.Resultado r = resultados.stream()
                .filter(x -> x != null && m.discordId().equals(x.discordId()))
                .findFirst().orElse(null);
        if (r == null || !r.ok()) {
            log.info("En vivo {}: ERROR de la IA ({})", m.discordId(), r == null ? "sin resultado" : r.razon());
            registrarError(m, r == null ? null : r.metodo());
            return OrdenBot.nada(m.discordId());
        }

        Decision d = decidir(m.discordId(), r);
        try {
            if (repo.guardarOk(m, r, d.respuesta())) {
                return d.orden();
            }
        } catch (DataIntegrityViolationException e) {
            // Una etiqueta fuera de las listas cerradas (CHECK de V2): se cuenta como error de la IA
            log.warn("En vivo {}: la IA devolvió una etiqueta fuera de la lista", m.discordId());
            registrarError(m, r.metodo());
            return OrdenBot.nada(m.discordId());
        }
        // El lote de la hora cambió el mensaje mientras la IA lo procesaba: el resultado viejo no se guarda
        log.info("En vivo {}: el mensaje cambió mientras la IA lo procesaba; no se responde", m.discordId());
        clasificacionRepo.liberar(m);
        return OrdenBot.nada(m.discordId());
    }

    /** La tabla de la ficha T05 §3.4: qué se guarda y qué orden recibe el bot. */
    private record Decision(OrdenBot orden, EnVivoRepository.Respuesta respuesta) {}

    private static Decision decidir(String discordId, RespuestaIa.Resultado r) {
        String intencion = r.intencion();
        if ("PREGUNTA_FAQ".equals(intencion)) {
            RespuestaIa.Respuesta faq = r.respuesta();
            if (faq != null && faq.publicable()) {
                List<String> fuentes = faq.fuentes() == null ? List.of() : List.copyOf(faq.fuentes());
                return new Decision(
                        new OrdenBot(OrdenBot.VERSION, discordId, Orden.RESPONDER, textoParaPublicar(faq.texto()), null),
                        new EnVivoRepository.Respuesta("RESPONDIDA", faq.texto(), fuentes));
            }
            // D3: sin respaldo firme (o con el tope agotado) no se publica el texto de la IA
            return new Decision(new OrdenBot(OrdenBot.VERSION, discordId, Orden.DERIVAR, TEXTO_DERIVAR, null),
                    new EnVivoRepository.Respuesta("DERIVADA", null, null));
        }
        if ("TESTIMONIO".equals(intencion)) {
            // F5: a un logro, solo una reacción. Los borradores de LinkedIn van al panel, no a Discord
            return new Decision(new OrdenBot(OrdenBot.VERSION, discordId, Orden.REACCIONAR, null, REACCION_LOGRO),
                    EnVivoRepository.Respuesta.NINGUNA);
        }
        return new Decision(OrdenBot.nada(discordId), EnVivoRepository.Respuesta.NINGUNA);
    }

    /**
     * La respuesta de la IA tal cual, recortada al máximo de Discord.
     * No se le agrega un pie con las fuentes: el Agente FAQ ya cita en el texto el documento que usó,
     * mientras que "fuentes" es solo el primero de los fragmentos que encontró la búsqueda, y a veces
     * no es el mismo (prueba real de T05). Las fuentes se guardan igual en respuesta_fuentes.
     */
    static String textoParaPublicar(String texto) {
        String cuerpo = texto.strip();
        return cuerpo.length() <= MAX_CARACTERES_DISCORD
                ? cuerpo : cuerpo.substring(0, MAX_CARACTERES_DISCORD - 1) + "…";
    }

    private void registrarError(Pendiente m, String metodo) {
        if (clasificacionRepo.guardarError(m, metodo, propiedades.maxIntentos()) == null) {
            clasificacionRepo.liberar(m);  // cambió mientras tanto
        }
    }

    private void sumarIntento(Pendiente m) {
        if (!clasificacionRepo.sumarIntento(m)) {
            clasificacionRepo.liberar(m);  // cambió mientras tanto
        }
    }

    /** La puerta en vivo recibe un mensaje por pedido, en modo tiempoReal (ficha T05 §3.1). */
    private static void exigirUnMensajeEnTiempoReal(LoteEntrada lote) {
        List<ErrorCampo> errores = new ArrayList<>();
        if (!MODO.equals(lote.modo())) {
            errores.add(new ErrorCampo("modo", "debe ser tiempoReal en esta ruta"));
        }
        if (lote.mensajes() != null && lote.mensajes().size() != 1) {
            errores.add(new ErrorCampo("mensajes", "debe traer exactamente un mensaje en esta ruta"));
        }
        if (!errores.isEmpty()) {
            throw new ContratoInvalidoException(errores);
        }
    }
}
