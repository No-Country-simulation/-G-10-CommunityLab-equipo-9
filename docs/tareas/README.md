# Tareas

Cada tarea tiene una **ficha** (la orden de trabajo, que escribe el chat principal) y un **informe** (lo que entrega el chat de tarea, con la [plantilla](PLANTILLA_INFORME.md)). El protocolo está en [CLAUDE.md §6](../../CLAUDE.md).

| Tarea | Qué | Depende de | Modelo recomendado | Estado |
|---|---|---|---|---|
| [T01](T01-modelo-datos.md) | Modelo de datos nuevo con Flyway (Java) · [informe](T01-informe.md) | — | Opus 5.5 | ✅ Aprobada el 2026-10-03 (`6034d64`) |
| [T02](T02-formato-java-ia.md) | Formato Java ↔ IA: la IA acepta el contrato v1 y devuelve intención, sentimiento y tema (Python) · [informe](T02-informe.md) · [contrato](../contratos/JAVA_IA_v1.md) | — | Opus 5.5 | ✅ Aprobada el 2026-10-03 (`5b7c63e`) |
| [T03](T03-puerta-lotes.md) | Puerta de lotes en Java: contrato v1 (D8), upsert, idempotencia y API key; `send_batch.py` al Java real | T01 | Sonnet 5.5 (se usó Opus 5.5) | ✅ Aprobada el 2026-10-04 (`c895af3`) · [informe](T03-informe.md) |
| [T04](T04-clasificacion-java-ia.md) | Java clasifica en segundo plano los mensajes `PENDIENTE` con la IA y guarda las etiquetas; API key entre Java y la IA (S2); carácter NUL | T01, T02, T03 | Opus 5.5 | ✅ Aprobada el 2026-10-04 (`3ea907b`) · [informe](T04-informe.md) |
| [T05](T05-bot-en-vivo.md) | El bot pasa por Java: puerta en vivo, respuesta guardada, tope total en la IA, bot en Docker (C2, F5, S8, S10) | T03, T04 | Opus 5.5 | ✅ Aprobada el 2026-10-04 (`c815546`, con los cambios de la auditoría) · [informe](T05-informe.md) · [contrato bot ↔ Java](../contratos/BOT_JAVA_v1.md) |

Estados: 📝 ficha lista · 🔨 en curso · 🔍 en auditoría · ✅ aprobada o fusionada · ⏳ ficha pendiente

## Observaciones de auditoría que pasan a otras tareas

