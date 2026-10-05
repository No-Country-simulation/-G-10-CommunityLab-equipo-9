package com.insightedulab.backend_java.dashboard;

import com.insightedulab.backend_java.dashboard.DashboardRepository.FilaSentimiento;
import com.insightedulab.backend_java.dashboard.VistasDashboard.Desercion;
import com.insightedulab.backend_java.dashboard.VistasDashboard.DudasSinResponder;
import com.insightedulab.backend_java.dashboard.VistasDashboard.Frustracion;
import com.insightedulab.backend_java.dashboard.VistasDashboard.Periodo;
import com.insightedulab.backend_java.dashboard.VistasDashboard.PuntoSentimiento;
import com.insightedulab.backend_java.dashboard.VistasDashboard.Sentimiento;
import com.insightedulab.backend_java.dashboard.VistasDashboard.Temas;
import com.insightedulab.backend_java.dashboard.VistasDashboard.Totales;
import com.insightedulab.backend_java.error.DatoInvalidoException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.DayOfWeek;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.temporal.ChronoUnit;
import java.time.temporal.TemporalAdjusters;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * El dashboard (T08, N5): Java calcula y el panel solo dibuja (DEC-123). No usa IA: todo sale de las
 * etiquetas que ya guardaron la clasificación (T04) y el bot (T05).
 */
@Service
public class DashboardService {

    /** Los 5 sentimientos del contrato Java ↔ IA (§4.2), en el orden en que se dibujan. */
    static final List<String> SENTIMIENTOS = List.of("MUY_POSITIVO", "POSITIVO", "NEUTRO", "NEGATIVO", "MUY_NEGATIVO");
    static final int DIAS_POR_DEFECTO = 30;
    static final int MAX_DIAS_PERIODO = 366;
    static final int DIAS_DESERCION = 14;      // DEC-119
    static final int HORAS_SIN_RESPONDER = 24;
    static final int MAX_DIAS_DESERCION = 365;
    static final int MAX_HORAS_SIN_RESPONDER = 24 * 90;
    static final int LIMITE_LISTAS = 200;

    private final DashboardRepository repo;
    private final ZoneId zona;
    private final Clock reloj;

    @Autowired
    public DashboardService(DashboardRepository repo, @Value("${dashboard.zona:America/Bogota}") String zona) {
        this(repo, ZoneId.of(zona), Clock.systemUTC());
    }

    DashboardService(DashboardRepository repo, ZoneId zona, Clock reloj) {
        this.repo = repo;
        this.zona = zona;
        this.reloj = reloj;
    }

    public Totales totales(LocalDate desde, LocalDate hasta) {
        Periodo p = periodo(desde, hasta);
        long[] t = repo.totales(inicio(p.desde()), fin(p.hasta()));
        return new Totales(p, t[0], t[1], t[2], t[3], t[4], t[5]);
    }

