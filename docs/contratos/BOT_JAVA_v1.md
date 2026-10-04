# Contrato Bot ↔ Java v1 — InsightEdu Lab

> **Estado:** v1.0 · **Fecha:** 2026-10-04 · **Tarea:** T05 · **Decisiones:** DEC-66, DEC-67, DEC-68 y DEC-70

## 0. Sobre este documento

**Qué es.** El formato en que el bot de Discord le envía cada mensaje a la API Java, y la orden que Java le devuelve.

**Para quién.**
- Quien mantenga el bot (`agents/bot_discord/bot_communitylab.py`).
- Quien mantenga la puerta en vivo de Java (`backend-java/.../envivo/` y `MensajeEnVivoController`).

**La regla principal (DEC-68).** Java decide y el bot obedece. El bot no mira intenciones ni respuestas de la IA: recibe una orden (`RESPONDER`, `DERIVAR`, `REACCIONAR` o `NADA`) y la cumple. Así, las reglas (D3: publicar solo con respaldo; F5: a un logro, solo una reacción) quedan en un único lugar, con pruebas.

**Fuentes de verdad.** Si este documento y el código no coinciden, manda el código.

| Qué | Dónde |
|---|---|
| Entrada | El **contrato v1** de la ingesta, tal cual: [CONTRACT.md](../../ingestion/discord/docs/CONTRACT.md) y [contract_v1.schema.json](../../ingestion/discord/schema/contract_v1.schema.json). El bot lo arma con `transform.py` de la ingesta: **no hay otro formato de mensaje** |
| Salida | [OrdenBot.java](../../backend-java/src/main/java/com/insightedulab/backend_java/envivo/OrdenBot.java) |
| Qué decide Java | [EnVivoService.java](../../backend-java/src/main/java/com/insightedulab/backend_java/envivo/EnVivoService.java) |

## 1. La puerta

| Dato | Valor |
|---|---|
| Método y ruta | `POST /api/v1/mensajes/en-vivo` |
| Dentro de Docker | `http://api-java:8080/api/v1/mensajes/en-vivo` (variable `BOT_JAVA_URL` del bot) |
| Cuerpo | Un **lote del contrato v1** con `modo = "tiempoReal"` y **exactamente un** mensaje |
| Cabecera obligatoria | `X-Api-Key`: la clave `API_KEY_BOT`. La genera `python scripts/generar_api_key.py --cliente bot`. **Solo esta clave abre esta puerta** (DEC-70) |
| Cabecera opcional | `X-Id-Correlacion`: el bot pone el `loteId`. Java lo usa también al llamar a la IA, así un mismo pedido se sigue en los tres registros |
| Respuesta | `200` con la orden, también cuando la IA falla (entonces la orden es `NADA`) |

El mensaje en vivo **no** se registra en `lotes_recibidos`: un mensaje se reconoce por su `discord_id`, y el lote de la hora que lo vuelva a traer no lo duplica.

## 2. Qué hace Java con cada mensaje

1. Lo valida como cualquier lote del contrato v1 (y le quita el carácter NUL).
2. En **una** transacción, lo guarda (upsert) y lo **reserva** (`reservado_hasta`). La clasificación en segundo plano (T04) no puede tomarlo mientras tanto.
3. Si ya estaba clasificado, ya tenía respuesta o lo tenía reservado otro, devuelve `NADA` **sin llamar a la IA**: un mensaje nunca se responde dos veces.
4. Llama a la IA en modo `tiempoReal` ([JAVA_IA_v1.md](JAVA_IA_v1.md)), sin transacción abierta.
5. Guarda las etiquetas y la respuesta, solo si el mensaje no cambió mientras tanto (`actualizado_en`), y devuelve la orden:

| Resultado de la IA | Se guarda en `mensajes` | Orden |
|---|---|---|
| `PREGUNTA_FAQ` con `respuesta.encontrada = true` y texto | Etiquetas `OK`, `respuesta_estado = RESPONDIDA`, `respuesta_texto`, `respuesta_fuentes`, `respondido_en` | `RESPONDER` |
| `PREGUNTA_FAQ` con `encontrada = false` (incluido el tope agotado, DEC-54) | Etiquetas `OK`, `respuesta_estado = DERIVADA`, `respondido_en` | `DERIVAR` |
| `TESTIMONIO` | Etiquetas `OK` | `REACCIONAR` |
| `COMENTARIO` u `OTRO` | Etiquetas `OK` | `NADA` |
| `ERROR` en el mensaje, `422`, `500`, tiempo agotado o IA caída | Suma un intento, sigue `PENDIENTE` y **sin reserva**: lo clasifica la tarea en segundo plano | `NADA` (DEC-67) |
| El lote de la hora cambió el mensaje mientras la IA lo procesaba | Nada: se libera la reserva | `NADA` |

## 3. Ejemplo

