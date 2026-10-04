# Contrato Java ↔ IA v1 — InsightEdu Lab

> **Estado:** v1.0 · **Fecha:** 2026-10-03 · **Tarea:** T02 · **Lo implementa del lado Java:** T04
> **Cambio de T04 (2026-10-04, validado por Harrison):** `/v1/procesar` exige `X-Api-Key` (S2) y hay un código de error más, `NO_AUTORIZADO` (401). Es un cambio que solo agrega: nada de lo anterior cambió.
> **Cambio de T05 (2026-10-04, DEC-54):** en `tiempoReal`, todo el pedido tiene un **tope de 25 s** (`TIEMPO_REAL_TOPE_S`, §6). Si se agota, la duda llega con sus etiquetas y `respuesta.encontrada = false`. Solo agrega: ningún campo cambió. Además se quitó la puerta vieja `POST /procesar`.
> **Cambio de T06 (2026-10-04, DEC-82):** una puerta nueva, **`POST /v1/generar`**: el Agente-Mod redacta un post de LinkedIn y un caso de éxito a partir de un logro (§9). Solo agrega: `/v1/procesar` no cambió.
> **Cambio de T06b (2026-10-04, DEC-97):** una puerta nueva, **`POST /v1/faq`**: con las dudas de la semana, la IA arma un borrador de preguntas frecuentes (§10). Solo agrega: `/v1/procesar` y `/v1/generar` no cambiaron.

## 0. Sobre este documento

**Qué es.** El formato en que la API Java le pide a la IA que etiquete mensajes, y en que la IA le contesta.

**Para quién.**
- Quien programe en Java la llamada a la IA (`NlpDataClient`, tarea T04).
- Quien mantenga la IA (`agents/orquestador/`).

**Fuentes de verdad.** Si este documento y el código no coinciden, manda el código.

| Qué | Dónde |
|---|---|
| Entrada | El **contrato v1** de la ingesta: [CONTRACT.md](../../ingestion/discord/docs/CONTRACT.md), [contract.py](../../ingestion/discord/contract.py) y [contract_v1.schema.json](../../ingestion/discord/schema/contract_v1.schema.json). La IA importa `contract.py`: no tiene una copia |
| Salida | [contrato_ia.py](../../agents/orquestador/contrato_ia.py) y su JSON Schema, [JAVA_IA_v1.schema.json](JAVA_IA_v1.schema.json), que se genera desde el código |
| Flujo | [grafo_v1.py](../../agents/orquestador/grafo_v1.py), un grafo de LangGraph |

Para regenerar el schema después de cambiar los modelos, desde la raíz del repositorio:

```
python -m agents.orquestador.contrato_ia
```

Una prueba falla si el archivo publicado y los modelos no coinciden.

## 1. La puerta

| Dato | Valor |
|---|---|
| Método y ruta | `POST /v1/procesar` |
| Dentro de Docker | `http://ia:8000/v1/procesar` (la variable `PYTHON_NLP_URL` de Java ya apunta a `http://ia:8000`) |
| Cuerpo | Un **lote del contrato v1**, tal cual: `versionContrato`, `loteId`, `fuente`, `modo`, `servidorId`, `generadoEn` y `mensajes`. Cada mensaje es la "caja" que Java guarda en `mensajes.contrato` |
| Cabecera obligatoria | `X-Api-Key`: la clave `API_KEY_IA` (S2). La genera `python scripts/generar_api_key.py --cliente ia`. Sin ella, o con otra: `401` |
| Cabecera opcional | `X-Id-Correlacion`: la IA la devuelve en los errores. Java pone el `loteId` de la tanda |
| Respuesta | `200` con los resultados, `401` sin clave válida, `422` si el lote no cumple el contrato, `500` si falló la IA por completo |
| Tiempos | Cada llamada al LLM tiene un tope de **20 s** (`LLM_TIMEOUT_S`). Ver la sección 6 |

`POST /procesar`, **sin** `/v1`, era la puerta vieja del bot. **Se quitó en T05** (responde `404`): ahora el bot pasa por Java (C2, [BOT_JAVA_v1.md](BOT_JAVA_v1.md)).

## 2. Qué hace la IA con cada mensaje