    public Sentimiento sentimiento(LocalDate desde, LocalDate hasta, String agrupar, boolean excluirOtro) {
        Periodo p = periodo(desde, hasta);
        boolean semana = esSemana(agrupar);
        List<FilaSentimiento> filas = repo.sentimiento(inicio(p.desde()), fin(p.hasta()), semana ? "week" : "day",
                zona.getId(), excluirOtro);

        // Todos los días (o lunes) del período, con los 5 sentimientos en 0: el gráfico no salta los vacíos
        Map<LocalDate, Map<String, Long>> serie = new LinkedHashMap<>();
        LocalDate primero = semana ? p.desde().with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY)) : p.desde();
        for (LocalDate d = primero; !d.isAfter(p.hasta()); d = d.plus(1, semana ? ChronoUnit.WEEKS : ChronoUnit.DAYS)) {
            Map<String, Long> ceros = new LinkedHashMap<>();
            SENTIMIENTOS.forEach(s -> ceros.put(s, 0L));
            serie.put(d, ceros);
        }
        for (FilaSentimiento f : filas) {
            Map<String, Long> punto = serie.get(f.inicio());
            if (punto != null && punto.containsKey(f.sentimiento())) {
                punto.put(f.sentimiento(), f.cantidad());
            }
        }
        List<PuntoSentimiento> puntos = serie.entrySet().stream()
                .map(e -> new PuntoSentimiento(e.getKey(), e.getValue())).toList();
        return new Sentimiento(p, semana ? "semana" : "dia", excluirOtro, puntos);
    }

    public Temas temas(LocalDate desde, LocalDate hasta, boolean excluirOtro) {
        Periodo p = periodo(desde, hasta);
        long dias = ChronoUnit.DAYS.between(p.desde(), p.hasta()) + 1;
        Periodo anterior = new Periodo(p.desde().minusDays(dias), p.desde().minusDays(1));
        return new Temas(p, anterior, excluirOtro,
                repo.temas(inicio(anterior.desde()), inicio(p.desde()), fin(p.hasta()), excluirOtro));
    }

    public Desercion desercion(Integer dias) {
        int d = rango("dias", dias, DIAS_DESERCION, 1, MAX_DIAS_DESERCION);
        return new Desercion(d, repo.desercion(d, LIMITE_LISTAS));
    }

    public Frustracion frustracion(LocalDate desde, LocalDate hasta) {
        Periodo p = periodo(desde, hasta);
        return new Frustracion(p, repo.frustracion(inicio(p.desde()), fin(p.hasta()), LIMITE_LISTAS));
    }

    public DudasSinResponder dudasSinResponder(LocalDate desde, LocalDate hasta, Integer horas, boolean excluirOtro) {
        Periodo p = periodo(desde, hasta);
        int h = rango("horas", horas, HORAS_SIN_RESPONDER, 0, MAX_HORAS_SIN_RESPONDER);
        DashboardRepository.Dudas r = repo.dudasSinResponder(inicio(p.desde()), fin(p.hasta()), h, excluirOtro,
                LIMITE_LISTAS);
        return new DudasSinResponder(p, h, excluirOtro, r.total(), r.dudas());
    }

    // ── Validaciones ──

    /** Sin fechas: los últimos 30 días hasta hoy. Si no, 422 cuando el período está al revés o es muy largo. */
    Periodo periodo(LocalDate desde, LocalDate hasta) {
        LocalDate h = hasta != null ? hasta : LocalDate.now(reloj.withZone(zona));
        LocalDate d = desde != null ? desde : h.minusDays(DIAS_POR_DEFECTO - 1);
        if (d.isAfter(h)) {
            throw new DatoInvalidoException("desde", "La fecha 'desde' es posterior a 'hasta'.");
        }
        if (ChronoUnit.DAYS.between(d, h) + 1 > MAX_DIAS_PERIODO) {
            throw new DatoInvalidoException("hasta", "El período no puede tener más de " + MAX_DIAS_PERIODO + " días.");
        }
        return new Periodo(d, h);
    }

    private static boolean esSemana(String agrupar) {
        if (agrupar == null || agrupar.isBlank() || agrupar.equals("dia")) {
            return false;
        }
        if (agrupar.equals("semana")) {
            return true;
        }
        throw new DatoInvalidoException("agrupar", "Tiene que ser 'dia' o 'semana'.");
    }

    private static int rango(String campo, Integer valor, int porDefecto, int minimo, int maximo) {
        int v = valor == null ? porDefecto : valor;
        if (v < minimo || v > maximo) {
            throw new DatoInvalidoException(campo, "Tiene que estar entre " + minimo + " y " + maximo + ".");
        }
        return v;
    }

    /** El primer instante del día en la zona del dashboard. */
    private Instant inicio(LocalDate dia) {
        return dia.atStartOfDay(zona).toInstant();
    }

    /** El fin del día (exclusivo): el primer instante del día siguiente. */
    private Instant fin(LocalDate dia) {
        return dia.plusDays(1).atStartOfDay(zona).toInstant();
    }
}
