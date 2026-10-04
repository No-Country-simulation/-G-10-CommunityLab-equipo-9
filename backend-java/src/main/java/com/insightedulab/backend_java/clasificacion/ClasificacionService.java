package com.insightedulab.backend_java.clasificacion;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightedulab.backend_java.client.IaNoDisponibleException;
import com.insightedulab.backend_java.client.IaRechazoException;
import com.insightedulab.backend_java.client.NlpDataClient;
import com.insightedulab.backend_java.client.RespuestaIa;
import com.insightedulab.backend_java.clasificacion.ClasificacionRepository.Pendiente;
import com.insightedulab.backend_java.error.ErrorApi;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.function.Function;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * Clasifica en segundo plano los mensajes PENDIENTE (OE2, F4).
 *
 * <ol>
 *   <li>Reserva una tanda chica (SKIP LOCKED + reservado_hasta).</li>
 *   <li>Arma un Lote del contrato v1 con sus cajas y llama a la IA, sin transacción abierta.</li>
 *   <li>Guarda cada resultado solo si el mensaje no cambió mientras tanto (actualizado_en).</li>
 * </ol>
 *
 * Un fallo de la IA nunca pierde ni marca mal un mensaje: o queda PENDIENTE para reintentar,
 * o pasa a ERROR después de {@code maxIntentos} errores de la IA en ese mensaje.
 */
@Service
public class ClasificacionService {

    private static final Logger log = LoggerFactory.getLogger(ClasificacionService.class);
    private static final DateTimeFormatter FECHA_UTC = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'");
    // "mensajes.2.autor.tipo" → 2: la IA dice qué mensaje del lote no cumple el contrato
    private static final Pattern INDICE_MENSAJE = Pattern.compile("^mensajes\\.(\\d+)(\\.|$)");

    /** Lo que pasó en una tanda; va al registro (sin textos de mensajes: S11). */
    public record Resumen(int tomados, int ok, int error, int reintento, int cambiaron, long duracionMs) {
        static Resumen vacio() {
            return new Resumen(0, 0, 0, 0, 0, 0);
        }
    }

    private final ClasificacionRepository repo;
    private final NlpDataClient ia;
    private final ObjectMapper objectMapper;
    private final ClasificacionProperties propiedades;

    public ClasificacionService(ClasificacionRepository repo, NlpDataClient ia, ObjectMapper objectMapper,
                                ClasificacionProperties propiedades) {
        this.repo = repo;
        this.ia = ia;
        this.objectMapper = objectMapper;
        this.propiedades = propiedades;
    }

    public Resumen procesarTanda() {
        long inicio = System.nanoTime();
        List<Pendiente> tomados = repo.reservar(propiedades.tanda(), propiedades.reservaSegundos());
        if (tomados.isEmpty()) {
            return Resumen.vacio();
        }
        Contador c = new Contador();
        // Un Lote por servidor: servidorId va en el sobre, no en cada mensaje
        Map<String, List<Pendiente>> porServidor = tomados.stream().collect(
                Collectors.groupingBy(Pendiente::servidorId, LinkedHashMap::new, Collectors.toList()));
        porServidor.forEach((servidor, mensajes) -> procesarLote(servidor, mensajes, c));
        return new Resumen(tomados.size(), c.ok, c.error, c.reintento, c.cambiaron,
                (System.nanoTime() - inicio) / 1_000_000);
    }

    public long contarSinServidor() {
        return repo.contarSinServidor();
    }

    private void procesarLote(String servidorId, List<Pendiente> mensajes, Contador c) {
        List<Pendiente> ordenados = new ArrayList<>(mensajes);
        ordenados.sort((a, b) -> a.fecha().compareTo(b.fecha()));
        String loteId = "clasif-" + UUID.randomUUID();

        RespuestaIa respuesta;
        try {
            respuesta = ia.procesar(armarLote(loteId, servidorId, ordenados), loteId);
        } catch (IaRechazoException e) {
            rechazado(loteId, ordenados, e, c);
            return;
        } catch (IaNoDisponibleException e) {
            log.warn("Tanda {}: la IA no respondió ({}). Los {} mensajes siguen PENDIENTE y se reintentan",
                    loteId, e.getMessage(), ordenados.size());
            ordenados.forEach(m -> {
                if (repo.sumarIntento(m)) c.reintento++; else c.cambiaron++;
            });
            return;
        }

        Map<String, RespuestaIa.Resultado> porId = respuesta.resultados().stream()
                .filter(r -> r != null && r.discordId() != null)
                .collect(Collectors.toMap(RespuestaIa.Resultado::discordId, Function.identity(), (a, b) -> a));
        for (Pendiente m : ordenados) {
            guardar(m, porId.get(m.discordId()), c);
        }
    }

