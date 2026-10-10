package com.insightedulab.backend_java.controller;

import com.insightedulab.backend_java.curaduria.CuraduriaService;
import com.insightedulab.backend_java.curaduria.VistasPanel.DetalleBorrador;
import com.insightedulab.backend_java.curaduria.VistasPanel.ListaBorradores;
import com.insightedulab.backend_java.curaduria.VistasPanel.PedidoAprobar;
import com.insightedulab.backend_java.curaduria.VistasPanel.PedidoEditar;
import com.insightedulab.backend_java.curaduria.VistasPanel.PedidoRechazar;
import com.insightedulab.backend_java.seguridad.ApiKeyFilter;
import com.insightedulab.backend_java.seguridad.ClientePermitido;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * Puertas de los borradores para el panel de curaduría (T07, contrato docs/contratos/PANEL_JAVA_v1.md).
 * Solo las puede usar el cliente "panel" (ApiKeyFilter y, además, cada método: DEC-70).
 * Los cambios exigen la cabecera X-Usuario con el usuario que inició sesión en el panel.
 */
@RestController
@RequestMapping("/api/v1/borradores")
public class BorradorController {

    public static final String CABECERA_USUARIO = "X-Usuario";

    private final CuraduriaService curaduria;

    public BorradorController(CuraduriaService curaduria) {
        this.curaduria = curaduria;
    }

    @GetMapping
    public ListaBorradores listar(@RequestAttribute(name = ApiKeyFilter.ATRIBUTO_CLIENTE, required = false) String cliente,
                                  @RequestParam(required = false) String estado,
                                  @RequestParam(required = false) String tipo,
                                  @RequestParam(required = false) Integer limite) {
        ClientePermitido.exigir(ClientePermitido.PANEL, cliente);  // segunda capa, además del filtro
        return curaduria.listar(estado, tipo, limite);
    }

    @GetMapping("/{id}")
    public DetalleBorrador detalle(@RequestAttribute(name = ApiKeyFilter.ATRIBUTO_CLIENTE, required = false) String cliente,
                                   @PathVariable long id) {
        ClientePermitido.exigir(ClientePermitido.PANEL, cliente);
        return curaduria.detalle(id);
    }

    @PutMapping("/{id}")
    public DetalleBorrador editar(@RequestAttribute(name = ApiKeyFilter.ATRIBUTO_CLIENTE, required = false) String cliente,
                                  @RequestHeader(name = CABECERA_USUARIO, required = false) String usuario,
                                  @PathVariable long id,
                                  @RequestBody(required = false) PedidoEditar pedido) {
        ClientePermitido.exigir(ClientePermitido.PANEL, cliente);
        return curaduria.editar(id, usuario, pedido);
    }

    @PostMapping("/{id}/aprobar")
    public DetalleBorrador aprobar(@RequestAttribute(name = ApiKeyFilter.ATRIBUTO_CLIENTE, required = false) String cliente,
                                   @RequestHeader(name = CABECERA_USUARIO, required = false) String usuario,
                                   @PathVariable long id,
                                   @RequestBody(required = false) PedidoAprobar pedido) {
        ClientePermitido.exigir(ClientePermitido.PANEL, cliente);
        return curaduria.aprobar(id, usuario, pedido);
    }

    @PostMapping("/{id}/rechazar")
    public DetalleBorrador rechazar(@RequestAttribute(name = ApiKeyFilter.ATRIBUTO_CLIENTE, required = false) String cliente,
                                    @RequestHeader(name = CABECERA_USUARIO, required = false) String usuario,
                                    @PathVariable long id,
                                    @RequestBody(required = false) PedidoRechazar pedido) {
        ClientePermitido.exigir(ClientePermitido.PANEL, cliente);
        return curaduria.rechazar(id, usuario, pedido);
    }
}
