package com.insightedulab.backend_java.generacion;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightedulab.backend_java.client.IaNoDisponibleException;
import com.insightedulab.backend_java.client.IaRechazoException;
import com.insightedulab.backend_java.client.NlpDataClient;
import com.insightedulab.backend_java.client.RespuestaGenerar;
import com.insightedulab.backend_java.generacion.GeneracionRepository.Logro;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

import java.io.IOException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Genera en segundo plano los borradores del Agente-Mod (T06, N3, DEC-80).
 *
 * <ol>
 *   <li>Reserva una tanda chica de logros sin generación (SKIP LOCKED + generacion_reservada_hasta).</li>
 *   <li>Por cada uno, le pide a la IA el post y el caso de éxito (POST /v1/generar), sin transacción abierta.</li>
 *   <li>Guarda el resultado solo si el mensaje no cambió y sigue siendo un TESTIMONIO OK.</li>
 * </ol>
 *
 * Nada queda a medias: los dos borradores y el estado GENERADO van en una transacción.
 * Nada se publica: los borradores quedan PENDIENTE para que Marketing los apruebe (N6).
 */
@Service
public class GeneracionService {

    private static final Logger log = LoggerFactory.getLogger(GeneracionService.class);

    /** Lo que pasó en una tanda; va al registro (sin textos: S11). */
    public record Resumen(int tomados, int generados, int noPublicables, int error, int reintento, int cambiaron,
                          long duracionMs) {}

    private final GeneracionRepository repo;
    private final NlpDataClient ia;
    private final ObjectMapper objectMapper;
    private final GeneracionProperties propiedades;
    private final TransactionTemplate transaccion;

    public GeneracionService(GeneracionRepository repo, NlpDataClient ia, ObjectMapper objectMapper,
                             GeneracionProperties propiedades, TransactionTemplate transaccion) {
        this.repo = repo;
        this.ia = ia;
        this.objectMapper = objectMapper;
        this.propiedades = propiedades;
        this.transaccion = transaccion;
    }

    public Resumen procesarTanda() {
        long inicio = System.nanoTime();
        List<Logro> tomados = repo.reservar(propiedades.tanda(), propiedades.reservaSegundos());
        Contador c = new Contador();
        for (Logro l : tomados) {
            generar(l, c);
        }
        return new Resumen(tomados.size(), c.generados, c.noPublicables, c.error, c.reintento, c.cambiaron,
                (System.nanoTime() - inicio) / 1_000_000);
    }

    private void generar(Logro l, Contador c) {
        String pedidoId = "gen-" + UUID.randomUUID();
        RespuestaGenerar r;
        try {
            r = ia.generar(armarPedido(pedidoId, l), pedidoId);
        } catch (IaRechazoException e) {
            log.error("Generar {}: la IA rechazó el pedido (422), error de programación", l.discordId());
            registrarError(l, "La IA rechazó el pedido (422).", c);
            return;
        } catch (IaNoDisponibleException e) {
            log.warn("Generar {}: la IA no respondió ({})", l.discordId(), e.getMessage());
            registrarError(l, e.getMessage(), c);
            return;
        } catch (RuntimeException e) {
            log.error("Generar {}: falló la llamada a la IA", l.discordId(), e);
            registrarError(l, "Falló la llamada a la IA: " + e.getClass().getSimpleName() + ".", c);
            return;
        }

        if (!r.ok() || r.publicable() == null) {
            log.info("Generar {}: ERROR de la IA", l.discordId());  // el motivo puede citar al alumno: no va al registro
            registrarError(l, r.motivo(), c);
        } else if (!r.publicable()) {
            guardarNoPublicable(l, r, c);
        } else if (vacio(r.postLinkedin()) || vacio(r.casoExito())) {
            // F4: la IA no debería mandar un publicable sin los dos textos; si pasa, es un error y no un borrador a medias
            registrarError(l, "La IA marcó el logro como publicable sin los dos textos.", c);
        } else {
            guardarBorradores(l, r, c);
        }
    }

    private void guardarBorradores(Logro l, RespuestaGenerar r, Contador c) {
        int tokensIn = tokens(r, true);
        int tokensOut = tokens(r, false);
        Boolean guardado;
        try {
            guardado = transaccion.execute(estado -> {
                if (!repo.marcar(l, "GENERADO", r.motivo())) {
                    return false;  // cambió mientras la IA redactaba: no se inserta nada
                }
                // Una sola llamada al LLM escribió los dos textos: sus tokens van en el post, y el caso lleva 0,
                // así la suma de la tabla es exacta
                repo.insertarBorrador(l.id(), "POST_LINKEDIN", r.postLinkedin().strip(), tokensIn, tokensOut);
                repo.insertarBorrador(l.id(), "CASO_EXITO", r.casoExito().strip(), 0, 0);
                return true;
            });
        } catch (DataAccessException e) {
            // Por ejemplo, ya había un borrador PENDIENTE del mismo tipo (índice único de V4): no se guarda nada
            log.error("Generar {}: no se pudieron guardar los borradores ({})", l.discordId(),
                    e.getMostSpecificCause().getClass().getSimpleName());
            repo.liberar(l);
            c.error++;
            return;
        }
        if (Boolean.TRUE.equals(guardado)) {
            c.generados++;
        } else {
            cambio(l, c);
        }
    }

    private void guardarNoPublicable(Logro l, RespuestaGenerar r, Contador c) {
        if (repo.marcar(l, "NO_PUBLICABLE", r.motivo())) {
            c.noPublicables++;
        } else {
            cambio(l, c);
        }
    }

    private void registrarError(Logro l, String motivo, Contador c) {
        String estado = repo.registrarError(l, motivo, propiedades.maxIntentos());
        if (estado == null) {
            cambio(l, c);
        } else if ("ERROR".equals(estado)) {
            c.error++;
        } else {
            c.reintento++;
        }
    }

    private void cambio(Logro l, Contador c) {
        // El lote de la hora lo editó (o se reclasificó) mientras la IA redactaba: se descarta el resultado
        log.info("Generar {}: el mensaje cambió mientras la IA redactaba; no se guarda nada", l.discordId());
        repo.liberar(l);
        c.cambiaron++;
    }

    /** El pedido de §9.2 del contrato: el logro y sus respuestas, con las cajas tal cual se guardaron. */
    private Map<String, Object> armarPedido(String pedidoId, Logro l) {
        Map<String, Object> pedido = new LinkedHashMap<>();
        pedido.put("versionContrato", l.versionContrato());
        pedido.put("pedidoId", pedidoId);
        pedido.put("logro", caja(l.contratoJson(), l.discordId()));
        List<Map<String, Object>> respuestas = new ArrayList<>();
        for (String json : repo.respuestas(l.discordId(), propiedades.maxRespuestas())) {
            respuestas.add(caja(json, l.discordId()));
        }
        pedido.put("respuestas", respuestas);
        return pedido;
    }

    private Map<String, Object> caja(String json, String discordId) {
        try {
            return objectMapper.readValue(json, new TypeReference<>() {});
        } catch (IOException e) {
            throw new IllegalStateException("Una caja del logro " + discordId + " no es JSON válido", e);
        }
    }

    private static int tokens(RespuestaGenerar r, boolean entrada) {
        if (r.metricas() == null) {
            return 0;
        }
        Integer n = entrada ? r.metricas().tokensIn() : r.metricas().tokensOut();
        return n == null ? 0 : n;
    }

    private static boolean vacio(String texto) {
        return texto == null || texto.isBlank();
    }

    private static final class Contador {
        int generados;
        int noPublicables;
        int error;
        int reintento;
        int cambiaron;
    }
}
