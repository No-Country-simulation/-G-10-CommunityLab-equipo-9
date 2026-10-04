package com.insightedulab.backend_java.service;

import com.fasterxml.jackson.databind.JsonMappingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightedulab.backend_java.dto.lote.LoteEntrada;
import com.insightedulab.backend_java.dto.lote.MensajeEntrada;
import com.insightedulab.backend_java.dto.lote.ReciboLote;
import com.insightedulab.backend_java.error.ContratoInvalidoException;
import com.insightedulab.backend_java.error.ErrorApi.ErrorCampo;
import com.insightedulab.backend_java.model.LoteRecibido;
import com.insightedulab.backend_java.model.enums.AutorRol;
import com.insightedulab.backend_java.model.enums.AutorTipo;
import com.insightedulab.backend_java.model.enums.ModoLote;
import com.insightedulab.backend_java.repository.LoteRecibidoRepository;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository;
import com.insightedulab.backend_java.repository.MensajeUpsertRepository.DatosMensaje;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Recibe un lote del contrato v1 (POST /api/v1/lotes):
 * <ol>
 *   <li>valida todo el lote antes de escribir nada (422 con cada campo que falla);</li>
 *   <li>si el loteId ya se recibió, devuelve el mismo recibo (reenviar es seguro);</li>
 *   <li>si no, en UNA transacción: fila en lotes_recibidos + upsert de cada mensaje (F1, F2, F3).</li>
 * </ol>
 */
@Service
public class LoteService {

    private static final Logger log = LoggerFactory.getLogger(LoteService.class);

    private final Validator validator;
    private final ObjectMapper objectMapper;
    private final MensajeUpsertRepository upsertRepo;
    private final LoteRecibidoRepository loteRepo;
    private final TransactionTemplate transaccion;

    public LoteService(Validator validator, ObjectMapper objectMapper, MensajeUpsertRepository upsertRepo,
                       LoteRecibidoRepository loteRepo, TransactionTemplate transaccion) {
        this.validator = validator;
        this.objectMapper = objectMapper;
        this.upsertRepo = upsertRepo;
        this.loteRepo = loteRepo;
        this.transaccion = transaccion;
    }

    public ReciboLote recibir(LoteEntrada lote) {
        List<DatosMensaje> mensajes = validar(lote);

        Optional<LoteRecibido> anterior = loteRepo.findByLoteId(lote.loteId());
        if (anterior.isPresent()) {
            log.info("Lote {} ya recibido: se devuelve el mismo recibo", lote.loteId());
            return ReciboLote.de(anterior.get(), true);
        }
        try {
            return transaccion.execute(estado -> guardar(lote, mensajes));
        } catch (DataIntegrityViolationException e) {
            // Otro pedido guardó el mismo loteId al mismo tiempo: esta transacción se deshizo entera
            return loteRepo.findByLoteId(lote.loteId())
                    .map(l -> ReciboLote.de(l, true))
                    .orElseThrow(() -> e);
        }
    }

    private ReciboLote guardar(LoteEntrada lote, List<DatosMensaje> mensajes) {
        // La fila del lote va PRIMERO: su loteId único hace esperar a un envío simultáneo del mismo lote,
        // que después falla y no repite los upsert.
        LoteRecibido fila = loteRepo.saveAndFlush(LoteRecibido.builder()
                .loteId(lote.loteId())
                .modo(ModoLote.valueOf(lote.modo()))
                .versionContrato(lote.versionContrato())
                // PostgreSQL guarda microsegundos: así el recibo repetido es idéntico al primero
                .recibidoEn(Instant.now().truncatedTo(ChronoUnit.MICROS))
                .total(mensajes.size())
                .build());

        int nuevos = 0;
        int actualizados = 0;
        for (DatosMensaje m : mensajes) {
            switch (upsertRepo.upsert(m)) {
                case NUEVO -> nuevos++;
                case ACTUALIZADO -> actualizados++;
                case SIN_CAMBIOS -> { }
            }
        }
        fila.setNuevos(nuevos);
        fila.setActualizados(actualizados);
        log.info("Lote {} guardado: total {}, nuevos {}, actualizados {}", lote.loteId(), mensajes.size(), nuevos, actualizados);
        return ReciboLote.de(fila, false);
    }

    /** Todo el lote, de una vez: o pasa entero o se responde 422 con todos los errores juntos. */
    private List<DatosMensaje> validar(LoteEntrada lote) {
        List<ErrorCampo> errores = new ArrayList<>(violaciones("", validator.validate(lote)));
        List<DatosMensaje> datos = new ArrayList<>();

        List<Map<String, Object>> cajas = lote.mensajes() == null ? List.of() : lote.mensajes();
        if (cajas.size() > LoteEntrada.MAX_MENSAJES) {
            throw new ContratoInvalidoException(errores);  // ya trae el error del tope: no se revisa uno por uno
        }
        for (int i = 0; i < cajas.size(); i++) {
            String prefijo = "mensajes[" + i + "]";
            Map<String, Object> caja = cajas.get(i);
            if (caja == null) {
                errores.add(new ErrorCampo(prefijo, "debe ser un objeto"));
                continue;
            }
            MensajeEntrada m;
            try {
                m = objectMapper.convertValue(caja, MensajeEntrada.class);
            } catch (IllegalArgumentException e) {
                errores.add(new ErrorCampo(prefijo + rutaDe(e), "tiene un tipo de dato incorrecto"));
                continue;
            }
            List<ErrorCampo> delMensaje = violaciones(prefijo + ".", validator.validate(m));
            if (!delMensaje.isEmpty()) {
                errores.addAll(delMensaje);
                continue;
            }
            Instant fecha;
            try {
                fecha = Instant.parse(m.fecha());  // el patrón no descarta un mes 13
            } catch (DateTimeParseException e) {
                errores.add(new ErrorCampo(prefijo + ".fecha", "no es una fecha válida"));
                continue;
            }
            datos.add(new DatosMensaje(
                    m.id(), m.canal().id(), m.autor().id(),
                    AutorTipo.valueOf(m.autor().tipo()), AutorRol.valueOf(m.autor().rol()),
                    m.esSimulado(), fecha, m.respondeA(), m.textoOriginal(),
                    caja, lote.versionContrato()));
        }
        if (!errores.isEmpty()) {
            throw new ContratoInvalidoException(errores);
        }
        return datos;
    }

    private static <T> List<ErrorCampo> violaciones(String prefijo, java.util.Set<ConstraintViolation<T>> violaciones) {
        return violaciones.stream()
                .map(v -> new ErrorCampo(prefijo + v.getPropertyPath(), v.getMessage()))
                .sorted(Comparator.comparing(ErrorCampo::campo))
                .toList();
    }

    /** ".autor.tipo" a partir del error de Jackson, sin incluir el valor recibido. */
    private static String rutaDe(IllegalArgumentException e) {
        if (!(e.getCause() instanceof JsonMappingException jme)) {
            return "";
        }
        StringBuilder ruta = new StringBuilder();
        for (JsonMappingException.Reference ref : jme.getPath()) {
            ruta.append(ref.getFieldName() != null ? "." + ref.getFieldName() : "[" + ref.getIndex() + "]");
        }
        return ruta.toString();
    }
}
