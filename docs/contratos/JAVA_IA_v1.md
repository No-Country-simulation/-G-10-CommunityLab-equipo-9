# Contrato Java ↔ IA v1 — InsightEdu Lab

> **Estado:** v1.0 · **Fecha:** 2026-10-03 · **Tarea:** T02 · **Lo implementa del lado Java:** T04

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
| Cabecera opcional | `X-Id-Correlacion`: la IA la devuelve en los errores |
| Respuesta | `200` con los resultados, `422` si el lote no cumple el contrato, `500` si falló la IA por completo |
| Tiempos | Cada llamada al LLM tiene un tope de **20 s** (`LLM_TIMEOUT_S`). Ver la sección 6 |

⚠️ `POST /procesar`, **sin** `/v1`, es la puerta vieja del bot y tiene otro formato. Se quita cuando el bot pase por Java (C2).

## 2. Qué hace la IA con cada mensaje

| Mensaje | Qué hace | Resultado |
|---|---|---|
| `autor.tipo = persona` (incluye `esSimulado = true`) y con texto | **Una** llamada al LLM, que devuelve intención, confianza, razón, sentimiento y tema | `estado = OK`, `metodo = llm` |
| `autor.tipo = botPropio` u `otroBot` | No llama al LLM | `OK`, `regla`, `OTRO`, confianza `1.0`, sin sentimiento ni tema |
| `tipo = avisoSistema` | No llama al LLM | Igual que el anterior |
| `textoOriginal` vacío (por ejemplo, solo una imagen) | No llama al LLM | Igual que el anterior |
| El LLM falla o no responde a tiempo | 1 reintento, salvo que se haya agotado el tiempo | `estado = ERROR`, **sin etiquetas** (F4) |
| `PREGUNTA_FAQ` en modo `tiempoReal` | Además, le pregunta al Agente FAQ | Trae `respuesta` |
| `PREGUNTA_FAQ` en modo `historial` | Nada más: no se gasta en respuestas | `respuesta = null` |
| `TESTIMONIO` | Solo se etiqueta. El Agente-Mod llega en la fase 4 | — |

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
| `estado = ERROR` | **No toca** las etiquetas. Pone `estado_clasificacion = 'ERROR'` y registra `razon`. Más tarde lo reintenta y lo muestra en el panel (F4) |
| Trae `respuesta` con `encontrada = true` | En `tiempoReal`, se la devuelve al bot para publicar. Opcional: guardarla como borrador `RESPUESTA_BOT` |
| Trae `respuesta` con `encontrada = false` | El bot avisa que un mentor revisará la duda. 🔎 Aparece en "dudas sin responder" (N5) |
| Error `422` | El lote está mal armado: es un error de programación. No se reintenta; se registra con `idCorrelacion` |
| Error `500`, o la IA no responde | Los mensajes quedan `PENDIENTE` y se reintentan después (F9) |

## 6. Tiempos (D4, F8)

| Pieza | Tiempo máximo |
|---|---|
| Cada llamada al LLM, del clasificador y del Agente FAQ | **20 s** (`LLM_TIMEOUT_S`). Si se agota, no se reintenta |
| Reintentos del clasificador por otros errores | **1** (`LLM_REINTENTOS`) |
| Java → IA | 30 s (lo configura T04) |
| Bot → Java | 40 s |

⚠️ **Riesgo para T04.** En `tiempoReal`, una duda encadena hasta 3 llamadas al LLM: clasificar, generar la respuesta y el control anti-alucinación. Si las tres llegan a su tope, la suma supera los 30 s de Java. En la práctica, cada llamada tarda pocos segundos. Si Java corta a los 30 s, el mensaje queda `PENDIENTE` y se reintenta.

## 7. Errores

Los dos usan el mismo formato y **nunca repiten los datos recibidos** (S7).

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
| `CONTRATO_INVALIDO` | 422 | El cuerpo no es JSON o no cumple el contrato v1 |
| `ERROR_INTERNO` | 500 | Falló la IA por completo. El detalle queda en el registro del contenedor `ia` |

## 8. Fuera de este contrato

| Qué | Dónde se resuelve |
|---|---|
| Clave entre Java y la IA (S2) | T04 |
| Posts de LinkedIn y casos de éxito (Agente-Mod) | Fase 4 |
| FAQ semanal | Fase 4 |
| Sacar a `/procesar` | Cuando el bot pase por Java (C2) |
