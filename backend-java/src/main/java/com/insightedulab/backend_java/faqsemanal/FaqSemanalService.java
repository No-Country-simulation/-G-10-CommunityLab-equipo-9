package com.insightedulab.backend_java.faqsemanal;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightedulab.backend_java.client.IaNoDisponibleException;
import com.insightedulab.backend_java.client.IaRechazoException;
import com.insightedulab.backend_java.client.NlpDataClient;
import com.insightedulab.backend_java.client.RespuestaFaqSemanal;
import com.insightedulab.backend_java.faqsemanal.FaqSemanalRepository.Duda;
import com.insightedulab.backend_java.faqsemanal.FaqSemanalRepository.Semana;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

import java.io.IOException;
import java.time.Duration;
import java.time.Instant;
import java.time.ZonedDateTime;
import java.time.temporal.IsoFields;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * La FAQ semanal (T06b, N4, DEC-94 a DEC-99).
 *
 * <ol>
 *   <li>Registra la semana (una fila por semana en faq_semanas) y la reserva.</li>
 *   <li>Junta las dudas de los últimos días y le pide la FAQ a la IA (POST /v1/faq), sin transacción abierta.
 *       Cada autor viaja como una clave opaca (a1, a2…): nunca su nombre, su usuario ni su ID.</li>
 *   <li>Guarda en una transacción el borrador FAQ (PENDIENTE, sin mensaje_id) y el estado de la semana.</li>
 * </ol>
 *
 * Si no hay preguntas repetidas, la semana queda SIN_REPETIDAS y no se vuelve a intentar. Si falla, suma un
 * intento y se reintenta con la misma ventana; al máximo, ERROR. Nada se publica: Marketing aprueba (N6).
 */
@Service
public class FaqSemanalService {

    private static final Logger log = LoggerFactory.getLogger(FaqSemanalService.class);
    private static final int MAX_FUENTES = 20;

    /**
     * Lo que pasó; va al registro (sin textos: S11).
     *
     * @param estado GENERADA, SIN_REPETIDAS, REINTENTO, ERROR u OMITIDA (ya terminó o la arma otra ejecución)
     */
    public record Resultado(String semana, String estado, int dudas, int repetidas, int conRespuesta,
                            long duracionMs) {}

    private final FaqSemanalRepository repo;
    private final NlpDataClient ia;
    private final ObjectMapper objectMapper;
    private final FaqSemanalProperties propiedades;
    private final TransactionTemplate transaccion;

    public FaqSemanalService(FaqSemanalRepository repo, NlpDataClient ia, ObjectMapper objectMapper,
                             FaqSemanalProperties propiedades, TransactionTemplate transaccion) {
        this.repo = repo;
        this.ia = ia;
        this.objectMapper = objectMapper;
        this.propiedades = propiedades;
        this.transaccion = transaccion;
    }

    /** Arma la FAQ de la semana de "ahora", si todavía no se armó. La ventana termina en "ahora". */
    public Resultado ejecutar(Instant ahora) {
        String semana = semanaDe(ahora);
        repo.crear(semana, ahora.minus(Duration.ofDays(propiedades.dias())), ahora);
        Semana s = repo.reservar(semana, propiedades.reservaSegundos());
        if (s == null) {
            return new Resultado(semana, "OMITIDA", 0, 0, 0, 0);
        }
        return procesar(s);
    }

    /** Reintenta la semana más antigua que quedó sin terminar, con su misma ventana. null si no hay ninguna. */
    public Resultado reintentar() {
        Semana s = repo.reservarPendiente(propiedades.reservaSegundos());
        return s == null ? null : procesar(s);
    }

    /** La semana ISO en la zona configurada, por ejemplo 2026-W40. */
    public String semanaDe(Instant momento) {
        ZonedDateTime z = momento.atZone(propiedades.zonaId());
        return String.format("%d-W%02d", z.get(IsoFields.WEEK_BASED_YEAR), z.get(IsoFields.WEEK_OF_WEEK_BASED_YEAR));
    }

    private Resultado procesar(Semana s) {
        long inicio = System.nanoTime();
        List<Duda> dudas = repo.dudas(s.desde(), s.hasta(), propiedades.maxDudas());
        Map<String, String> claves = clavesOpacas(dudas);
        if (claves.size() < 2) {
            // Sin dos personas distintas no hay preguntas repetidas: no se gasta la IA
            return terminar(s, "SIN_REPETIDAS", "Las dudas de la ventana son de menos de 2 personas; no se llamó a la IA.",
                    dudas.size(), 0, 0, null, inicio);
        }

        String pedidoId = "faq-" + UUID.randomUUID();
        RespuestaFaqSemanal r;
        try {
            r = ia.faq(armarPedido(pedidoId, s, dudas, claves), pedidoId);
        } catch (IaRechazoException e) {
            log.error("FAQ semanal {}: la IA rechazó el pedido (422), error de programación", s.semana());
            return registrarError(s, "La IA rechazó el pedido (422).", dudas.size(), inicio);
        } catch (IaNoDisponibleException e) {
            log.warn("FAQ semanal {}: la IA no respondió ({})", s.semana(), e.getMessage());
            return registrarError(s, e.getMessage(), dudas.size(), inicio);
        } catch (RuntimeException e) {
            log.error("FAQ semanal {}: falló la llamada a la IA", s.semana(), e);
            return registrarError(s, "Falló la llamada a la IA: " + e.getClass().getSimpleName() + ".", dudas.size(), inicio);
        }

        List<RespuestaFaqSemanal.Grupo> grupos = r.grupos() == null ? List.of() : r.grupos();
        boolean hayTexto = r.texto() != null && !r.texto().isBlank();
        if (!r.ok()) {
            return registrarError(s, r.motivo(), dudas.size(), inicio);
        } else if (hayTexto != !grupos.isEmpty()) {
            // F4: la IA no debería mandar texto sin grupos ni grupos sin texto; si pasa, es un error
            return registrarError(s, "La IA respondió texto y grupos que no coinciden.", dudas.size(), inicio);
        } else if (!hayTexto) {
            return terminar(s, "SIN_REPETIDAS", r.motivo(), dudas.size(), 0, 0, null, inicio);
        }
        int conRespuesta = (int) grupos.stream().filter(g -> Boolean.TRUE.equals(g.respondida())).count();
        return guardarBorrador(s, r, dudas.size(), grupos.size(), conRespuesta, inicio);
    }

