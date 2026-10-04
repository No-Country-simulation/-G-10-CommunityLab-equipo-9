# Tareas

Cada tarea tiene una **ficha** (la orden de trabajo, que escribe el chat principal) y un **informe** (lo que entrega el chat de tarea, con la [plantilla](PLANTILLA_INFORME.md)). El protocolo está en [CLAUDE.md §6](../../CLAUDE.md).

| Tarea | Qué | Depende de | Modelo recomendado | Estado |
|---|---|---|---|---|
| [T01](T01-modelo-datos.md) | Modelo de datos nuevo con Flyway (Java) · [informe](T01-informe.md) | — | Opus 5.5 | ✅ Aprobada el 2026-10-03 (`6034d64`) |
| [T02](T02-formato-java-ia.md) | Formato Java ↔ IA: la IA acepta el contrato v1 y devuelve intención, sentimiento y tema (Python) · [informe](T02-informe.md) · [contrato](../contratos/JAVA_IA_v1.md) | — | Opus 5.5 | ✅ Aprobada el 2026-10-03 (`5b7c63e`) |
| [T03](T03-puerta-lotes.md) | Puerta de lotes en Java: contrato v1 (D8), upsert, idempotencia y API key; `send_batch.py` al Java real | T01 | Sonnet 5.5 (se usó Opus 5.5) | ✅ Aprobada el 2026-10-04 (`c895af3`) · [informe](T03-informe.md) |
| [T04](T04-clasificacion-java-ia.md) | Java clasifica en segundo plano los mensajes `PENDIENTE` con la IA y guarda las etiquetas; API key entre Java y la IA (S2); carácter NUL | T01, T02, T03 | Opus 5.5 | 🔍 Terminada (`3ea907b`), **pendiente de auditoría** |

Estados: 📝 ficha lista · 🔨 en curso · 🔍 en auditoría · ✅ aprobada o fusionada · ⏳ ficha pendiente

## Observaciones de auditoría que pasan a otras tareas

| Origen | Observación | Va a |
|---|---|---|
| T01 | Si cambia el texto de un mensaje, sus etiquetas viejas se conservan con `estado_clasificacion = PENDIENTE`. **Las consultas del dashboard deben contar solo `OK`** | Fase 5 (dashboard) |
| T01 | La ingesta apuntaba a `POST /api/v1/community/process`, que se quitó. La puerta nueva tiene que definir su ruta y actualizar `send_batch.py` y `.env.example` | T03 |
| T01 | La caja llega a `MensajeUpsertRepository` como `Map<String, Object>`. El DTO de entrada debe entregarla así o convertirla | T03 |
| T01 | `lotes_recibidos` y `mensajes` no están vinculados (un mensaje puede llegar en muchos lotes). Hace falta una tabla intermedia solo si el panel necesita saber en qué lote llegó cada mensaje | Fase 5, si hace falta |
| T01 | 🔎 Las URL de los adjuntos cambian en cada extracción, así que un mensaje con adjunto siempre cuenta como "actualizado". **T03 lo evaluó:** solo afecta el contador y `actualizado_en`; no reinicia la clasificación. Se deja así | — |
| T03 | Java valida los campos que van a columnas; la IA valida el contrato completo. **Un 422 de la IA es un error del lote**: se cuenta como intento y no se reintenta sin fin | T04 (ya está en la ficha) |
| T03 | Un carácter NUL (`\u0000`) en un texto hace fallar **todo** el lote con 500, porque PostgreSQL no lo acepta. Se quitará al recibir | T04 |
| T03 | La API key viaja en texto plano por HTTP. Está bien en `127.0.0.1`; en el servidor, la ingesta y Java tienen que hablar por la red interna de Docker o por HTTPS | Fase 6 |
| T03 | Java exige `Content-Length` en POST, PUT y PATCH (si falta, 411). `httpx`, `requests` y `aiohttp` lo envían con JSON. Revisarlo si un cliente envía por partes | C2 y panel |
| T03 | Un pedido `OPTIONS` del navegador recibe 401. No afecta, porque el panel llama a Java desde el servidor (S6) | Fase 5, si el panel cambia |
| T02 | **Tiempos en vivo:** una duda encadena hasta 3 llamadas al LLM, de 20 s como máximo cada una. En el peor caso supera los 30 s de Java → IA (D4). La IA necesita un **tope total por pedido** (por ejemplo, 25 s), o hay que ajustar los tiempos | T04 |
| T02 | 🔎 **Lotes de historial:** la IA etiqueta un mensaje tras otro (1 a 3 s cada uno), así que un lote de 39 mensajes no entra en 30 s. Java tiene que enviar a la IA **en tandas chicas** o procesar en segundo plano los mensajes `PENDIENTE` | T04 |
| T02 | Las listas cerradas de `sentimiento` y de `tema` (11 temas, [JAVA_IA_v1.md §4.3](../contratos/JAVA_IA_v1.md)) pueden pasar a `CHECK` en una migración `V2__…` | T04 |
| T02 | "Me gustó la clase, por fin entendí recursividad" salió `TESTIMONIO`. Hay que decidir si los logros de aprendizaje generan borradores o si el Agente-Mod los filtra | Fase 4 |
| T02 | `metricas` no cuenta los tokens del Agente FAQ | Fase 6 (🟡) |
| T02 | `/procesar` (el del bot) ahora también corta al LLM a los 20 s, sin 6 reintentos. Es una mejora, pero cambia el comportamiento | Al migrar el bot (C2) |
| T01 | 🔎 El upsert reconoce lo nuevo con `xmax = 0`, un comportamiento de PostgreSQL muy usado pero no documentado como garantía. Lo cubren las pruebas: si cambia la versión de PostgreSQL, hay que volver a correrlas | Al actualizar PostgreSQL |
