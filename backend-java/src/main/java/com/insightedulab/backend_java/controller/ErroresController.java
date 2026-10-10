package com.insightedulab.backend_java.controller;

import com.insightedulab.backend_java.curaduria.CuraduriaService;
import com.insightedulab.backend_java.curaduria.VistasPanel.ListaErrores;
import com.insightedulab.backend_java.curaduria.VistasPanel.Reintento;
import com.insightedulab.backend_java.seguridad.ApiKeyFilter;
import com.insightedulab.backend_java.seguridad.ClientePermitido;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Lo que quedó en ERROR y el botón de reintentar del panel (T07, DEC-111).
 * Solo lo puede usar el cliente "panel" (DEC-70). Reintentar exige X-Usuario.
 */
@RestController
@RequestMapping("/api/v1/errores")
public class ErroresController {

    private final CuraduriaService curaduria;

    public ErroresController(CuraduriaService curaduria) {
        this.curaduria = curaduria;
    }

    @GetMapping
    public ListaErrores listar(@RequestAttribute(name = ApiKeyFilter.ATRIBUTO_CLIENTE, required = false) String cliente) {
        ClientePermitido.exigir(ClientePermitido.PANEL, cliente);  // segunda capa, además del filtro
        return curaduria.errores();
    }

    @PostMapping("/clasificacion/{mensajeId}/reintentar")
    public Reintento reintentarClasificacion(
            @RequestAttribute(name = ApiKeyFilter.ATRIBUTO_CLIENTE, required = false) String cliente,
            @RequestHeader(name = BorradorController.CABECERA_USUARIO, required = false) String usuario,
            @PathVariable long mensajeId) {
        ClientePermitido.exigir(ClientePermitido.PANEL, cliente);
        return curaduria.reintentarClasificacion(mensajeId, usuario);
    }

    @PostMapping("/generacion/{mensajeId}/reintentar")
    public Reintento reintentarGeneracion(
            @RequestAttribute(name = ApiKeyFilter.ATRIBUTO_CLIENTE, required = false) String cliente,
            @RequestHeader(name = BorradorController.CABECERA_USUARIO, required = false) String usuario,
            @PathVariable long mensajeId) {
        ClientePermitido.exigir(ClientePermitido.PANEL, cliente);
        return curaduria.reintentarGeneracion(mensajeId, usuario);
    }
}