    private Resultado guardarBorrador(Semana s, RespuestaFaqSemanal r, int dudas, int repetidas, int conRespuesta,
                                      long inicio) {
        int tokensIn = r.metricas() == null || r.metricas().tokensIn() == null ? 0 : r.metricas().tokensIn();
        int tokensOut = r.metricas() == null || r.metricas().tokensOut() == null ? 0 : r.metricas().tokensOut();
        Boolean guardado;
        try {
            guardado = transaccion.execute(estado -> {
                long borradorId = repo.insertarBorrador(r.texto().strip(), tokensIn, tokensOut);
                if (!repo.terminar(s, "GENERADA", r.motivo(), dudas, repetidas, conRespuesta, borradorId)) {
                    estado.setRollbackOnly();  // otra ejecución ya la terminó: no queda un borrador suelto
                    return false;
                }
                return true;
            });
        } catch (DataAccessException e) {
            log.error("FAQ semanal {}: no se pudo guardar el borrador ({})", s.semana(),
                    e.getMostSpecificCause().getClass().getSimpleName());
            return registrarError(s, "No se pudo guardar el borrador.", dudas, inicio);
        }
        String estado = Boolean.TRUE.equals(guardado) ? "GENERADA" : "OMITIDA";
        return resultado(s, estado, dudas, repetidas, conRespuesta, inicio);
    }

    private Resultado terminar(Semana s, String estado, String motivo, int dudas, int repetidas, int conRespuesta,
                               Long borradorId, long inicio) {
        boolean guardado = repo.terminar(s, estado, motivo, dudas, repetidas, conRespuesta, borradorId);
        return resultado(s, guardado ? estado : "OMITIDA", dudas, repetidas, conRespuesta, inicio);
    }

    private Resultado registrarError(Semana s, String motivo, int dudas, long inicio) {
        String estado = repo.registrarError(s, motivo, dudas, propiedades.maxIntentos());
        return resultado(s, estado == null ? "OMITIDA" : estado, dudas, 0, 0, inicio);
    }

    private static Resultado resultado(Semana s, String estado, int dudas, int repetidas, int conRespuesta, long inicio) {
        return new Resultado(s.semana(), estado, dudas, repetidas, conRespuesta, (System.nanoTime() - inicio) / 1_000_000);
    }

    /** a1, a2… en el orden en que aparecen. Solo viven en este pedido: la IA no puede saber quién es quién. */
    private static Map<String, String> clavesOpacas(List<Duda> dudas) {
        Map<String, String> claves = new HashMap<>();
        for (Duda d : dudas) {
            claves.computeIfAbsent(d.autorId(), id -> "a" + (claves.size() + 1));
        }
        return claves;
    }

    /** El pedido de §10.2 del contrato. */
    private Map<String, Object> armarPedido(String pedidoId, Semana s, List<Duda> dudas, Map<String, String> claves) {
        Map<String, Object> pedido = new LinkedHashMap<>();
        pedido.put("pedidoId", pedidoId);
        pedido.put("semana", s.semana());
        pedido.put("desde", s.desde().atZone(propiedades.zonaId()).toLocalDate().toString());
        pedido.put("hasta", s.hasta().atZone(propiedades.zonaId()).toLocalDate().toString());
        List<Map<String, Object>> lista = new ArrayList<>();
        for (Duda d : dudas) {
            Map<String, Object> duda = new LinkedHashMap<>();
            duda.put("autor", claves.get(d.autorId()));
            duda.put("texto", d.texto());
            duda.put("tema", d.tema());
            duda.put("respuesta", d.respuestaTexto() == null ? null
                    : Map.of("texto", d.respuestaTexto(), "fuentes", fuentes(d.respuestaFuentes())));
            lista.add(duda);
        }
        pedido.put("dudas", lista);
        return pedido;
    }

    private List<String> fuentes(String json) {
        if (json == null) {
            return List.of();
        }
        try {
            List<String> fuentes = objectMapper.readValue(json, new TypeReference<List<String>>() {});
            return fuentes.stream().filter(f -> f != null && !f.isBlank()).limit(MAX_FUENTES).toList();
        } catch (IOException e) {
            return List.of();  // sin fuentes legibles la respuesta igual vale: la publicó el bot con respaldo
        }
    }
}