| Mensaje | Qué hace | Resultado |
|---|---|---|
| `autor.tipo = persona` (incluye `esSimulado = true`) y con texto | **Una** llamada al LLM, que devuelve intención, confianza, razón, sentimiento y tema | `estado = OK`, `metodo = llm` |
| `autor.tipo = botPropio` u `otroBot` | No llama al LLM | `OK`, `regla`, `OTRO`, confianza `1.0`, sin sentimiento ni tema |
| `tipo = avisoSistema` | No llama al LLM | Igual que el anterior |
| `textoOriginal` vacío (por ejemplo, solo una imagen) | No llama al LLM | Igual que el anterior |
| El LLM falla o no responde a tiempo | 1 reintento, salvo que se haya agotado el tiempo | `estado = ERROR`, **sin etiquetas** (F4) |
| `PREGUNTA_FAQ` en modo `tiempoReal` | Además, le pregunta al Agente FAQ, con el tiempo que queda del tope (§6) | Trae `respuesta` |
| `PREGUNTA_FAQ` en modo `historial` | Nada más: no se gasta en respuestas | `respuesta = null` |
| `TESTIMONIO` | Solo se etiqueta. Los borradores los pide Java después, en otra puerta: `POST /v1/generar` (§9) | — |

La IA **no** guarda nada ni sube nada a OCI (D2): eso le toca a Java.

## 3. Ejemplo

**Entrada** (un lote en tiempo real, con una duda; se acortaron algunos campos repetidos)

```json
{
  "versionContrato": "1.0",
  "loteId": "3f2b8c1e-0d4a-4b7e-9a51-6c2f0e8d9b10",
  "fuente": "discord",
  "modo": "tiempoReal",
  "servidorId": "1554157903701741700",
  "generadoEn": "2026-09-29T15:00:00.000Z",
  "mensajes": [
    {
      "id": "1554205178671009863",
      "canal": { "id": "1554158212742127821", "nombre": "dudas" },
      "hilo": null,
      "fecha": "2026-09-28T18:56:30.331Z",
      "tipo": "mensaje",
      "tipoDiscord": 0,
      "esSimulado": true,
      "autor": { "id": "sim-ana-perez", "idDiscord": "1554160711800717417", "nombreUsuario": "Ana Pérez",
                 "nombreVisible": "Ana Pérez", "tipo": "persona", "rol": "miembro" },
      "textoOriginal": "como instalo pyhton en windows?? me sale que pip no se reconoce como comando 😭",
      "tieneTexto": true, "tieneBloqueCodigo": false, "enlaces": [],
      "menciones": { "usuarios": [], "roles": [], "todos": false },
      "mencionaAlBot": false, "respondeA": null, "adjuntos": [], "reacciones": [],
      "fijado": false, "editado": false, "editadoEn": null,
      "stickers": [], "vistasPrevias": [], "encuesta": null
    }
  ]
}
```

**Salida**

```json
{
  "versionContratoIa": "1.0",
  "loteId": "3f2b8c1e-0d4a-4b7e-9a51-6c2f0e8d9b10",
  "resultados": [
    {
      "discordId": "1554205178671009863",
      "estado": "OK",
      "metodo": "llm",
      "intencion": "PREGUNTA_FAQ",
      "confianza": 0.93,
      "sentimiento": "NEGATIVO",
      "tema": "herramientas_entorno",
      "razon": "Pide ayuda para instalar Python y resolver un error de pip.",
      "respuesta": {
        "texto": "Al instalar Python marca la casilla 'Add python.exe to PATH'…",
        "encontrada": true,
        "fuentes": ["06_Manual_del_Estudiante_V3.pdf (Pág. 4)"],
        "motivo": null
      }
    }
  ],
  "metricas": { "duracionMs": 4210, "tokensIn": 812, "tokensOut": 64 }
}
```

**Un error del LLM** (en el mismo formato, dentro de `resultados`)

```json
{ "discordId": "1554205393054466139", "estado": "ERROR", "metodo": "llm",
  "intencion": null, "confianza": null, "sentimiento": null, "tema": null,
  "razon": "El LLM no respondió en 20 s.", "respuesta": null }
```

## 4. Campos de la salida

### 4.1 La respuesta

| Campo | Tipo | Nota |
|---|---|---|
| `versionContratoIa` | `"1.0"` | Cambia si cambia este formato |
| `loteId` | texto | El `loteId` recibido |
| `resultados` | lista | **Exactamente uno por mensaje**, en el mismo orden del lote |
| `metricas.duracionMs` | entero | Lo que tardó todo el lote dentro de la IA |
| `metricas.tokensIn`, `tokensOut` | entero | Solo los del clasificador: el Agente FAQ no informa los suyos |

