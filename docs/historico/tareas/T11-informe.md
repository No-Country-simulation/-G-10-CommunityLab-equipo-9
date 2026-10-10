# Informe de la tarea T11 — Borrar el código que ya no se usa

| Dato | Valor |
|---|---|
| Fecha | 2026-10-10 |
| Modelo de Claude usado | Opus 5.5 (`claude-opus-5-5`); la ficha recomendaba Sonnet 5.5 |
| Rama | `tarea/T11-limpieza-codigo`, desde `feature/integracion-arquitectura-3` (`9bbb93a`) |
| Commits | Los da Harrison al cerrar (sección 7): `refactor(ia): borrar el orquestador viejo, sus variables y el requirements.txt de la raiz (T11)` y `docs: informe de T11 y cierre de DEC-145 y DEC-146` |

## 1. Resumen

Se borraron 15 archivos del diseño anterior de `agents/orquestador/` y el `requirements.txt` de la raíz, más las variables de `config.py` que nadie usaba (≈1290 líneas menos). **Ningún comportamiento cambió**: las cuatro suites de Python dan los mismos números que antes (79 · 22 · 51 · 36), la imagen `ia` se reconstruyó y responde `faq_listo: true`, y Java pasa 219 de 219. No se quitó ni se adaptó ninguna prueba.

## 2. Criterios de terminado

| Criterio (ficha §4) | Estado | Evidencia |
|---|---|---|
| `pytest agents/orquestador/tests`: todas pasan | ✅ | 🧪 79 passed antes y 79 passed después. `test_orquestador.py` estaba fuera de `tests/`, así que nunca contaba en las 79 |
| Bot, panel e ingesta: todas pasan, sin cambios | ✅ | 🧪 22 · 51 · 36 antes y después |
| Pruebas de Java: 219 de 219 | ✅ | 🧪 219 tests, 0 fallos, 0 errores (§4). Solo cambiaron dos comentarios de prueba |
| `docker compose up -d --build ia` y `/health` | ✅ | 🧪 Imagen construida; `{"status":"ok","service":"orquestador","port":8000,"faq_listo":true}`; registro: `Application startup complete` y `Agente FAQ precargado`, sin errores ni `ImportError` |
| Búsqueda final: ningún archivo vigente importa ni nombra un módulo borrado | ✅ | 🧪 `grep` de todos los nombres borrados (módulos, clases, funciones y variables) fuera de `docs/historico/`: solo quedan las menciones que **cuentan** que se borraron (README del orquestador, DEC-69, DEC-145, DEC-146) |

### Qué se borró

| Archivo o carpeta | Comprobación (💻 `grep` de importaciones en todo el repositorio) |
|---|---|
| `orquestador.py`, `adaptador.py`, `test_orquestador.py` | Solo se importaban entre ellos (`test_orquestador.py` → `orquestador.py` y `adaptador.py`) |
| `nodos/clasificador.py`, `consolidacion.py`, `descarte.py`, `filtro_ruido.py`, `invocador_mod.py` | Solo los importaba `orquestador.py` |
| `aristas/` completa | Solo la importaba `orquestador.py` |
| `clasificadores/generic_adapter.py`, `laya_adapter.py`, `laya_guardrail.py` | Solo los usaban `nodos/clasificador.py` y `clasificadores/__init__.py` (que se ajustó). 🔎 `laya_adapter.py` ya estaba roto: importaba `LAYA_CONFIDENCE_THRESHOLD`, que no existía en `config.py` |
| `storage/` completa (cliente de OCI viejo) | Solo la usaba `nodos/consolidacion.py`. La subida a OCI la hace Java (T09) |
| `requirements.txt` de la raíz | Ningún `Dockerfile` ni `compose.yml` lo usa (la IA usa `agents/requirements-ia.txt`; bot y panel, el suyo). El `pip install -r requirements.txt` del README §8.3 es el de `ingestion/discord`. Traía librerías de diseños viejos (`laya`, `oci`, `langchain-oci`, `chromadb`, `discord.py`) |

### Variables quitadas de `agents/orquestador/config.py`

Para recuperar la versión anterior: `git show 9bbb93a:agents/orquestador/config.py`.

