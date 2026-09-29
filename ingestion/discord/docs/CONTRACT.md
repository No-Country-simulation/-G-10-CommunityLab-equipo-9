# Contrato de ingesta v1 — InsightEdu Lab

> **Estado:** borrador v0.1, para validar · **Fecha:** 2026-09-29 · **Rama:** `feature/discord-ingestion`

## 0. Sobre este documento

**Qué es el contrato.** Es el formato en que cada mensaje de Discord entra al sistema. Es el mismo formato tanto en el análisis por lotes como en el bot en vivo (ver [ARCHITECTURE_PROPOSAL.md](ARCHITECTURE_PROPOSAL.md)).

**Cómo se diseñó.** A partir del [catálogo de eventos](EVENT_CATALOG.md), sin tomar como referencia los modelos de backend ni del motor IA, para no sesgarlo. La regla fue: **cada campo cita los casos del catálogo que lo necesitan**, y los campos técnicos citan la decisión que los exige. Si un dato no tiene casos, no entra. La comparación con backend es el paso siguiente (§9).

**Para quién.**
- Backend, que lo recibe.
- IA y dashboard, que lo consumen.
- Quien programe la transformación desde Discord.

## 1. Reglas del contrato

1. **1 mensaje de Discord = 1 registro.** No se agrupan mensajes (P7).
2. **El texto original no se modifica.** La limpieza queda para después (P1).
3. **Siempre los mismos campos.** Si Discord no manda un dato, el campo va igual, con un valor explícito: `[]`, `null` o `false`.
4. **Los IDs van como texto.** Superan el número entero máximo que maneja JavaScript sin perder precisión.
5. **Las fechas van en ISO 8601, en UTC, terminadas en `Z` y con milisegundos.** Por ejemplo: `2026-09-28T18:56:30.331Z`.
6. **Los nombres de campo van en `camelCase`.**
7. **Solo entran los datos que pide algún caso del MVP.** Todo lo demás se conserva en los datos crudos (`data/raw/`).
8. **El contrato tiene número de versión.** Si cambia, cambia la versión.

## 2. El lote

> El "sobre" que envuelve a los mensajes. En el análisis se envía un lote con muchos mensajes; en tiempo real, un lote con un solo mensaje.

| Campo | Tipo | Ejemplo | Por qué existe |
|---|---|---|---|
| `versionContrato` | texto | `"1.0"` | Decisión: contrato versionado ([SCOPE.md](SCOPE.md)) |
| `loteId` | texto (UUID) | `"3f2b…"` | Para rastrear cada envío y detectar los reenvíos |
| `fuente` | texto | `"discord"` | Permite sumar otras plataformas en el futuro sin cambiar el formato |
| `modo` | `historial` \| `tiempoReal` | `"historial"` | Los dos flujos de la arquitectura |
| `servidorId` | texto | `"1554157903701741700"` | Distingue a qué comunidad pertenece el lote |
| `generadoEn` | fecha | `"2026-09-29T15:00:00.000Z"` | Momento en que se armó el lote |
| `mensajes` | lista de mensajes (§3) | — | — |

## 3. El mensaje

> Todos los campos de cada mensaje. La columna "Casos" remite al [catálogo](EVENT_CATALOG.md).