### 4.2 Cada resultado

| Campo | Tipo | Columna en Java (`V1__modelo_inicial.sql`) | Nota |
|---|---|---|---|
| `discordId` | texto | `mensajes.discord_id` | El `id` del mensaje |
| `estado` | `OK` \| `ERROR` | `mensajes.estado_clasificacion` | Ver la sección 5 |
| `metodo` | `llm` \| `palabrasClave` \| `regla` | — (opcional guardarlo) | Quién decidió. `regla` = no pasó por el LLM |
| `intencion` | `TESTIMONIO` \| `PREGUNTA_FAQ` \| `COMENTARIO` \| `OTRO` o `null` | `mensajes.intencion` | `null` solo si `ERROR` |
| `confianza` | número de 0 a 1 o `null` | `mensajes.confianza` | `null` solo si `ERROR` |
| `sentimiento` | `MUY_POSITIVO` \| `POSITIVO` \| `NEUTRO` \| `NEGATIVO` \| `MUY_NEGATIVO` o `null` | `mensajes.sentimiento` | `null` si `ERROR` o `regla` |
| `tema` | uno de la lista de 4.3, o `null` | `mensajes.tema` | `null` si `ERROR` o `regla` |
| `razon` | texto | — (registro) | Por qué esa intención, o el motivo del error o de la regla |
| `respuesta` | objeto o `null` | — (el bot la publica) | Solo en `tiempoReal` y para `PREGUNTA_FAQ` con `estado = OK` |

**`respuesta`**

| Campo | Tipo | Nota |
|---|---|---|
| `texto` | texto | Lo que el bot publicaría. Puede estar vacío |
| `encontrada` | booleano | **D3: el bot publica `texto` solo si es `true`.** Si es `false`, deriva a un mentor. Una respuesta con fidelidad media cuenta como `false` |
| `fuentes` | lista de textos | Documento y página |
| `motivo` | texto o `null` | Por qué no se encontró, o por qué requiere revisión |

### 4.3 Lista cerrada de temas

Validada por Harrison el 2026-10-03. Está pensada para que el dashboard pueda contar mensajes por tema (N5).

| Tema | Qué incluye |
|---|---|
| `inscripciones` | Matrícula, requisitos de ingreso, cupos |
| `becas_pagos` | Becas, cuotas, pagos, descuentos |
| `calendario_clases` | Horarios, clases en vivo, fechas del calendario académico |
| `evaluaciones` | Challenges, entregas, plazos, notas, apelaciones |
| `contenido_curso` | Dudas de teoría o de la materia (listas, recursividad, SQL…) |
| `herramientas_entorno` | Instalar y configurar herramientas, errores de entorno o de compilación, git |
| `plataforma_acceso` | Acceso a la plataforma, a la cuenta o al campus virtual |
| `proyectos` | Proyectos propios, repositorios, portafolio, deploy |
| `empleo` | Entrevistas, contrataciones, búsqueda laboral |
| `comunidad` | Saludos, agradecimientos, motivación, apoyo entre compañeros |
| `otro` | Nada de lo anterior |

`V1__modelo_inicial.sql` dejó `sentimiento` y `tema` sin `CHECK`, a la espera de esta lista. **T04 puede agregarlos en una migración `V2__…`** con estos valores.

## 5. Qué hace Java con cada resultado

| Resultado | Qué hace Java |
|---|---|
| `estado = OK` | Guarda `intencion`, `confianza`, `sentimiento` y `tema`. Pone `estado_clasificacion = 'OK'` y `clasificado_en = now()` |
| `estado = OK` y `metodo = regla` | Lo mismo: `sentimiento` y `tema` quedan en `null`. 🔎 El dashboard puede filtrar con `autor_tipo = 'persona'` |
| `estado = ERROR` | **No toca** las etiquetas. Suma un intento (`intentos_clasificacion`) y registra `razon`. Sigue `PENDIENTE` hasta el máximo (3); ahí pasa a `ERROR` y lo verá el panel (F4) |
| Trae `respuesta` con `encontrada = true` | En `tiempoReal`, la guarda en la fila del mensaje (`respuesta_estado = RESPONDIDA`, DEC-66) y le ordena al bot publicarla ([BOT_JAVA_v1.md](BOT_JAVA_v1.md)) |
| Trae `respuesta` con `encontrada = false` | Guarda `respuesta_estado = DERIVADA` y el bot avisa que un mentor revisará la duda. 🔎 Aparece en "dudas sin responder" (N5) |
| Error `422` | El lote está mal armado: es un error de programación y se registra. Solo los mensajes que señala `errores[].campo` (`mensajes.<i>.…`) suman un intento, y al máximo pasan a `ERROR`: no se reintenta sin fin. Si no se puede saber cuál es, suman todos |
| Error `401`, `500`, o la IA no responde | Los mensajes quedan `PENDIENTE`, suman un intento y se reintentan en la siguiente vuelta (F9) |

