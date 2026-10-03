# Tareas

Cada tarea tiene una **ficha** (la orden de trabajo, que escribe el chat principal) y un **informe** (lo que entrega el chat de tarea, con la [plantilla](PLANTILLA_INFORME.md)). El protocolo está en [CLAUDE.md §6](../../CLAUDE.md).

| Tarea | Qué | Depende de | Modelo recomendado | Estado |
|---|---|---|---|---|
| [T01](T01-modelo-datos.md) | Modelo de datos nuevo con Flyway (Java) · [informe](T01-informe.md) | — | Opus 5.5 | ✅ Aprobada el 2026-10-03 (`6034d64`) |
| [T02](T02-formato-java-ia.md) | Formato Java ↔ IA: la IA acepta el contrato v1 y devuelve intención, sentimiento y tema (Python) | — | Opus 5.5 | 📝 Ficha lista |
| T03 | Puerta de lotes con opción C, upsert y API key (Java) | T01 | — | ⏳ Ficha pendiente |
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
| T01 | 🔎 El upsert reconoce lo nuevo con `xmax = 0`, un comportamiento de PostgreSQL muy usado pero no documentado como garantía. Lo cubren las pruebas: si cambia la versión de PostgreSQL, hay que volver a correrlas | Al actualizar PostgreSQL |
