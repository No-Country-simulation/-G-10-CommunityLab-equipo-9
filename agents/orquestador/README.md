# IA · Orquestador

Servicio `ia` de InsightEdu Lab (FastAPI + LangGraph). **Solo lo llama la API Java**, con la clave `API_KEY_IA` en `X-Api-Key`.

| Puerta | Qué hace | Código |
|---|---|---|
| `POST /v1/procesar` | Clasifica un lote del contrato v1: intención, sentimiento y tema por mensaje. En modo `tiempoReal`, además, la respuesta del Agente FAQ a las dudas | `grafo_v1.py`, `clasificadores/etiquetador.py` |
| `POST /v1/generar` | Borrador de post de LinkedIn y caso de éxito de un logro (Agente-Mod) | `../agent_mod/agente_mod.py` |
| `POST /v1/faq` | FAQ semanal con las dudas repetidas | `../agent_mod/faq_semanal.py` |
| `GET /health` | Salud del servicio (`faq_listo` indica que el Agente FAQ ya cargó) | `api.py` |

- **Contrato:** [docs/contratos/JAVA_IA_v1.md](../../docs/contratos/JAVA_IA_v1.md).
- **Cómo funciona dentro del sistema:** [docs/ARQUITECTURA.md](../../docs/ARQUITECTURA.md) §4 y §8.
- **Pruebas** (sin Gemini, con un LLM falso): `python -m pytest agents/orquestador/tests -q`, desde la raíz.

⚠️ **Código que ya no se usa** (de un diseño anterior, pendiente de borrar: [ESTADO.md](../../docs/ESTADO.md)): `orquestador.py`, `adaptador.py`, `nodos/` (salvo `invocador_faq.py`, que sí se usa), `aristas/`, `clasificadores/` (salvo `etiquetador.py`, `llm_models.py` y `keyword_fallback.py`), `storage/` y `test_orquestador.py`. El README original de este módulo está en [docs/historico/componentes/](../../docs/historico/componentes/orquestador_README.md).