Así lo hace Java desde T04 (`ClasificacionService`): cada 30 s toma hasta 5 mensajes `PENDIENTE` y los envía en un lote `historial`. Un resultado se guarda solo si el mensaje no cambió mientras la IA lo procesaba (`actualizado_en`).

## 6. Tiempos (D4, F8)

| Pieza | Tiempo máximo |
|---|---|
| Cada llamada al LLM, del clasificador y del Agente FAQ | **20 s** (`LLM_TIMEOUT_S`). Si se agota, no se reintenta |
| Reintentos del clasificador por otros errores | **1** (`LLM_REINTENTOS`) |
| **Todo el pedido en `tiempoReal`** | **25 s** (`TIEMPO_REAL_TOPE_S`, DEC-54, T05). En `historial` no hay tope |
| Java → IA | 30 s de lectura y 5 s de conexión (`RestClientConfig`, T04) |
| Bot → Java | 40 s |

**El tope de `tiempoReal` (agregado en T05).** Una duda encadena hasta 3 llamadas al LLM: clasificar, generar la respuesta y el control anti-alucinación. Sin tope, la suma podía superar los 30 s de Java. Ahora clasificar y responder comparten 25 s:

| Si se agota… | Resultado |
|---|---|
| Mientras responde el Agente FAQ | Las etiquetas de la duda llegan bien, con `respuesta = {"texto": "", "encontrada": false, "fuentes": [], "motivo": "Se agotó el tope de 25 s del pedido en tiempo real."}`. El bot deriva al mentor |
| Mientras clasifica | `estado = ERROR`, sin etiquetas (F4), como cualquier otro error del LLM |

Así la respuesta llega antes de los 30 s de Java. 🔎 Python no puede detener un hilo: el Agente FAQ cortado termina su trabajo en segundo plano y su respuesta se descarta (sí gasta esa llamada a Gemini).

## 7. Errores

Todos usan el mismo formato y **nunca repiten los datos recibidos** (S7).

```json
{
  "codigo": "CONTRATO_INVALIDO",
  "mensaje": "El lote no cumple el contrato v1.",
  "errores": [
    { "campo": "mensajes.0.autor.tipo", "problema": "Input should be 'persona', 'botPropio' or 'otroBot'" },
    { "campo": "modo", "problema": "Field required" }
  ],
  "idCorrelacion": "abc-123"
}
```

| `codigo` | HTTP | Cuándo |
|---|---|---|
| `NO_AUTORIZADO` | 401 | Falta `X-Api-Key`, la clave no es la de `API_KEY_IA` o la IA no tiene clave configurada. Se revisa **antes** que el cuerpo |
| `CONTRATO_INVALIDO` | 422 | El cuerpo no es JSON o no cumple el contrato v1 |
| `ERROR_INTERNO` | 500 | Falló la IA por completo. El detalle queda en el registro del contenedor `ia` |

## 8. Fuera de este contrato

| Qué | Dónde se resuelve |
|---|---|
| Posts de LinkedIn y casos de éxito (Agente-Mod) | ✅ En `POST /v1/generar` (§9, T06) |
| FAQ semanal | ✅ En `POST /v1/faq` (§10, T06b) |
| Sacar a `/procesar` | ✅ Hecho en T05 |

## 9. `POST /v1/generar`: post de LinkedIn y caso de éxito (T06)

**Qué hace.** Recibe un logro (un mensaje con `intencion = TESTIMONIO`) y, si las hay, las respuestas que recibió. El **Agente-Mod** (`agents/agent_mod/`) decide si el logro **vale la pena publicarse** (DEC-53) y, si es así, redacta los dos borradores con la **guía de voz** de la institución ([agents/agent_mod/guia_de_voz.md](../../agents/agent_mod/guia_de_voz.md), DEC-84). Hace **una** llamada al LLM, con salida estructurada.

Es una puerta aparte de `/v1/procesar` (DEC-82): redactar no hace más lenta la clasificación. Nada se publica: Java guarda los borradores como `PENDIENTE` y Marketing los aprueba en el panel (N6).