| Grupo | Variables | Quién las usaba |
|---|---|---|
| **A** (ficha §2.3) | `LAYA_ENABLED`, `LAYA_MODEL`, `ORQ_SUBAGENTE_MOD_PATH`, `MIN_LONGITUD_CONTENIDO`, `PATRON_COMANDOS`, `MAX_REINTENTOS_CLASIFICACION`, `OCI_BUCKET`, `OCI_NAMESPACE`, `OCI_REGION`, `OCI_CONFIG_PATH`, `OCI_PREFIJO_ACTIVOS`, `OCI_PREFIJO_REPORTES`, `OCI_PREFIJO_LOGS` | Solo el código borrado |
| **B** (DEC-146) | `BASE_DIR`, `FAQ_PROVIDER`, `FAQ_MODEL` (`gemini-2.0-flash-exp`), `MOD_PROVIDER` (`openai`), `MOD_MODEL` (`gpt-4o-mini`), `CATEGORIAS_VALIDAS`, `UMBRAL_CONFIANZA_ALTA`, `UMBRAL_CONFIANZA_MEDIA`, y la **segunda copia** de `GEMINI_API_KEY` y de `OPENAI_API_KEY` | **Nadie**, ni el código viejo. Decían cosas falsas (que el Agente-Mod usa ChatGPT; el Agente FAQ tiene su propio `agents/agent_faq/config.py`). Harrison decidió borrarlas y registrarlo como decisión |

Ninguna de estas variables aparece en `compose.yml` ni en `.env.example` (💻 `grep`), así que ningún `.env` deja de tener efecto. Si en `main` aparece `cannot import name X from agents.orquestador.config`, X está en esta tabla.

### Qué se conservó y por qué

| Archivo | Por qué |
|---|---|
| `contratos.py` | Lo importan `agent_faq/tools/buscador.py`, `tools/reporte_faq.py`, `vectorstore/preguntas_store.py`, y `clasificadores/base.py` y `keyword_fallback.py` |
| `clasificadores/base.py`, `keyword_fallback.py`, `llm_models.py` | `etiquetador.py` usa `KeywordFallback` (proveedor `keyword`); `llm_models.py` lo usan el etiquetador, el Agente-Mod y la FAQ semanal |
| `nodos/invocador_faq.py` | Lo usan `api.py`, `grafo_v1.py` y `agent_mod/faq_semanal.py` |
| `GEMINI_API_KEY`, `OPENAI_API_KEY`, `COHERE_API_KEY`, `ANTHROPIC_API_KEY` (primera copia) y `ORQ_SUBAGENTE_FAQ_PATH` | Los usan `llm_models.py` e `invocador_faq.py` |
| `agents/agent_faq/test_agente.py` | 💻 Coincide con el Agente FAQ actual: `AgenteFAQ(forzar_reindexado=…)` y `responder(pregunta, metadata=…)`, que devuelve `respuesta_agente` (con `respuesta`, `encontrado`, `fuente` y los puntajes) y `reporte` (con `analisis_frecuencia`). **No se ejecutó**: es interactivo, llama a Gemini y escribe en el historial de preguntas |
| `tests/test_v1_procesar.py::test_la_puerta_vieja_procesar_ya_no_existe` | No importa nada borrado: comprueba que la API actual responde 404 en `/procesar` |

## 3. Archivos cambiados

