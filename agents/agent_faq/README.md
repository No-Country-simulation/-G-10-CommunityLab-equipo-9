# IA · Agente FAQ

Responde dudas de los alumnos **solo con lo que dicen los documentos de la institución** (RAG: búsqueda en los PDF y redacción con Gemini). Lo usan el flujo en vivo (`/v1/procesar` en modo `tiempoReal`) y la FAQ semanal (`/v1/faq`, que llama solo al buscador).

| Qué | Dónde |
|---|---|
| Los documentos de CommunityLab (institución ficticia) | `data/pdfs/` (12 PDF) |
| El índice de búsqueda ya construido | `data/vectorstore/faiss_pdfs/` |
| Buscar, reordenar y citar | `tools/buscador.py`, `vectorstore/` |
| El agente | `agente_faq.py` |

**Reglas:**
- si no encuentra respaldo en los PDF, la respuesta sale con `encontrada = false` y el bot deriva a un mentor;
- una respuesta con fidelidad media cuenta como no encontrada;
- las fuentes llevan solo el nombre del PDF y la página.

**Si se agregan o cambian PDF**, hay que reconstruir el índice: 🔎 borrar `data/vectorstore/faiss_pdfs/` y volver a construir la imagen `ia`; al arrancar, el agente lo arma de nuevo (sin probar).

⚠️ `historial_preguntas.json`, `data/vectorstore/faiss_preguntas/`, `tools/reporte_faq.py` y `vectorstore/preguntas_store.py` guardan un historial de preguntas **dentro de la IA**. El sistema no lo usa como fuente de datos: las dudas y la FAQ semanal salen de la base de Java.

Cómo encaja en el sistema: [docs/ARQUITECTURA.md](../../docs/ARQUITECTURA.md) §4.3, §4.5 y §8. El README original de este módulo está en [docs/historico/componentes/](../../docs/historico/componentes/agent_faq_README.md).