### 9.1 La puerta

| Dato | Valor |
|---|---|
| Método y ruta | `POST /v1/generar` (dentro de Docker, `http://ia:8000/v1/generar`) |
| Cabecera obligatoria | `X-Api-Key` con `API_KEY_IA`, igual que `/v1/procesar` (S2) |
| Cabecera opcional | `X-Id-Correlacion`: vuelve en los errores |
| Respuesta | `200` con la decisión (también cuando el LLM falla: entonces `estado = ERROR`), `401`, `422` o `500`, con el formato común de error (§7) |
| Tiempo | Una sola llamada, con un tope de **25 s** (`MOD_TIMEOUT_S`) y sin reintento: cabe en los 30 s de lectura de Java. Si falla, Java la pide otra vez en la siguiente vuelta |
| Modelo | `MOD_MODEL_NAME` (DEC-85). Si está vacío, el mismo que clasifica. Mismo proveedor y clave (D5). Temperatura `MOD_TEMPERATURE` (0,7) |

### 9.2 El pedido

| Campo | Tipo | Nota |
|---|---|---|
| `versionContrato` | `"1.0"` | La versión del contrato v1 de las cajas |
| `pedidoId` | texto, de 1 a 100 caracteres | Lo pone Java; vuelve en la respuesta |
| `logro` | caja del contrato v1 | El mensaje del logro, tal cual está en `mensajes.contrato` |
| `respuestas` | lista de cajas del contrato v1 | Los mensajes con `respondeA` igual al `id` del logro. **Como máximo 20** (si son más, `422`). Puede ir vacía |

### 9.3 Qué ve el LLM (DEC-81)

El Agente-Mod **no** le envía la caja al LLM. Le envía solo:
- el **primer nombre** del autor, sacado de `autor.nombreVisible` ("Camila Rojas" → "Camila");
- el canal, el `textoOriginal` del logro (para la cita textual) y el total de reacciones con sus emojis;
- de cada respuesta, solo el `rol` de quien responde y su texto.

**Nunca** le llegan el nombre completo, `nombreUsuario`, los IDs ni los nombres de quienes respondieron. Las menciones de Discord (`<@123>`, `<@&123>`, `<#123>`) se cambian por `@alguien` antes de enviar. Como última defensa, si el borrador trae el nombre completo o el usuario del autor (por ejemplo, porque el alumno los escribió en su mensaje), se reemplazan por el primer nombre.

### 9.4 Ejemplo

**Pedido** (con las cajas acortadas)

```json
{
  "versionContrato": "1.0",
  "pedidoId": "gen-7c1d0a5e-3b2f-4e8a-9f61-2d4b8c0e1a77",
  "logro": {
    "id": "1556321890585419808",
    "canal": { "id": "1554158272867467374", "nombre": "logros" },
    "autor": { "id": "111111111111111111", "nombreVisible": "Camila Rojas", "tipo": "persona", "rol": "miembro", "…": "…" },
    "textoOriginal": "me contrataron!!!!! después de 6 meses en el bootcamp y 40 postulaciones, empiezo el lunes como QA trainee. No se rindan",
    "reacciones": [ { "emoji": "🎉", "emojiId": null, "cantidad": 12 } ],
    "…": "el resto de los campos del contrato v1"
  },
  "respuestas": [
    { "id": "1556321900000000001", "respondeA": "1556321890585419808",
      "autor": { "rol": "mentor", "…": "…" }, "textoOriginal": "felicitaciones!! 👏", "…": "…" }
  ]
}
```

**Respuesta: publicable**

```json
{
  "versionContratoIa": "1.0",
  "pedidoId": "gen-7c1d0a5e-3b2f-4e8a-9f61-2d4b8c0e1a77",
  "discordId": "1556321890585419808",
  "estado": "OK",
  "publicable": true,
  "motivo": "Es una contratación después de un proceso largo.",
  "postLinkedin": "🎉 Después de 6 meses de bootcamp y 40 postulaciones, Camila empieza su primer trabajo en tecnología…",
  "casoExito": "**Situación:** …
**Desafío:** …
**Logro:** …
**En sus palabras:** \"me contrataron!!!!! …\"
**Cierre:** …",
  "metricas": { "duracionMs": 6120, "tokensIn": 1450, "tokensOut": 520 }
}
```

**No publicable** y **error**