| Archivo | Qué cambió | Por qué |
|---|---|---|
| Los 15 de la tabla "Qué se borró" y `requirements.txt` | Borrados | Ficha §2.1 y §2.5 |
| `agents/orquestador/clasificadores/__init__.py` | Ya no importa ni exporta `GenericLLMAdapter`; se quitó el comentario de Laya | Ficha §2.1 |
| `agents/orquestador/config.py` | Sin las variables de los grupos A y B ni `from pathlib import Path` (solo lo usaban `BASE_DIR` y `OCI_CONFIG_PATH`). El comentario de proveedores decía `"gemini" \| … \| "laya"`; ahora dice los que acepta `llm_models.py`: `"google" \| "openai" \| "cohere" \| "anthropic" \| "keyword"` | Ficha §2.3 y DEC-146 |
| `agents/orquestador/clasificadores/base.py`, `keyword_fallback.py` | Solo el docstring: decían que se usan "cuando Cohere y Laya no están disponibles"; ahora dicen cuándo se usan hoy | Búsqueda final de la ficha §4 (nombraban Laya) |
| `backend-java/src/test/…/ModeloDatosTest.java` | Comentario: `docs/tareas/T01-informe.md` → `docs/OPERACION.md §5` | Ficha §2.7. Se apunta al documento vigente con el mismo dato (cómo elegir la base de pruebas), no al histórico |
| `backend-java/src/test/…/SubidaOciTest.java` | Comentario: `CHAT_PRINCIPAL §5` → `AGENTS.md §5` | Ficha §2.7. `AGENTS.md` §5 tiene la misma regla (reutilizar las propiedades de una prueba existente) |
| `agents/orquestador/README.md` | Sin el aviso de "código que ya no se usa"; una línea dice que se borró en T11 | Ficha §2.8 |
| `docs/ARQUITECTURA.md` §10 | Sin el aviso | Ficha §2.8 |
| `docs/ESTADO.md` §3 | Punto 1 marcado como hecho, con enlace a este informe | Ficha §2.8 |
| `docs/DECISIONES.md` | DEC-145 cerrada; DEC-146 nueva; DEC-69 ya no dice "la limpieza queda como mejora" | Ficha §2.8 y decisión de Harrison |

## 4. Pruebas

| Comando ejecutado | Antes | Después (🧪) |
|---|---|---|
| `python -m pytest agents/orquestador/tests -q` | 79 passed | **79 passed** |
| `python -m pytest agents/bot_discord/tests -q` | 22 passed, 1 warning | **22 passed, 1 warning** |
| `python -m pytest panel/tests -q` | 51 passed | **51 passed** |
| `python -m pytest -q` (desde `ingestion/discord`) | 36 passed | **36 passed** |
| Importar cada módulo que queda (`config`, `clasificadores`, `etiquetador`, `llm_models`, `invocador_faq`, `grafo_v1`, `contratos`, `contrato_ia`, `api`) | — | **Todos importan sin error** |
| `docker compose up -d --build ia` y `GET http://127.0.0.1:8000/health` | — | **`Up (healthy)`**, `{"status":"ok","service":"orquestador","port":8000,"faq_listo":true}` |
| Pruebas de Java ([OPERACION.md](../../OPERACION.md) §5), contra `insightedu_test` | 219 | **BUILD exit 0: 219 tests, 0 failures, 0 errors, 0 skipped** (contado en `target/surefire-reports`). Los `ERROR` del registro son los fallos de OCI que las pruebas simulan |

Las pruebas de Python se corrieron con el entorno `%USERPROFILE%\.venvs\insightedu-discord` (el Python del sistema no tiene `pytest`). El warning del bot ya estaba antes.

## 5. Decisiones que se tomaron

| Decisión | Alternativas descartadas | ¿Cambia el contrato, la arquitectura o D1 a D7? |
|---|---|---|
| **DEC-146:** borrar también las variables de `config.py` que no usaba nadie (grupo B). Decisión de Harrison | Borrar solo el grupo A, como decía la ficha al pie de la letra | No |
| Los comentarios de Java apuntan a documentos vigentes (`OPERACION.md`, `AGENTS.md`), no a `docs/historico/` | Cambiar solo la ruta a `docs/historico/…` | No |
| Corregir los docstrings de `base.py` y `keyword_fallback.py` y el comentario de proveedores de `config.py` | Dejarlos: nombraban Laya, que ya no existe | No (solo texto) |

## 6. Dudas, riesgos y pendientes

- **Avisos del editor que ya estaban** (no se tocaron: la ficha no permite refactorizar): `import re` sin usar en `keyword_fallback.py`, `...` innecesarios en `base.py` y falta del salto de línea final en ambos. Mejora menor para después.
- La imagen `ia` que corre ahora en la máquina de Harrison ya es la de esta rama. Su comportamiento es el mismo; si se vuelve a otra rama, conviene reconstruirla.
- `test_agente.py` no se ejecutó (sección 2).

## 7. Comandos que ejecutó Harrison

Se completan al cerrar (`git add`, los dos commits y `git push -u origin tarea/T11-limpieza-codigo`).