| Campo | Tipo | Ejemplo | De dónde sale en Discord | Casos |
|---|---|---|---|---|
| `id` | texto | `"1554205178671009863"` | `id` | A1. También sirve para vincular respuestas (A6, A7) y evitar duplicados (P6) |
| `canal` | objeto (§4.2) | `{ "id": "…", "nombre": "dudas" }` | `channel_id`; el nombre sale de la extracción | A1, A2, A4, B1, B5, D1, D2, E1, E4 |
| `fecha` | fecha | `"2026-09-28T18:56:30.331Z"` | `timestamp`, convertido a UTC con `Z` | A1, A2, A4, A5, A7, B1–B5, D1, D2, E1–E5, F2, H3 |
| `tipo` | valor fijo (§5) | `"respuesta"` | Se deduce de `type` | A7, G4, I1. Distingue a las personas de los avisos del sistema |
| `tipoDiscord` | entero | `19` | `type`, sin cambios | Trazabilidad: el valor original de Discord |
| `esSimulado` | booleano | `true` | `true` si lo publicó uno de **nuestros** webhooks de simulación | Decisión: marcar los mensajes simulados ([SCOPE.md](SCOPE.md)) |
| `autor` | objeto (§4.1) | — | `author`, más reglas (§4.1) | A1, A7, A8, A10, B1, B5, B6, E1, E3, H1, I2 |
| `textoOriginal` | texto | `"como instalo pyhton…"` | `content`, sin cambios | A1, A4, B1–B6, C1, C3, D1–D3, E1, E2, E5, F2, H1, H3 |
| `tieneTexto` | booleano | `false` | `content` no está vacío | A3. Hallazgo de la guía: hay mensajes sin texto |
| `tieneBloqueCodigo` | booleano | `true` | `content` contiene `` ``` `` | A1, C3 |
| `enlaces` | lista (§4.5) | `[{ "url": "…", "dominio": "github.com" }]` | Se extraen de `content` | A1, B8, C1, C3, D3, H3, I2 |
| `menciones` | objeto (§4.3) | — | `mentions`, `mention_roles` y `mention_everyone` | B6, B7, G2 |
| `mencionaAlBot` | booleano | `true` | Menciona al bot (`<@id>`) **o a su rol** (`<@&id>`) | G2 y el hallazgo de la prueba real |
| `respondeA` | texto o `null` | `"1554205273621667853"` | `message_reference.message_id`, solo en respuestas | A6, A7, A8, A10, B7. Con él se calculan las "respuestas recibidas" (A5, A9, C3) |
| `adjuntos` | lista (§4.4) | — | `attachments` | A1, A3, B1, B2, C1 |
| `reacciones` | lista (§4.6) | `[{ "emoji": "🎉", "emojiId": null, "cantidad": 1 }]` | `reactions`; `[]` si no viene | A6, A9, A10, B1, B7, D1, D2, G1 |
| `fijado` | booleano | `true` | `pinned` | A8, C2, G4 |
| `editado` | booleano | `true` | `edited_timestamp` no es `null` | A6, G5 |
| `editadoEn` | fecha o `null` | `"2026-09-28T21:25:19.495Z"` | `edited_timestamp` | A6, G5 |
| `stickers` | lista de textos | `["wave"]` | Nombres de `sticker_items` | I1 |
| `vistasPrevias` | lista (§4.7) | — | `embeds` | B8, I1 |
| `encuesta` | objeto (§4.8) o `null` | — | `poll` | D4 |

## 4. Objetos dentro del mensaje

### 4.1 `autor`

| Campo | Tipo | Ejemplo | Regla |
|---|---|---|---|
| `id` | texto | `"sim-ana-perez"` | **La identidad estable del autor, la que usan todos los consumidores.** Si es una persona real, es su ID de Discord. Si es simulado, es `sim-` más su nombre normalizado, porque su ID de Discord es el del webhook |
| `idDiscord` | texto | `"1554160711800717417"` | `author.id` sin cambios, para trazabilidad. En los simulados es el ID del webhook |
| `nombreUsuario` | texto | `"Ana Pérez"` | `author.username` |
| `nombreVisible` | texto | `"Ana Pérez"` | `author.global_name`; si no existe, `username` |
| `tipo` | valor fijo (§5) | `"persona"` | Se deduce de `author.bot`, `webhook_id` y el ID de nuestro bot |
| `rol` | valor fijo (§5) | `"mentor"` | Sale de una **lista configurada** de mentores y *staff*, no de Discord (ver §8). Si la persona no está en la lista, es `miembro` |

### 4.2 `canal`

| Campo | Tipo | Ejemplo |
|---|---|---|
| `id` | texto | `"1554158212742127821"` |
| `nombre` | texto | `"dudas"` |

### 4.3 `menciones`

| Campo | Tipo | Ejemplo |
|---|---|---|
| `usuarios` | lista de IDs | `["1554158872585965578"]` |
| `roles` | lista de IDs | `["1554160419470315653"]` |
| `todos` | booleano | `false` (`true` si menciona a `@everyone`) |

### 4.4 Adjunto (`adjuntos[]`)

| Campo | Tipo | Ejemplo | Nota |
|---|---|---|---|
| `id` | texto | `"1554243551888416798"` | |
| `nombre` | texto | `"captura.jpg"` | |
| `tipoContenido` | texto o `null` | `"image/jpeg"` | |
| `tamanoBytes` | entero | `97526` | |
| `ancho`, `alto` | entero o `null` | `831`, `1080` | Solo en imágenes y videos |
| `url` | texto | `"https://cdn.discordapp.com/…"` | **Es temporal.** No se debe guardar como un enlace permanente |
| `urlExpiraEn` | fecha o `null` | `"2026-09-29T21:28:59.000Z"` | Se lee del parámetro `ex` de la URL (ver §8) |

### 4.5 Enlace (`enlaces[]`)

| Campo | Tipo | Ejemplo |
|---|---|---|
| `url` | texto | `"https://github.com/usuario-ejemplo/conversor-monedas"` |
| `dominio` | texto | `"github.com"`, sin `www.` |

### 4.6 Reacción (`reacciones[]`)

| Campo | Tipo | Ejemplo | Nota |
|---|---|---|---|
| `emoji` | texto | `"🎉"` | En los emojis personalizados, es su nombre |
| `emojiId` | texto o `null` | `null` | `null` si es un emoji estándar |
| `cantidad` | entero | `12` | No dice quién reaccionó (ver §6) |

### 4.7 Vista previa (`vistasPrevias[]`)

| Campo | Tipo | Nota |
|---|---|---|
| `tipo` | texto | Por ejemplo `"link"`, `"video"` o `"gifv"` |
| `url` | texto o `null` | |
| `titulo` | texto o `null` | En un post de LinkedIn compartido, suele ser el título del post |
| `descripcion` | texto o `null` | |

### 4.8 `encuesta`

| Campo | Tipo | Nota |
|---|---|---|
| `pregunta` | texto | |
| `opciones` | lista de `{ texto, votos }` | |
| `finalizada` | booleano | |

⚠️ Las §4.7 y §4.8 siguen la documentación de Discord, pero **todavía no hay muestras reales**. Se verifican cuando se amplíe la simulación.

## 5. Valores fijos

| Campo | Valores | Cuándo |
|---|---|---|
| `modo` | `historial` | El lote viene de la extracción por lotes |
| | `tiempoReal` | El lote viene del bot en vivo |
| `tipo` | `mensaje` | `type` 0 |
| | `respuesta` | `type` 19 |
| | `avisoSistema` | `type` 6 (fijado), 7 (se unió), 18 (hilo creado) o 46 (resultado de encuesta) |
| | `otro` | Cualquier otro `type` |
| `autor.tipo` | `persona` | Una persona real, o un alumno simulado por nuestros webhooks |
| | `botPropio` | Nuestro bot (A10) |
| | `otroBot` | Cualquier otro bot o webhook (I2) |
| `autor.rol` | `miembro` | Valor por defecto |
| | `mentor` | Está en la lista configurada de mentores |
| | `staff` | Está en la lista configurada de *staff* |

## 6. Lo que NO está en el contrato

> Tan importante como lo que sí está: evita que cada equipo espere un dato que nunca va a llegar.

| Dato | Por qué no está | Quién lo resuelve |
|---|---|---|
| Sentimiento, tema o tipo de evento de negocio (contratación, frustración…) | Es interpretación | Motor IA |
| Respuestas recibidas, dudas sin responder, tamaño de un debate (A5, A9, C3) | Se calcula entre muchos mensajes, con `respondeA`, `autor.id` y `fecha` | IA o dashboard |
| Mensajes partidos agrupados (A2, A3) | Es un cálculo derivado (P7) | IA o un paso posterior |
| Deserción y tendencias (E3, E4) | Es un cálculo derivado | Dashboard |
| Quién reaccionó (C2, G1) | Requiere una petición aparte por cada emoji | Una versión futura |
| Hilos y foros (G3) | P5 está descartado para el MVP | — |
| Fecha de ingreso y roles reales de Discord (F1, F3) | Decisión del MVP: no se extraen datos de los miembros | El rol sale de la lista configurada |
| Borrados y salidas de miembros (G6, F4) | Solo existen en tiempo real | La versión de tiempo real |
| Eventos programados (H2) | No son mensajes, y no están priorizados en el MVP | — |
| Campos estéticos del perfil, `flags`, `components`, `tts`… | Ningún caso los usa | Quedan en los datos crudos |

## 7. Ejemplos con datos reales

> Generados con [`prototypes/contract_prototype.py`](../prototypes/contract_prototype.py) a partir de `data/raw/`. Los datos de la persona real están ocultos, y la URL del adjunto está acortada.

**Lote completo, con una duda simulada** (`loteId` y `generadoEn` son valores ilustrativos)
```json
{
  "versionContrato": "1.0",
  "loteId": "3f2b8c1e-0d4a-4b7e-9a51-6c2f0e8d9b10",
  "fuente": "discord",
  "modo": "historial",
  "servidorId": "1554157903701741700",
  "generadoEn": "2026-09-29T15:00:00.000Z",
  "mensajes": [
    {
      "id": "1554205178671009863",
      "canal": { "id": "1554158212742127821", "nombre": "dudas" },
      "fecha": "2026-09-28T18:56:30.331Z",
      "tipo": "mensaje",
      "tipoDiscord": 0,
      "esSimulado": true,
      "autor": {
        "id": "sim-ana-perez",
        "idDiscord": "1554160711800717417",
        "nombreUsuario": "Ana Pérez",
        "nombreVisible": "Ana Pérez",
        "tipo": "persona",
        "rol": "miembro"
      },
      "textoOriginal": "como instalo pyhton en windows?? me sale que pip no se reconoce como comando 😭",
      "tieneTexto": true,
      "tieneBloqueCodigo": false,
      "enlaces": [],
      "menciones": { "usuarios": [], "roles": [], "todos": false },
      "mencionaAlBot": false,
      "respondeA": null,
      "adjuntos": [],
      "reacciones": [],
      "fijado": false,
      "editado": false,
      "editadoEn": null,
      "stickers": [],
      "vistasPrevias": [],
      "encuesta": null
    }
  ]
}
```

**Respuesta de una persona real, editada** (solo se muestran los campos que cambian respecto del ejemplo anterior)
```json
{
  "id": "1554242531439415440",
  "fecha": "2026-09-28T21:24:55.925Z",
  "tipo": "respuesta",
  "tipoDiscord": 19,
  "esSimulado": false,
  "autor": { "id": "<oculto>", "idDiscord": "<oculto>", "nombreUsuario": "<oculto>", "nombreVisible": "<oculto>", "tipo": "persona", "rol": "miembro" },
  "textoOriginal": "Que necesitas @Ana Pérez ?",
  "respondeA": "1554205273621667853",
  "editado": true,
  "editadoEn": "2026-09-28T21:25:19.495Z"
}
```

**Imagen sin texto, fijada**
```json
{
  "id": "1554243552215703622",
  "fecha": "2026-09-28T21:28:59.297Z",
  "textoOriginal": "",
  "tieneTexto": false,
  "adjuntos": [{
    "id": "1554243551888416798", "nombre": "captura.jpg", "tipoContenido": "image/jpeg",
    "tamanoBytes": 97526, "ancho": 831, "alto": 1080,
    "url": "https://cdn.discordapp.com/attachments/…/captura.jpg?ex=…&is=…&hm=…",
    "urlExpiraEn": "2026-09-29T21:28:59.000Z"
  }],
  "fijado": true
}
```

**Un logro con reacción** (canal `logros`)
```json
{
  "id": "1554205393054466139",
  "canal": { "id": "1554158272867467374", "nombre": "logros" },
  "autor": { "id": "sim-camila-rojas", "…": "…" },
  "textoOriginal": "me contrataron!!!!! después de 6 meses en el bootcamp y 40 postulaciones, empiezo el lunes como QA trainee. No se rindan 🙌🙌",
  "reacciones": [{ "emoji": "🎉", "emojiId": null, "cantidad": 1 }]
}
```

**Resultado del prototipo:** los 38 mensajes se convierten sin errores. Los 7 alumnos simulados y el mentor quedan con **un solo ID cada uno en los dos canales**; antes, con el ID de Discord, Ana tenía un ID distinto en cada canal.

## 8. Decisiones para validar

| # | Decisión | Propuesta | Por qué |
|---|---|---|---|
| 1 | Identidad de los alumnos simulados | `autor.id` = `sim-` más el nombre normalizado | Probado: da un ID estable en todos los canales |
| 2 | Rol del autor (mentor o *staff*) | Una lista configurada: IDs de Discord en producción y nombres en la simulación | No se extraen datos de los miembros, pero A8, C2 y H1 necesitan reconocer a los mentores |
| 3 | URL del adjunto | Se incluye, junto con `urlExpiraEn` | El bot en vivo puede usar la imagen (A3) porque la URL es reciente; en lotes quizá ya venció, y por eso se informa cuándo. **Cambia lo que decía la guía §12 ("sin la URL")** |
| 4 | Avisos del sistema | Se envían marcados como `avisoSistema`, sin filtrarlos | La ingesta no decide qué es relevante; filtrar es trivial para quien consume |
| 5 | Mención al bot | `mencionaAlBot` cubre al bot y a su rol | Hallazgo de la prueba real: al escribir `@` se elige fácilmente el rol. Requiere conocer el ID del rol del bot, que se obtiene con una petición a la lista de roles del servidor |
| 6 | Encuesta y vistas previas | Se definen según la documentación | Todavía sin muestras reales (ver §4.8) |

## 9. Próximos pasos

1. **Validar este borrador** (tú).
2. **Comparar con backend (3.6):** poner este contrato al lado de su DTO y conversar las diferencias en las dos direcciones.
3. **Programar:** el modelo `pydantic` que genera el JSON Schema, la transformación de `data/raw/` al contrato y la validación de todos los mensajes.