```json
{ "versionContratoIa": "1.0", "pedidoId": "gen-…", "discordId": "…", "estado": "OK",
  "publicable": false, "motivo": "Es un avance de aprendizaje del día a día.",
  "postLinkedin": null, "casoExito": null, "metricas": { "…": "…" } }

{ "versionContratoIa": "1.0", "pedidoId": "gen-…", "discordId": "…", "estado": "ERROR",
  "publicable": null, "motivo": "El LLM no respondió en 25 s.",
  "postLinkedin": null, "casoExito": null, "metricas": { "…": "…" } }
```

### 9.5 Campos de la respuesta

| Campo | Tipo | Nota |
|---|---|---|
| `versionContratoIa` | `"1.0"` | |
| `pedidoId` | texto | El recibido |
| `discordId` | texto | El `id` del logro |
| `estado` | `OK` \| `ERROR` | `ERROR`: el LLM falló, no respondió a tiempo, devolvió algo sin formato o marcó el logro como publicable sin escribir los dos textos. **Nunca** trae un borrador vacío ni a medias (F4) |
| `publicable` | booleano o `null` | `null` solo si `ERROR` |
| `motivo` | texto | Por qué es publicable o no, o el motivo del error (sin el detalle del proveedor: ese va al registro) |
| `postLinkedin`, `casoExito` | texto o `null` | Los dos, solo si `publicable = true`. Si no, `null` |
| `metricas` | objeto | `duracionMs`, `tokensIn` y `tokensOut` del Agente-Mod |

El JSON Schema está en [JAVA_IA_v1.schema.json](JAVA_IA_v1.schema.json), en la clave `generar` (`pedido` y `respuesta`).

### 9.6 Qué hace Java con cada respuesta

Lo hace la generación en segundo plano (`backend-java/.../generacion/`, T06): cada tanto toma los logros (`TESTIMONIO`, `OK`, de una persona) que todavía no tienen generación, de a pocos y con reserva, y los envía uno por uno.

| Respuesta | Qué guarda Java |
|---|---|
| `OK` y `publicable = true` | Dos filas en `borradores` (`POST_LINKEDIN` y `CASO_EXITO`), `PENDIENTE`, con `texto_ia` y los tokens; la generación del mensaje queda `GENERADO`. Todo en una transacción, y solo si el mensaje no cambió mientras la IA redactaba |
| `OK` y `publicable = false` | Ningún borrador. La generación queda `NO_PUBLICABLE`, con el motivo |
| `ERROR`, `422`, `500`, tiempo agotado o IA caída | Suma un intento y libera la reserva. Al máximo de intentos, `ERROR` |

## 10. `POST /v1/faq`: la FAQ semanal (T06b)

**Qué hace.** Recibe las dudas de los alumnos de los últimos días y arma **un borrador de preguntas frecuentes** con las que repitieron **al menos 2 personas distintas** (DEC-98). Lo hace `agents/agent_mod/faq_semanal.py`:

1. **Agrupa** las dudas que preguntan lo mismo, con **una** llamada al LLM. El LLM devuelve los grupos, una pregunta clara por grupo y una introducción corta con la [guía de voz](../../agents/agent_mod/guia_de_voz.md).
2. **Cuenta** las personas distintas de cada grupo con las claves opacas del pedido. Las cuenta el código, no el LLM. Descarta los grupos de menos de 2 personas.
3. **Busca la respuesta** de cada grupo (DEC-95):
   - si el bot ya respondió alguna duda del grupo, usa esa respuesta;
   - si no, le hace la pregunta del grupo al **buscador del Agente FAQ** y acepta la respuesta solo con `encontrada = true` (D3; una fidelidad media no cuenta, DEC-49).
4. **Arma el texto con código**:
   - las respuestas van tal cual: ningún LLM las reescribe ni les agrega datos (D3);
   - las preguntas sin respuesta van en una sección aparte (DEC-96).

No usa el historial interno del Agente FAQ (DEC-83): llama directo al buscador, que no guarda las preguntas. Nada se publica: Java guarda el borrador como `PENDIENTE` y Marketing lo aprueba en el panel (N6).

### 10.1 La puerta