| Origen | Observación | Va a |
|---|---|---|
| T01 | Si cambia el texto de un mensaje, sus etiquetas viejas se conservan con `estado_clasificacion = PENDIENTE`. **Las consultas del dashboard deben contar solo `OK`** | Fase 5 (dashboard) |
| T01 | La ingesta apuntaba a `POST /api/v1/community/process`, que se quitó. La puerta nueva tiene que definir su ruta y actualizar `send_batch.py` y `.env.example` | T03 |
| T01 | La caja llega a `MensajeUpsertRepository` como `Map<String, Object>`. El DTO de entrada debe entregarla así o convertirla | T03 |
| T01 | `lotes_recibidos` y `mensajes` no están vinculados (un mensaje puede llegar en muchos lotes). Hace falta una tabla intermedia solo si el panel necesita saber en qué lote llegó cada mensaje | Fase 5, si hace falta |
| T01 | 🔎 Las URL de los adjuntos cambian en cada extracción, así que un mensaje con adjunto siempre cuenta como "actualizado". **T03 lo evaluó:** solo afecta el contador y `actualizado_en`; no reinicia la clasificación. Se deja así | — |
| T03 | Java valida los campos que van a columnas; la IA valida el contrato completo. **Un 422 de la IA es un error del lote**: se cuenta como intento y no se reintenta sin fin | ✅ Resuelto en T04 |
| T03 | Un carácter NUL (`\u0000`) en un texto hace fallar **todo** el lote con 500, porque PostgreSQL no lo acepta. Se quitará al recibir | ✅ Resuelto en T04 |
| T03 | La API key viaja en texto plano por HTTP. Está bien en `127.0.0.1`; en el servidor, la ingesta y Java tienen que hablar por la red interna de Docker o por HTTPS | Fase 6 |
| T03 | Java exige `Content-Length` en POST, PUT y PATCH (si falta, 411). `httpx`, `requests` y `aiohttp` lo envían con JSON. Revisarlo si un cliente envía por partes | C2 ✅ (el bot usa `aiohttp`); falta el panel |
| T03 | Un pedido `OPTIONS` del navegador recibe 401. No afecta, porque el panel llama a Java desde el servidor (S6) | Fase 5, si el panel cambia |
| T02 | **Tiempos en vivo:** una duda encadena hasta 3 llamadas al LLM, de 20 s como máximo cada una. En el peor caso supera los 30 s de Java → IA (D4). La IA necesita un **tope total por pedido** (por ejemplo, 25 s), o hay que ajustar los tiempos | ✅ Resuelto en T05 (DEC-54) |
| T02 | 🔎 **Lotes de historial:** la IA etiqueta un mensaje tras otro (1 a 3 s cada uno), así que un lote de 39 mensajes no entra en 30 s. Java tiene que enviar a la IA **en tandas chicas** o procesar en segundo plano los mensajes `PENDIENTE` | ✅ Resuelto en T04 |
| T02 | Las listas cerradas de `sentimiento` y de `tema` (11 temas, [JAVA_IA_v1.md §4.3](../contratos/JAVA_IA_v1.md)) pueden pasar a `CHECK` en una migración `V2__…` | ✅ Resuelto en T04 (V2) |
| T02 | "Me gustó la clase, por fin entendí recursividad" salió `TESTIMONIO`. Hay que decidir si los logros de aprendizaje generan borradores o si el Agente-Mod los filtra | Fase 4 |
| T02 | `metricas` no cuenta los tokens del Agente FAQ | Fase 6 (🟡) |
| T02 | `/procesar` (el del bot) ahora también corta al LLM a los 20 s, sin 6 reintentos. Es una mejora, pero cambia el comportamiento | ✅ `/procesar` se quitó en T05 |
| T01 | 🔎 El upsert reconoce lo nuevo con `xmax = 0`, un comportamiento de PostgreSQL muy usado pero no documentado como garantía. Lo cubren las pruebas: si cambia la versión de PostgreSQL, hay que volver a correrlas | Al actualizar PostgreSQL |
| T04 | 🔎 **Doble clasificación en vivo:** si el flujo en vivo guarda el mensaje como `PENDIENTE` antes de llamar a la IA, la clasificación en segundo plano puede tomarlo al mismo tiempo (dos llamadas al LLM por el mismo mensaje). El flujo en vivo tiene que guardarlo reservado (`reservado_hasta`) o ya clasificado | ✅ Resuelto en T05 |
| T04 | Los mensajes en `ERROR` no se reintentan solos, y la razón del error solo queda en el registro de `api-java`. El panel debería poder devolverlos a `PENDIENTE`; si tiene que mostrar la razón, hace falta una columna en una `V3__…` | T07 |
| T04 | **Ritmo:** 39 mensajes tardan unos 5 minutos (tandas de 5 cada 30 s). Se ajusta con `clasificacion.tanda` e `intervalo-ms`, sin tocar código, cuidando el límite de pedidos por minuto de Gemini (F15) | T10 (demo) |
| T04 | Un corte largo de la IA, o una `API_KEY_IA` mal puesta (401), suma intentos sin pasar a `ERROR`. Cuando la IA vuelve, el primer `ERROR` de ese mensaje es definitivo | 🟡 |
| T04 | 🔎 Si la IA devolviera algo que Java no puede leer (un error del cliente que no es de conexión), la tanda falla sin sumar intentos y se reintenta cada 2 min sin fin. Muy improbable, porque la respuesta está tipada por el contrato | 🟡 |
| T04 | PowerShell no encuentra `Select-String "Clasificación"` en los registros por la tilde; sirve `"Clasificaci"`. Anotarlo en [OPERACION.md](../OPERACION.md) (no se edita ahora porque T04 tocó ese archivo) | ✅ Agregado en T05 |
| T04 | El `curl` de la prueba real de [T02-informe.md](T02-informe.md) ahora necesita `-H "X-Api-Key: …"` | — (solo si alguien lo repite) |
| Chat principal (2026-10-04) | 🧪 **"Dudas sin responder" sale inflado si solo se cuenta `respondeA`:** de los 39 mensajes, solo 1 usa el botón "Responder" de Discord, así que las 16 dudas aparecen sin respuesta. El flujo en vivo tiene que **guardar si el bot respondió** (`respuesta.encontrada`), y el dashboard tiene que contar una duda como atendida si la respondió el bot o una persona | T05 ✅ (guarda `respuesta_estado`) y T08 (contar) |
| Chat principal (2026-10-04) | 🔎 **Alerta de deserción en la demo:** los mensajes de prueba abarcan solo 5 días (del 2026-09-28 al 2026-10-02), así que la regla "no escribe hace 14 días" no marcaría a nadie hasta mediados de octubre. El umbral tiene que ser configurable, o la demo necesita datos más largos | T08 y T10 |
| T05 | `RESPONDIDA` se guarda cuando Java decide, **antes** de que el bot publique. Si Discord rechazara la respuesta (por ejemplo, por permisos), la base diría "respondida" aunque el alumno no la vio. Riesgo aceptado (DEC-79) | T08 (al interpretar el indicador) |
| T05 | Las preguntas que no son del curso ahora son `PREGUNTA_FAQ` con tema `otro` y se derivan al mentor (DEC-73): cuentan como dudas y como "dudas sin responder". El dashboard debería poder separar el tema `otro` | T08 |
| T05 | La entidad JPA `Mensaje` no tiene las 4 columnas de la V3 (`ddl-auto=validate` lo permite). Agregarlas cuando el dashboard las lea | T08 |
| T05 | `respuesta_fuentes` guarda **el primero** de los 3 fragmentos que encontró la búsqueda (`buscador.py`, `citaciones[0]`), que no siempre es el documento que citó Gemini. La fuente citada queda en `respuesta_texto` | T06 (si la FAQ semanal usa las fuentes) o 🟡 |
| T05 | Cuando se agota el tope de 25 s, el Agente FAQ sigue trabajando en segundo plano y gasta esa llamada a Gemini. Hay 4 hilos: si se trabaran todos, las dudas siguientes se derivarían | 🟡 |
| T05 | El aviso "escribiendo…" aparece en todos los mensajes de los dos canales, también en `#logros` | 🟡 |
| T05 | Si falta el token, el aviso del bot lo escribe `config.py` de la ingesta y menciona su `.env`, no el de la raíz | 🟡 |
| T05 | Las ediciones de mensajes no pasan por el bot: las toma el lote de la hora. Una duda ya respondida que se edita vuelve a `PENDIENTE`, pero no se responde otra vez | — (comportamiento esperado) |
| T05 | Las claves que se pegaron en el chat de T05 (token del bot, webhooks y clave de la ingesta) no se cambiaron (DEC-71, riesgo aceptado). Al desplegar se generan claves nuevas para el servidor | T10 |
