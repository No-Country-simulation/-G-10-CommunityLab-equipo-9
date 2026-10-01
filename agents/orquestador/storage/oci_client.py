"""
Cliente de OCI Object Storage.

Sube paquetes, reportes y logs al bucket configurado.
Si las credenciales no están disponibles, falla silenciosamente.
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

from ..config import (
    OCI_BUCKET, OCI_NAMESPACE, OCI_CONFIG_PATH,
    OCI_PREFIJO_ACTIVOS, OCI_PREFIJO_REPORTES, OCI_PREFIJO_LOGS,
)


class OCIClient:
    """Wrapper simple para subir JSONs a OCI Object Storage."""

    def __init__(self):
        self.bucket = OCI_BUCKET
        self.namespace = OCI_NAMESPACE
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        """Inicializa el cliente de OCI (import diferido)."""
        try:
            import oci

            config_path = Path(OCI_CONFIG_PATH)
            if not config_path.exists():
                print(f"[OCIClient] Config no encontrada: {config_path}")
                return

            config = oci.config.from_file(str(config_path))
            self._client = oci.object_storage.ObjectStorageClient(config)

            if not self.namespace:
                self.namespace = self._client.get_namespace().data

            print("[OCIClient] Cliente OCI inicializado.")
        except Exception as e:
            print(f"[OCIClient] No se pudo inicializar: {e}")
            self._client = None

    def _fecha_actual(self) -> str:
        return datetime.utcnow().strftime("%Y-%m-%d")

    def _subir_json(self, ruta_objeto: str, data: dict) -> bool:
        """Sube un dict como JSON al bucket."""
        if not self._client:
            print(f"[OCIClient] Cliente no disponible. Skip: {ruta_objeto}")
            return False

        try:
            contenido = json.dumps(data, ensure_ascii=False, indent=2, default=str)
            self._client.put_object(
                namespace_name=self.namespace,
                bucket_name=self.bucket,
                object_name=ruta_objeto,
                put_object_body=contenido.encode("utf-8"),
                content_type="application/json",
            )
            print(f"[OCIClient] Subido: {ruta_objeto}")
            return True
        except Exception as e:
            print(f"[OCIClient] Error subiendo {ruta_objeto}: {e}")
            return False

    def subir_paquete(self, lote_id: str, paquete: dict) -> bool:
        ruta = f"{OCI_PREFIJO_ACTIVOS}/{self._fecha_actual()}/{lote_id}/paquete-distribucion.json"
        return self._subir_json(ruta, paquete)

    def subir_log(self, lote_id: str, log: dict) -> bool:
        ruta = f"{OCI_PREFIJO_LOGS}/{self._fecha_actual()}/{lote_id}/log_ejecucion.json"
        return self._subir_json(ruta, log)

    def subir_reporte(self, lote_id: str, nombre: str, reporte: dict) -> bool:
        ruta = f"{OCI_PREFIJO_REPORTES}/{self._fecha_actual()}/{lote_id}/{nombre}.json"
        return self._subir_json(ruta, reporte)