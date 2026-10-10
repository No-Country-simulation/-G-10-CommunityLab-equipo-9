# T11 · Borrar el código que ya no se usa

| Dato | Valor |
|---|---|
| Objetivo | Que `main` no tenga código de diseños anteriores que confunda a quien lo lee (personas o asistentes de IA). DEC-145 |
| Tamaño | S (solo borrar y ajustar importaciones; **ningún cambio de comportamiento**) |
| Modelo recomendado | **Sonnet 5.5** |
| Depende de | La documentación de cierre (DEC-143), ya hecha en la rama de integración |
| Rama | `tarea/T11-limpieza-codigo`, desde `feature/integracion-arquitectura-3` (se retira al cerrar, DEC-144) |
| Lectura previa | [AGENTS.md](../../../AGENTS.md), [ARQUITECTURA.md](../../ARQUITECTURA.md) §8 y §10 y [ESTADO.md](../../ESTADO.md) §3 |

## 1. Qué queda igual

Ninguna puerta, ningún resultado y ningún comportamiento cambia. Si algo de la lista de abajo resulta usado, **no se borra**: se anota en el informe.

## 2. Alcance

1. **Borrar en `agents/orquestador/`** (💻 verificado el 2026-10-09: solo los usa el código viejo o `test_orquestador.py`):
   - `orquestador.py`, `adaptador.py` y `test_orquestador.py`;
   - `nodos/clasificador.py`, `nodos/consolidacion.py`, `nodos/descarte.py`, `nodos/filtro_ruido.py` y `nodos/invocador_mod.py`;
   - `aristas/` completa;
   - `clasificadores/generic_adapter.py`, `clasificadores/laya_adapter.py` y `clasificadores/laya_guardrail.py`, ajustando `clasificadores/__init__.py`;
   - `storage/` completa (el cliente de OCI viejo; la subida a OCI la hace Java).
2. **No borrar, porque se usan:**
   - `contratos.py` (lo importa el Agente FAQ: `tools/buscador.py`, `tools/reporte_faq.py` y `vectorstore/preguntas_store.py`);
   - `clasificadores/base.py` y `clasificadores/keyword_fallback.py` (los usa `etiquetador.py`), y `clasificadores/llm_models.py`;
   - `nodos/invocador_faq.py` (lo usan `api.py`, `grafo_v1.py` y `agent_mod/faq_semanal.py`).
3. **`config.py`:** quitar solo las variables que usaba únicamente el código borrado (por ejemplo, las del cliente de OCI viejo o la ruta del Agente-Mod viejo), comprobándolo con una búsqueda.
4. **Pruebas que importen módulos borrados** (por ejemplo, alguna de `tests/test_v1_procesar.py` que compruebe el diseño viejo): se adaptan o se quitan, explicando cuál y por qué en el informe.
5. **`requirements.txt` de la raíz:** borrarlo si ningún `Dockerfile`, `compose.yml` ni documento vigente lo usa (las imágenes usan `agents/requirements-ia.txt` y los `requirements.txt` de cada pieza).
6. **`agents/agent_faq/test_agente.py`** (un script interactivo que llama a Gemini): conservarlo si funciona con el agente actual; si no, borrarlo y decirlo en el informe.
7. **Comentarios que citan rutas movidas** a `docs/historico/`: en `backend-java/src/test/.../ModeloDatosTest.java` (`docs/tareas/T01-informe.md`) y `SubidaOciTest.java` (`CHAT_PRINCIPAL`).
8. **Documentación:** quitar el aviso de "código que ya no se usa" de [agents/orquestador/README.md](../../../agents/orquestador/README.md) y de [ARQUITECTURA.md](../../ARQUITECTURA.md) §10, marcar el punto 1 de [ESTADO.md](../../ESTADO.md) §3 como hecho y cerrar DEC-145 en [DECISIONES.md](../../DECISIONES.md).

## 3. Fuera de alcance

- Cambiar el historial interno de preguntas del Agente FAQ (`historial_preguntas.json`, `faiss_preguntas`): se sigue escribiendo y es un cambio de comportamiento (queda como mejora en ESTADO).
- Cualquier mejora o refactorización. Tocar `backend-java/` más allá de los dos comentarios.
- **No ejecutar `simulate_students.py`** ni encender un segundo bot.

## 4. Pruebas

| Comando | Debe dar |
|---|---|
| `python -m pytest agents/orquestador/tests -q` | Todas pasan (hoy son 79, menos las que se quiten por el punto 4) |
| `python -m pytest agents/bot_discord/tests -q`, `python -m pytest panel/tests -q` y, desde `ingestion/discord`, `python -m pytest -q` | Todas pasan, sin cambios |
| Las pruebas de Java ([OPERACION.md](../../OPERACION.md) §5) | 219 de 219 |
| `docker compose up -d --build ia` y `GET http://127.0.0.1:8000/health` | La imagen se construye, arranca y responde `ok` con `faq_listo: true` (comprueba que no quedó una importación rota) |
| Búsqueda final | Ningún archivo vigente importa ni nombra un módulo borrado |

## 5. Al terminar

- Informe `docs/historico/tareas/T11-informe.md` con la [plantilla](PLANTILLA_INFORME.md): qué se borró, qué se conservó y por qué, y la salida de las pruebas.
- Commits con un solo `-m` y `git push -u origin tarea/T11-limpieza-codigo`.