    private void guardar(Pendiente m, RespuestaIa.Resultado r, Contador c) {
        if (r != null && r.ok()) {
            try {
                if (repo.guardarOk(m, r)) {
                    c.ok++;
                } else {
                    cambio(m, c);
                }
                return;
            } catch (DataIntegrityViolationException e) {
                // Una etiqueta fuera de las listas cerradas (CHECK de V2): se cuenta como error de la IA
                log.warn("Mensaje {}: la IA devolvió una etiqueta fuera de la lista", m.discordId());
            }
        } else if (r == null) {
            log.warn("Mensaje {}: la IA no devolvió resultado", m.discordId());
        } else {
            log.info("Mensaje {}: ERROR de la IA ({})", m.discordId(), r.razon());
        }
        registrarError(m, r == null ? null : r.metodo(), c);
    }

    private void registrarError(Pendiente m, String metodo, Contador c) {
        String estado = repo.guardarError(m, metodo, propiedades.maxIntentos());
        if (estado == null) {
            cambio(m, c);
        } else if ("ERROR".equals(estado)) {
            c.error++;
        } else {
            c.reintento++;
        }
    }

    /** 422: solo los mensajes que la IA señala suman intento; los demás se liberan sin penalizar. */
    private void rechazado(String loteId, List<Pendiente> ordenados, IaRechazoException e, Contador c) {
        Set<Integer> culpables = new HashSet<>();
        for (ErrorApi.ErrorCampo campo : e.getErrores()) {
            Matcher indice = INDICE_MENSAJE.matcher(campo.campo() == null ? "" : campo.campo());
            if (indice.find()) {
                culpables.add(Integer.parseInt(indice.group(1)));
            }
        }
        log.error("Tanda {}: la IA rechazó el lote (422), error de programación. Campos: {}", loteId,
                e.getErrores().stream().map(ErrorApi.ErrorCampo::campo).toList());
        for (int i = 0; i < ordenados.size(); i++) {
            Pendiente m = ordenados.get(i);
            if (culpables.isEmpty() || culpables.contains(i)) {
                registrarError(m, null, c);
            } else {
                repo.liberar(m);
                c.reintento++;
            }
        }
    }

    private void cambio(Pendiente m, Contador c) {
        // El lote de la hora lo actualizó mientras la IA lo procesaba: se descarta el resultado viejo
        repo.liberar(m);
        c.cambiaron++;
    }

    private Map<String, Object> armarLote(String loteId, String servidorId, List<Pendiente> mensajes) {
        Map<String, Object> lote = new LinkedHashMap<>();
        lote.put("versionContrato", mensajes.get(0).versionContrato());
        lote.put("loteId", loteId);
        lote.put("fuente", "discord");
        lote.put("modo", "historial");  // en historial la IA no gasta en respuestas del FAQ
        lote.put("servidorId", servidorId);
        lote.put("generadoEn", FECHA_UTC.format(Instant.now().truncatedTo(ChronoUnit.MILLIS).atOffset(ZoneOffset.UTC)));
        List<Map<String, Object>> cajas = new ArrayList<>(mensajes.size());
        for (Pendiente m : mensajes) {
            cajas.add(caja(m));
        }
        lote.put("mensajes", cajas);
        return lote;
    }

    private Map<String, Object> caja(Pendiente m) {
        try {
            return objectMapper.readValue(m.contratoJson(), new TypeReference<>() {});
        } catch (IOException e) {
            throw new IllegalStateException("La caja del mensaje " + m.discordId() + " no es JSON válido", e);
        }
    }

    private static final class Contador {
        int ok;
        int error;
        int reintento;
        int cambiaron;
    }
}