**Pedido** (se acortó la caja; es la misma del [ejemplo de JAVA_IA_v1.md §3](JAVA_IA_v1.md#3-ejemplo))

```json
{
  "versionContrato": "1.0",
  "loteId": "3f2b8c1e-0d4a-4b7e-9a51-6c2f0e8d9b10",
  "fuente": "discord",
  "modo": "tiempoReal",
  "servidorId": "1554157903701741700",
  "generadoEn": "2026-10-04T15:00:00.000Z",
  "mensajes": [
    { "id": "1554205178671009863", "canal": { "id": "1554158212742127821", "nombre": "dudas" },
      "textoOriginal": "como instalo pyhton en windows?? me sale que pip no se reconoce como comando 😭",
      "…": "el resto de los campos del contrato v1" }
  ]
}
```

**Respuesta: `RESPONDER`**

```json
{
  "versionContratoBot": "1.0",
  "discordId": "1554205178671009863",
  "orden": "RESPONDER",
  "texto": "Al instalar Python marca la casilla 'Add python.exe to PATH'…\n\nFuentes:\n06_Manual_del_Estudiante_V3.pdf (Pág. 4)",
  "reaccion": null
}
```

**Las otras órdenes**

```json
{ "versionContratoBot": "1.0", "discordId": "…", "orden": "DERIVAR",
  "texto": "¡Gracias por tu pregunta! No encontré una respuesta segura en los documentos del curso, así que un mentor te responderá pronto. 🙏",
  "reaccion": null }

{ "versionContratoBot": "1.0", "discordId": "…", "orden": "REACCIONAR", "texto": null, "reaccion": "🎉" }

{ "versionContratoBot": "1.0", "discordId": "…", "orden": "NADA", "texto": null, "reaccion": null }
```

## 4. Campos de la respuesta

| Campo | Tipo | Nota |
|---|---|---|
| `versionContratoBot` | `"1.0"` | Cambia si cambia este formato |
| `discordId` | texto | El `id` del mensaje recibido |
| `orden` | `RESPONDER` \| `DERIVAR` \| `REACCIONAR` \| `NADA` | Lo único que el bot tiene que mirar |
| `texto` | texto o `null` | Lo que el bot publica **tal cual**, de 2000 caracteres como máximo (el límite de Discord). Solo en `RESPONDER` y `DERIVAR`. En `RESPONDER` es la respuesta del Agente FAQ sin agregados: el Agente FAQ ya cita en el texto el documento que usó. Java no le agrega un pie con `fuentes`, porque esa lista es el primer fragmento que encontró la búsqueda y a veces no es el documento citado (prueba real de T05) |
| `reaccion` | texto o `null` | El emoji que pone el bot. Solo en `REACCIONAR` |

## 5. Qué hace el bot con cada orden

| Orden | Qué hace |
|---|---|
| `RESPONDER` y `DERIVAR` | **Responde al mensaje** (así la respuesta queda enlazada: en el contrato tiene `respondeA`) con `texto`, y con **todas las menciones desactivadas** (`AllowedMentions.none()`, S8): ni `@everyone`, ni roles, ni usuarios, ni aviso al autor |
| `REACCIONAR` | Pone `reaccion` en el mensaje. **Sin texto** (F5) |
| `NADA` | Nada |
| Cualquier error (ver §6) u orden desconocida | Nada. Lo registra, sin el texto (DEC-67). El lote de la hora rescata el mensaje |

## 6. Errores

Todos usan el formato común de error de Java, con `codigo`, `mensaje`, `errores` e `idCorrelacion` ([JAVA_IA_v1.md §7](JAVA_IA_v1.md#7-errores)). Nunca repiten los datos recibidos (S7).

| `codigo` | HTTP | Cuándo |
|---|---|---|
| `NO_AUTORIZADO` | 401 | Falta `X-Api-Key` o la clave no es de ningún cliente |
| `PROHIBIDO` | 403 | La clave es de otro cliente (por ejemplo, la de la ingesta). Se revisa antes de leer el cuerpo |
| `CUERPO_INVALIDO` | 400 | El cuerpo no es JSON |
| `CONTRATO_INVALIDO` | 422 | No cumple el contrato v1, `modo` no es `tiempoReal` o no trae exactamente un mensaje |
| `ERROR_INTERNO` | 500 | Falló Java. El detalle queda en su registro |

Además, Java exige `Content-Length` (observación de T03). `aiohttp` lo envía cuando el cuerpo va con `json=`.

## 7. Tiempos (D4, F8)

| Pieza | Tiempo máximo |
|---|---|
| Cada llamada al LLM | 20 s |
| Todo el pedido dentro de la IA en `tiempoReal` | **25 s** (`TIEMPO_REAL_TOPE_S`, DEC-54) |
| Java → IA | 30 s |
| **Bot → Java** | **40 s**. Mientras espera, el bot muestra "escribiendo…" en el canal |

## 8. Fuera de este contrato

| Qué | Dónde se resuelve |
|---|---|
| Ediciones y borrados de mensajes | El lote de la hora los relee (`INGEST_REREAD_DAYS`) |
| Hilos y comandos de barra (`/ayuda`) | Fuera del MVP |
| Posts de LinkedIn y casos de éxito | T06: van al panel, nunca a Discord |