| Dato | Valor |
|---|---|
| Método y ruta | `POST /v1/faq` (dentro de Docker, `http://ia:8000/v1/faq`) |
| Cabecera obligatoria | `X-Api-Key` con `API_KEY_IA`, igual que las otras puertas (S2) |
| Cabecera opcional | `X-Id-Correlacion`: vuelve en los errores |
| Respuesta | `200` con el resultado (también cuando no hay preguntas repetidas o el LLM falla: entonces `estado = ERROR`), `401`, `422` o `500`, con el formato común de error (§7) |
| Tiempo | Tope total de **120 s** (`FAQ_SEMANAL_TOPE_S`). La llamada que agrupa tiene **45 s** como máximo (`FAQ_AGRUPAR_TIMEOUT_S`) y no se reintenta. Cada consulta al Agente FAQ usa lo que queda del tope. **Java espera hasta 150 s**: más que el tope |
| Si se agota el tope | Los grupos que faltan van a la sección "sin respuesta", con el motivo "no se alcanzó a consultar los documentos". **Nunca** se inventa una respuesta ni queda un borrador a medias |
| Modelo | El del Agente-Mod (`MOD_MODEL_NAME`, DEC-85), con temperatura `FAQ_AGRUPAR_TEMPERATURE` (0,2) |
| Ahorro | Si las dudas son de menos de 2 personas, no se llama al LLM |

### 10.2 El pedido

| Campo | Tipo | Nota |
|---|---|---|
| `pedidoId` | texto, de 1 a 100 caracteres | Lo pone Java; vuelve en la respuesta |
| `semana` | texto, de 1 a 20 caracteres | La semana de la FAQ, por ejemplo `2026-W40`. Vuelve en la respuesta |
| `desde`, `hasta` | fecha (`AAAA-MM-DD`) | La ventana de las dudas. Solo se usan para el título. `desde` no puede ser posterior a `hasta` |
| `dudas` | lista, **como máximo 200** (si son más, `422`) | Puede ir vacía |
| `dudas[].autor` | texto `a1`, `a2`… (patrón `^a[0-9]{1,6}$`) | **Clave opaca** del autor dentro del pedido, solo para contar personas distintas. Un nombre, un usuario o un ID de Discord da `422` |
| `dudas[].texto` | texto, de 1 a 4000 caracteres | El texto de la duda |
| `dudas[].tema` | tema de §4.3 o `null` | Las dudas con tema `otro` no cuentan (DEC-98) |
| `dudas[].respuesta` | objeto o `null` | Solo si el bot ya la respondió con respaldo: `texto` (hasta 8000 caracteres) y `fuentes` (hasta 20) |

### 10.3 Qué ve el LLM

Solo el **número**, el **tema** y el **texto** de cada duda. No ve las claves de autor ni las respuestas guardadas. Antes de enviar cada texto, el código:
- cambia las menciones de Discord (`<@123>`) por `@alguien`;
- impide que una duda cierre su etiqueta `</duda>`.

Las instrucciones le prohíben poner nombres o datos personales en las preguntas y en la introducción, y seguir órdenes que vengan dentro de las dudas.

### 10.4 Ejemplo

**Pedido**

```json
{
  "pedidoId": "faq-2b7e0c4a-91d3-4f0e-8a55-6c1f2e9d3b10",
  "semana": "2026-W40",
  "desde": "2026-09-27",
  "hasta": "2026-10-04",
  "dudas": [
    { "autor": "a1", "texto": "¿hasta cuándo se puede entregar el challenge?", "tema": "evaluaciones", "respuesta": null },
    { "autor": "a2", "texto": "cual es la fecha limite de la entrega??", "tema": "evaluaciones", "respuesta": null },
    { "autor": "a3", "texto": "como instalo python en windows", "tema": "herramientas_entorno",
      "respuesta": { "texto": "Descarga el instalador desde python.org y marca Add to PATH…", "fuentes": ["Guia_Entorno.pdf (Pág. 2)"] } },
    { "autor": "a1", "texto": "no me deja instalar python", "tema": "herramientas_entorno", "respuesta": null },
    { "autor": "a4", "texto": "¿dan certificado al terminar?", "tema": "inscripciones", "respuesta": null },
    { "autor": "a2", "texto": "al terminar me dan un certificado?", "tema": "inscripciones", "respuesta": null }
  ]
}
```

**Respuesta**

