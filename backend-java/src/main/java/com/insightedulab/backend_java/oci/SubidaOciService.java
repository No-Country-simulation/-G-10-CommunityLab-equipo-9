package com.insightedulab.backend_java.oci;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightedulab.backend_java.oci.OciProperties.EstadoPar;
import com.insightedulab.backend_java.oci.SubidaOciRepository.Subida;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Sube en segundo plano los borradores a OCI (T09, N7, DEC-127):
 * <ol>
 *   <li>Encola las subidas que faltan: generados/ para todo borrador y aprobados/ solo para los APROBADOS (F11).</li>
 *   <li>Reserva una tanda (SKIP LOCKED + reservada_hasta).</li>
 *   <li>Por cada una, arma el JSON con Jackson y hace el PUT, sin transacción abierta.</li>
 *   <li>Anota el resultado con una guarda: si falla suma un intento y, al máximo, queda en ERROR.</li>
 * </ol>
 * Generar y aprobar no esperan a esta tarea: si OCI está caído, siguen funcionando y las subidas se reintentan.
 * El registro lleva solo números, nombres de objeto y códigos HTTP: nunca la PAR (una credencial) ni textos (S11).
 */
@Service
public class SubidaOciService {

    private static final Logger log = LoggerFactory.getLogger(SubidaOciService.class);

    /** Lo que pasó en una tanda; va al registro. */
    public record Resumen(int tomadas, int subidas, int reintento, int error, long duracionMs) {
        static final Resumen VACIO = new Resumen(0, 0, 0, 0, 0);
    }

    private final SubidaOciRepository repo;
    private final OciClient cliente;
    private final ObjectMapper objectMapper;
    private final OciProperties propiedades;
    private final AtomicBoolean avisado = new AtomicBoolean();

    public SubidaOciService(SubidaOciRepository repo, OciClient cliente, ObjectMapper objectMapper,
                            OciProperties propiedades) {
        this.repo = repo;
        this.cliente = cliente;
        this.objectMapper = objectMapper;
        this.propiedades = propiedades;
    }

    /**
     * true si hay una PAR con la forma de una PAR de bucket. Si no, lo avisa en el registro UNA sola vez
     * (sin mostrar la PAR): sin PAR no es un error de cada borrador, es una elección o un descuido de configuración.
     */
    public boolean listo() {
        EstadoPar estado = propiedades.estadoPar();
        if (estado == EstadoPar.LISTA) {
            return true;
        }
        if (avisado.compareAndSet(false, true)) {
            if (estado == EstadoPar.SIN_PAR) {
                log.warn("OCI: no hay URL PAR (OCI_PAR_URL está vacía); no se sube nada hasta que se configure");
            } else {
                log.error("OCI: OCI_PAR_URL no parece una PAR de bucket (tiene que empezar con https://objectstorage. "
                        + "y terminar en /o/); no se sube nada hasta que se corrija");
            }
        }
        return false;
    }

    public Resumen procesarTanda() {
        if (!listo()) {
            return Resumen.VACIO;
        }
        long inicio = System.nanoTime();
        repo.encolar();
        List<Subida> tomadas = repo.reservar(propiedades.tanda(), propiedades.reservaSegundos());
        Contador c = new Contador();
        for (Subida s : tomadas) {
            subir(s, c);
        }
        return new Resumen(tomadas.size(), c.subidas, c.reintento, c.error, (System.nanoTime() - inicio) / 1_000_000);
    }

    private void subir(Subida s, Contador c) {
        ArchivoOci archivo = repo.borrador(s.borradorId());
        if (archivo == null) {
            repo.errorDefinitivo(s.id(), "El borrador ya no existe.");
            c.error++;
            return;
        }
        if (SubidaOciRepository.APROBADOS.equals(s.carpeta()) && !"APROBADO".equals(archivo.estado())) {
            // F11: no debería pasar (solo se encolan los APROBADOS), pero un pendiente o un rechazado nunca va a aprobados/
            log.error("OCI: el borrador {} está {} y no va a aprobados/", archivo.id(), archivo.estado());
            repo.errorDefinitivo(s.id(), "El borrador no está APROBADO (F11).");
            c.error++;
            return;
        }

        String objeto = nombreDelObjeto(s.carpeta(), archivo);
        byte[] json;
        try {
            // Primero el texto y luego UTF-8: si Jackson escribiera directo los bytes, cada emoji saldría como
            // 🎉 (válido, pero ilegible al abrir el archivo en la consola de Oracle)
            json = objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(archivo)
                    .getBytes(StandardCharsets.UTF_8);
        } catch (JsonProcessingException e) {
            // No debería pasar con este objeto; se cuenta como intento para no repetirlo sin fin
            registrarFallo(s, objeto, "No se pudo armar el JSON.", c);
            return;
        }

        try {
            cliente.subir(objeto, json);
        } catch (OciException e) {
            registrarFallo(s, objeto, e.getMessage(), c);
            return;
        } catch (RuntimeException e) {
            // Solo la clase: el mensaje de una excepción desconocida podría llevar la URL PAR
            registrarFallo(s, objeto, "Falló la subida: " + e.getClass().getSimpleName() + ".", c);
            return;
        }

        if (repo.subido(s.id(), objeto)) {
            c.subidas++;
        } else {
            // Otra ejecución se adelantó (la reserva venció mientras subíamos): el PUT repetido deja el mismo archivo
            log.info("OCI: {} ya estaba anotado por otra ejecución", objeto);
        }
    }

    private void registrarFallo(Subida s, String objeto, String motivo, Contador c) {
        String estado = repo.fallo(s.id(), motivo, propiedades.maxIntentos(), propiedades.esperaReintentoSegundos());
        if (estado == null) {
            return;  // otra ejecución ya la resolvió
        }
        if ("ERROR".equals(estado)) {
            log.error("OCI: no se pudo subir {} y se agotaron los intentos ({})", objeto, motivo);
            c.error++;
        } else {
            log.warn("OCI: no se pudo subir {}; se reintenta ({})", objeto, motivo);
            c.reintento++;
        }
    }

    /**
     * Estable y legible: carpeta / tipo / fecha / borrador-id.json. La fecha es la de cuando se creó el borrador
     * (generados/) o se aprobó (aprobados/), en la zona de oci.zona. Si se repite la subida, es el mismo nombre.
     */
    String nombreDelObjeto(String carpeta, ArchivoOci archivo) {
        var instante = SubidaOciRepository.APROBADOS.equals(carpeta) && archivo.aprobadoEn() != null
                ? archivo.aprobadoEn() : archivo.creadoEn();
        LocalDate fecha = LocalDate.ofInstant(instante, propiedades.zonaHoraria());
        return carpeta + "/" + archivo.tipo() + "/" + fecha + "/borrador-" + archivo.id() + ".json";
    }

    private static final class Contador {
        int subidas;
        int reintento;
        int error;
    }
}
