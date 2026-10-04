"""
Cliente del panel para la API Java (contrato Panel ↔ Java v1, docs/contratos/PANEL_JAVA_v1.md).

El panel habla SOLO con Java (DEC-112): nunca con la base ni con la IA. Las llamadas salen del servidor de
Streamlit, no del navegador (por eso Java no necesita CORS, S6).
- Cada pedido lleva X-Api-Key (la clave del cliente "panel", DEC-70).
- Cada cambio lleva X-Usuario: quién inició sesión. Java lo guarda como aprobado_por o rechazado_por.
- Los POST y PUT van siempre con cuerpo JSON (aunque sea {}): así llevan Content-Length, que Java exige.
"""
from __future__ import annotations

import os

import httpx

TIEMPO_S = 15.0


class ErrorJava(Exception):
    """Java respondió con un error (o no respondió). estado es el código HTTP; 0 si no hubo conexión."""

    def __init__(self, estado: int, codigo: str, mensaje: str, campo: str | None = None):
        super().__init__(mensaje)
        self.estado = estado
        self.codigo = codigo
        self.mensaje = mensaje
        self.campo = campo


class ClienteJava:

    def __init__(self, url: str, clave: str, transport: httpx.BaseTransport | None = None,
                 tiempo_s: float = TIEMPO_S):
        self._http = httpx.Client(base_url=url.rstrip("/"), timeout=tiempo_s, transport=transport,
                                  headers={"X-Api-Key": clave, "Accept": "application/json"})

    # ── Borradores ──

    def listar_borradores(self, estado: str = "PENDIENTE", tipo: str | None = None, limite: int = 100) -> list[dict]:
        params = {"estado": estado, "limite": limite}
        if tipo:
            params["tipo"] = tipo
        return self._pedir("GET", "/api/v1/borradores", params=params)["borradores"]

    def detalle(self, borrador_id: int) -> dict:
        return self._pedir("GET", f"/api/v1/borradores/{int(borrador_id)}")

    def editar(self, borrador_id: int, usuario: str, texto_final: str) -> dict:
        return self._pedir("PUT", f"/api/v1/borradores/{int(borrador_id)}", usuario=usuario,
                           cuerpo={"textoFinal": texto_final})

    def aprobar(self, borrador_id: int, usuario: str, consentimiento: bool, tiempo_seg: int,
                texto_final: str | None = None) -> dict:
        cuerpo = {"consentimiento": bool(consentimiento), "tiempoCuraduriaSeg": int(tiempo_seg)}
        if texto_final is not None:
            cuerpo["textoFinal"] = texto_final
        return self._pedir("POST", f"/api/v1/borradores/{int(borrador_id)}/aprobar", usuario=usuario, cuerpo=cuerpo)

    def rechazar(self, borrador_id: int, usuario: str, motivo: str | None, tiempo_seg: int | None) -> dict:
        cuerpo: dict = {}
        if motivo:
            cuerpo["motivo"] = motivo
        if tiempo_seg is not None:
            cuerpo["tiempoCuraduriaSeg"] = int(tiempo_seg)
        return self._pedir("POST", f"/api/v1/borradores/{int(borrador_id)}/rechazar", usuario=usuario, cuerpo=cuerpo)

    # ── Errores (DEC-111) ──

    def errores(self) -> dict:
        return self._pedir("GET", "/api/v1/errores")

    def reintentar(self, etapa: str, mensaje_id: int, usuario: str) -> dict:
        if etapa not in ("clasificacion", "generacion"):
            raise ValueError(f"Etapa desconocida: {etapa}")
        return self._pedir("POST", f"/api/v1/errores/{etapa}/{int(mensaje_id)}/reintentar", usuario=usuario, cuerpo={})

    # ── Común ──

    def _pedir(self, metodo: str, ruta: str, usuario: str | None = None, cuerpo: dict | None = None,
               params: dict | None = None) -> dict:
        cabeceras = {"X-Usuario": usuario} if usuario is not None else None
        try:
            r = self._http.request(metodo, ruta, params=params, json=cuerpo, headers=cabeceras)
        except httpx.HTTPError:
            # Sin detalles: la URL interna o el error de red no le sirven a quien usa el panel
            raise ErrorJava(0, "SIN_CONEXION", "No se pudo conectar con la API Java. ¿Está encendida?") from None
        if r.is_success:
            return r.json()
        raise _error_de(r)


def _error_de(r: httpx.Response) -> ErrorJava:
    """El ErrorApi de Java (codigo, mensaje, errores) como ErrorJava."""
    try:
        cuerpo = r.json()
        errores = cuerpo.get("errores") or []
        campo = errores[0].get("campo") if errores else None
        return ErrorJava(r.status_code, cuerpo.get("codigo", "ERROR"), cuerpo.get("mensaje", "Error de la API Java."),
                         campo)
    except (ValueError, AttributeError):
        return ErrorJava(r.status_code, "ERROR", f"La API Java respondió HTTP {r.status_code}.")


def desde_entorno() -> ClienteJava | None:
    """El cliente con PANEL_JAVA_URL y API_KEY_PANEL, o None si falta la clave."""
    clave = os.environ.get("API_KEY_PANEL", "").strip()
    if not clave:
        return None
    return ClienteJava(os.environ.get("PANEL_JAVA_URL", "http://localhost:8008"), clave)