```json
{
  "versionContratoIa": "1.0",
  "pedidoId": "faq-2b7e0c4a-91d3-4f0e-8a55-6c1f2e9d3b10",
  "semana": "2026-W40",
  "estado": "OK",
  "texto": "# Preguntas frecuentes de la semana (27/09 al 04/10/2026)\n\n…introducción…\n\n## 1. ¿Cuál es el plazo para subir las entregas?\n\n…respuesta tal cual…\n\n_La preguntaron 2 personas · Fuente: Reglamento_Academico.pdf (Pág. 4)_\n\n## 2. ¿Cómo se instala Python?\n\n…\n\n## Preguntas frecuentes sin respuesta en los documentos\n\n…\n\n- ¿Se entrega un certificado al terminar? (la preguntaron 2 personas)\n",
  "motivo": "3 preguntas repetidas, 2 con respuesta en los documentos.",
  "grupos": [
    { "pregunta": "¿Cuál es el plazo para subir las entregas?", "personas": 2, "respondida": true,
      "origen": "agenteFaq", "fuentes": ["Reglamento_Academico.pdf (Pág. 4)"], "motivo": null },
    { "pregunta": "¿Cómo se instala Python?", "personas": 2, "respondida": true,
      "origen": "bot", "fuentes": ["Guia_Entorno.pdf (Pág. 2)"], "motivo": null },
    { "pregunta": "¿Se entrega un certificado al terminar?", "personas": 2, "respondida": false,
      "origen": null, "fuentes": [], "motivo": "El contexto no cubre la pregunta." }
  ],
  "metricas": { "duracionMs": 38250, "tokensIn": 2210, "tokensOut": 240 }
}
```

**Sin preguntas repetidas** y **error**

```json
{ "versionContratoIa": "1.0", "pedidoId": "faq-…", "semana": "2026-W40", "estado": "OK", "texto": null,
  "motivo": "No hubo preguntas repetidas por al menos 2 personas.", "grupos": [], "metricas": { "…": "…" } }

{ "versionContratoIa": "1.0", "pedidoId": "faq-…", "semana": "2026-W40", "estado": "ERROR", "texto": null,
  "motivo": "El LLM no agrupó las dudas en 45 s.", "grupos": [], "metricas": { "…": "…" } }
```

### 10.5 Campos de la respuesta

| Campo | Tipo | Nota |
|---|---|---|
| `versionContratoIa` | `"1.0"` | |
| `pedidoId`, `semana` | texto | Los recibidos |
| `estado` | `OK` \| `ERROR` | `ERROR`: el LLM que agrupa falló, no respondió a tiempo o devolvió algo sin formato. Nunca trae texto ni grupos (F4) |
| `texto` | Markdown o `null` | El borrador. Hay texto **si y solo si** hay grupos. Si todos los grupos quedaron sin respuesta, igual hay borrador, con la sección "sin respuesta" |
| `motivo` | texto | Cuántas preguntas repetidas hubo y cuántas con respuesta, por qué no hay texto, o el error (sin el detalle del proveedor) |
| `grupos[]` | lista | De la más repetida a la menos repetida |
| `grupos[].pregunta` | texto | Escrita por el LLM, sin nombres |
| `grupos[].personas` | entero ≥ 2 | Personas distintas, contadas por el código |
| `grupos[].respondida` | booleano | `true` solo con respaldo en los documentos |
| `grupos[].origen` | `bot` \| `agenteFaq` \| `null` | `null` si no tiene respuesta |
| `grupos[].fuentes` | lista de textos | Solo el nombre del documento y la página (DEC-76), nunca la ruta |
| `grupos[].motivo` | texto o `null` | Por qué no tiene respuesta |
| `metricas` | objeto | `duracionMs` de todo el pedido; `tokensIn` y `tokensOut` solo de la llamada que agrupa (no incluye al Agente FAQ, igual que §4.1) |

El JSON Schema está en [JAVA_IA_v1.schema.json](JAVA_IA_v1.schema.json), en la clave `faq` (`pedido` y `respuesta`).

### 10.6 Qué hace Java con cada respuesta

Lo hace la tarea semanal (`backend-java/.../faqsemanal/`, T06b). La semana queda registrada en la tabla `faq_semanas`, que tiene una fila por semana y no permite dos.

| Respuesta | Qué guarda Java |
|---|---|
| `OK` con `texto` | Un borrador `FAQ`, `PENDIENTE`, sin `mensaje_id` (DEC-33), con los tokens. La semana queda `GENERADA`, con el id del borrador. Todo en una transacción |
| `OK` sin `texto` | Ningún borrador. La semana queda `SIN_REPETIDAS` y no se vuelve a intentar |
| `ERROR`, `422`, `500`, tiempo agotado o IA caída | Suma un intento. Se reintenta cada 30 minutos con la misma ventana de fechas; al tercer fallo, `ERROR` |
