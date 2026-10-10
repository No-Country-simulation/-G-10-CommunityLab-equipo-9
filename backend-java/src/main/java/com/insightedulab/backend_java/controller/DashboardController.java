package com.insightedulab.backend_java.controller;

import com.insightedulab.backend_java.dashboard.DashboardService;
import com.insightedulab.backend_java.dashboard.VistasDashboard.Desercion;
import com.insightedulab.backend_java.dashboard.VistasDashboard.DudasSinResponder;
import com.insightedulab.backend_java.dashboard.VistasDashboard.Frustracion;
import com.insightedulab.backend_java.dashboard.VistasDashboard.Sentimiento;
import com.insightedulab.backend_java.dashboard.VistasDashboard.Temas;
import com.insightedulab.backend_java.dashboard.VistasDashboard.Totales;
import com.insightedulab.backend_java.seguridad.ApiKeyFilter;
import com.insightedulab.backend_java.seguridad.ClientePermitido;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;

/**
 * Puertas de solo lectura del dashboard (T08, DEC-122, PANEL_JAVA_v1.md §7).
 * Solo las puede usar el cliente "panel" (ApiKeyFilter y, además, cada método: DEC-70).
 * El período va en días (desde y hasta incluidos, AAAA-MM-DD); sin fechas, los últimos 30 días.
 */
@RestController
@RequestMapping("/api/v1/dashboard")
public class DashboardController {

    private final DashboardService dashboard;

    public DashboardController(DashboardService dashboard) {
        this.dashboard = dashboard;
    }

    @GetMapping("/totales")
    public Totales totales(@RequestAttribute(name = ApiKeyFilter.ATRIBUTO_CLIENTE, required = false) String cliente,
                           @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate desde,
                           @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate hasta) {
        ClientePermitido.exigir(ClientePermitido.PANEL, cliente);  // segunda capa, además del filtro
        return dashboard.totales(desde, hasta);
    }

    @GetMapping("/sentimiento")
    public Sentimiento sentimiento(
            @RequestAttribute(name = ApiKeyFilter.ATRIBUTO_CLIENTE, required = false) String cliente,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate desde,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate hasta,
            @RequestParam(required = false) String agrupar,
            @RequestParam(defaultValue = "false") boolean excluirOtro) {
        ClientePermitido.exigir(ClientePermitido.PANEL, cliente);
        return dashboard.sentimiento(desde, hasta, agrupar, excluirOtro);
    }

    @GetMapping("/temas")
    public Temas temas(@RequestAttribute(name = ApiKeyFilter.ATRIBUTO_CLIENTE, required = false) String cliente,
                       @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate desde,
                       @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate hasta,
                       @RequestParam(defaultValue = "false") boolean excluirOtro) {
        ClientePermitido.exigir(ClientePermitido.PANEL, cliente);
        return dashboard.temas(desde, hasta, excluirOtro);
    }

    @GetMapping("/desercion")
    public Desercion desercion(@RequestAttribute(name = ApiKeyFilter.ATRIBUTO_CLIENTE, required = false) String cliente,
                               @RequestParam(required = false) Integer dias) {
        ClientePermitido.exigir(ClientePermitido.PANEL, cliente);
        return dashboard.desercion(dias);
    }

    @GetMapping("/frustracion")
    public Frustracion frustracion(
            @RequestAttribute(name = ApiKeyFilter.ATRIBUTO_CLIENTE, required = false) String cliente,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate desde,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate hasta) {
        ClientePermitido.exigir(ClientePermitido.PANEL, cliente);
        return dashboard.frustracion(desde, hasta);
    }

    @GetMapping("/dudas-sin-responder")
    public DudasSinResponder dudasSinResponder(
            @RequestAttribute(name = ApiKeyFilter.ATRIBUTO_CLIENTE, required = false) String cliente,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate desde,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate hasta,
            @RequestParam(required = false) Integer horas,
            @RequestParam(defaultValue = "false") boolean excluirOtro) {
        ClientePermitido.exigir(ClientePermitido.PANEL, cliente);
        return dashboard.dudasSinResponder(desde, hasta, horas, excluirOtro);
    }
}
