# Tareas

Cada tarea tiene una **ficha** (la orden de trabajo, que escribe el chat principal) y un **informe** (lo que entrega el chat de tarea, con la [plantilla](PLANTILLA_INFORME.md)). El protocolo está en [CLAUDE.md §6](../../CLAUDE.md).

| Tarea | Qué | Depende de | Modelo recomendado | Estado |
|---|---|---|---|---|
| [T01](T01-modelo-datos.md) | Modelo de datos nuevo con Flyway (Java) · [informe](T01-informe.md) | — | Opus 5.5 | ✅ Aprobada el 2026-10-03 (`6034d64`) |
| [T02](T02-formato-java-ia.md) | Formato Java ↔ IA: la IA acepta el contrato v1 y devuelve intención, sentimiento y tema (Python) · [informe](T02-informe.md) · [contrato](../contratos/JAVA_IA_v1.md) | — | Opus 5.5 | ✅ Aprobada el 2026-10-03 (`5b7c63e`) |
| [T03](T03-puerta-lotes.md) | Puerta de lotes en Java: contrato v1 (D8), upsert, idempotencia y API key; `send_batch.py` al Java real | T01 | Sonnet 5.5 | 📝 Ficha lista · falta validar D8 |
| T04 | Java envía los mensajes a la IA y guarda las etiquetas | T01, T02 | — | ⏳ Ficha pendiente |

Estados: 📝 ficha lista · 🔨 en curso · 🔍 en auditoría · ✅ aprobada o fusionada · ⏳ ficha pendiente

## Observaciones de auditoría que pasan a otras tareas

| Origen | Observación | Va a |
|---|---|---|
| T01 | Si cambia el texto de un mensaje, sus etiquetas viejas se conservan con `estado_clasificacion = PENDIENTE`. **Las consultas del dashboard deben contar solo `OK`** | Fase 5 (dashboard) |
| T01 | La ingesta apuntaba a `POST /api/v1/community/process`, que se quitó. La puerta nueva tiene que definir su ruta y actualizar `send_batch.py` y `.env.example` | T03 |
| T01 | La caja llega a `MensajeUpsertRepository` como `Map<String, Object>`. El DTO de entrada debe entregarla así o convertirla | T03 |
| T01 | `lotes_recibidos` y `mensajes` no están vinculados (un mensaje puede llegar en muchos lotes). Hace falta una tabla intermedia solo si el panel necesita saber en qué lote llegó cada mensaje | Fase 5, si hace falta |
| T01 | 🔎 Las URL de los adjuntos cambian en cada extracción, así que un mensaje con adjunto siempre cuenta como "actualizado" | T03 (evaluar) |
| T02 | **Tiempos en vivo:** una duda encadena hasta 3 llamadas al LLM, de 20 s como máximo cada una. En el peor caso supera los 30 s de Java → IA (D4). La IA necesita un **tope total por pedido** (por ejemplo, 25 s), o hay que ajustar los tiempos | T04 |
| T02 | 🔎 **Lotes de historial:** la IA etiqueta un mensaje tras otro (1 a 3 s cada uno), así que un lote de 39 mensajes no entra en 30 s. Java tiene que enviar a la IA **en tandas chicas** o procesar en segundo plano los mensajes `PENDIENTE` | T04 |
| T02 | Las listas cerradas de `sentimiento` y de `tema` (11 temas, [JAVA_IA_v1.md §4.3](../contratos/JAVA_IA_v1.md)) pueden pasar a `CHECK` en una migración `V2__…` | T04 |
| T02 | "Me gustó la clase, por fin entendí recursividad" salió `TESTIMONIO`. Hay que decidir si los logros de aprendizaje generan borradores o si el Agente-Mod los filtra | Fase 4 |
| T02 | `metricas` no cuenta los tokens del Agente FAQ | Fase 6 (🟡) |
| T02 | `/procesar` (el del bot) ahora también corta al LLM a los 20 s, sin 6 reintentos. Es una mejora, pero cambia el comportamiento | Al migrar el bot (C2) |
| T01 | 🔎 El upsert reconoce lo nuevo con `xmax = 0`, un comportamiento de PostgreSQL muy usado pero no documentado como garantía. Lo cubren las pruebas: si cambia la versión de PostgreSQL, hay que volver a correrlas | Al actualizar PostgreSQL |
