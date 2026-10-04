# Contrato Panel ↔ Java v1 — InsightEdu Lab

> **Estado:** v1.0 · **Fecha:** 2026-10-04 · **Tarea:** T07 · **Decisiones:** D6, DEC-70, DEC-110, DEC-111, DEC-112 y DEC-113

## 0. Sobre este documento

**Qué es.** Las puertas de la API Java que usa el panel de curaduría para listar, editar, aprobar o rechazar borradores, y para reintentar lo que quedó en `ERROR`.

**Para quién.**
- Quien mantenga el panel (`panel/`, sobre todo `panel/cliente_java.py`).
- Quien mantenga las puertas en Java (`BorradorController`, `ErroresController` y el paquete `curaduria/`).

**La regla principal (DEC-112).** El panel habla **solo con Java**. Nunca lee la base ni llama a la IA (regla 2 de la propuesta 3). Java es quien decide si un cambio se puede hacer.

**Fuentes de verdad.** Si este documento y el código no coinciden, manda el código.

| Qué | Dónde |
|---|---|
| Formas de pedidos y respuestas | [VistasPanel.java](../../backend-java/src/main/java/com/insightedulab/backend_java/curaduria/VistasPanel.java) |
| Reglas | [CuraduriaService.java](../../backend-java/src/main/java/com/insightedulab/backend_java/curaduria/CuraduriaService.java) |
| SQL | [CuraduriaRepository.java](../../backend-java/src/main/java/com/insightedulab/backend_java/curaduria/CuraduriaRepository.java) y la migración `V6__curaduria.sql` |
| Pruebas | `CuraduriaApiTest.java` |

## 1. Cabeceras

| Cabecera | Cuándo | Qué lleva |
|---|---|---|
| `X-Api-Key` | **Siempre** | La clave `API_KEY_PANEL`. Se genera con `python scripts/generar_api_key.py --cliente panel`. **Solo esta clave abre estas puertas**, y no abre ninguna otra (DEC-70) |
| `X-Usuario` | En **todo cambio** (`PUT` y `POST`) | El usuario que inició sesión en el panel, por ejemplo `harrison`. Solo letras sin tilde, números, `.`, `_` y `-`, de 1 a 40 caracteres. Si falta o no cumple: `422`. Java confía en él porque solo el panel tiene la clave, y lo guarda como `aprobado_por` o `rechazado_por` |
| `Content-Type` | Con cuerpo | `application/json` |
| `Content-Length` | En `POST` y `PUT` | Obligatoria (si falta, `411`). `httpx` la envía siempre con `json=` |
| `X-Id-Correlacion` | Opcional | Java la devuelve en la respuesta y la escribe en su registro |

Dentro de Docker, Java está en `http://api-java:8080` (variable `PANEL_JAVA_URL` del panel).

## 2. Las puertas

| # | Método y ruta | Para qué |
|---|---|---|
| 1 | `GET /api/v1/borradores?estado=&tipo=&limite=` | Listar borradores |
| 2 | `GET /api/v1/borradores/{id}` | Ver un borrador con su contexto |
| 3 | `PUT /api/v1/borradores/{id}` | Guardar una edición, sin aprobar |
| 4 | `POST /api/v1/borradores/{id}/aprobar` | Aprobar (con la edición en el mismo paso, si la hay) |
| 5 | `POST /api/v1/borradores/{id}/rechazar` | Rechazar |
| 6 | `GET /api/v1/errores` | Listar lo que quedó en `ERROR` |
| 7 | `POST /api/v1/errores/clasificacion/{mensajeId}/reintentar` | Devolver una clasificación a la cola |
| 8 | `POST /api/v1/errores/generacion/{mensajeId}/reintentar` | Devolver una generación a la cola |

Los borradores `RESPUESTA_BOT` no pasan por el panel: lo que responde el bot no se aprueba (D3, DEC-66).

### 2.1 Listar borradores

| Parámetro | Valores | Si no viene |
|---|---|---|
| `estado` | `PENDIENTE`, `APROBADO` o `RECHAZADO` | `PENDIENTE` |
| `tipo` | `POST_LINKEDIN`, `CASO_EXITO` o `FAQ` | Todos |
| `limite` | 1 a 500 | 100 |

Los pendientes vienen del más antiguo al más nuevo (se atienden en orden). Los aprobados y los rechazados, el último revisado primero.

```
GET /api/v1/borradores?estado=PENDIENTE
```
```json
{
  "borradores": [
    {
      "id": 1,
      "tipo": "POST_LINKEDIN",
      "estado": "PENDIENTE",
      "creadoEn": "2026-10-04T15:02:11.120Z",
      "extracto": "🎉 Camila empieza su primer trabajo en tecnología…",
      "autorNombre": "Camila Rojas",
      "canal": "logros",
      "semana": null,
      "revisadoPor": null,
      "revisadoEn": null
    },
    {
      "id": 11,
      "tipo": "FAQ",
      "estado": "PENDIENTE",
      "creadoEn": "2026-10-04T17:40:00.000Z",
      "extracto": "Preguntas frecuentes de la semana…",
      "autorNombre": null,
      "canal": null,
      "semana": "2026-W40",
      "revisadoPor": null,
      "revisadoEn": null
    }
  ]
}
```

`extracto` son los primeros 160 caracteres del texto final (o del de la IA, si no se editó). `revisadoPor` y `revisadoEn` dicen quién aprobó o rechazó, y cuándo.

### 2.2 Ver un borrador

```
GET /api/v1/borradores/1
```
```json
{
  "id": 1,
  "tipo": "POST_LINKEDIN",
  "estado": "PENDIENTE",
  "requiereConsentimiento": true,
  "textoIa": "🎉 Camila empieza su primer trabajo en tecnología… #CommunityLab",
  "textoFinal": null,
  "consentimientoConfirmado": false,
  "creadoEn": "2026-10-04T15:02:11.120Z",
  "aprobadoPor": null,
  "aprobadoEn": null,
  "tiempoCuraduriaSeg": null,
  "rechazadoPor": null,
  "rechazadoEn": null,
  "motivoRechazo": null,
  "motivoIa": "Es una contratación.",
  "origen": {
    "discordId": "1554243551888416798",
    "canal": "logros",
    "fecha": "2026-09-28T18:58:11.331Z",
    "texto": "me contrataron!!! empiezo el lunes como QA trainee",
    "autorNombre": "Camila Rojas"
  },
  "faq": null
}
```

| Campo | Qué es |
|---|---|
| `requiereConsentimiento` | `true` en `POST_LINKEDIN` y `CASO_EXITO`: nombran al alumno (D6). `false` en la FAQ |
| `textoFinal` | La edición guardada, o `null` si nadie editó |
| `motivoIa` | En un post o un caso de éxito, por qué la IA lo vio publicable (`mensajes.generacion_motivo`). En la FAQ, el resumen de la semana (`faq_semanas.motivo`) |
| `origen` | El mensaje de Discord que dio origen al borrador. `autorNombre` es el `nombreVisible` del contrato v1. `null` en la FAQ, que junta muchas dudas |
| `faq` | Solo en la FAQ: `{ "semana": "2026-W40", "desde": "…", "hasta": "…", "motivo": "…" }` |

### 2.3 Editar

```
PUT /api/v1/borradores/1
X-Usuario: harrison

{ "textoFinal": "🎉 Camila empieza su primer trabajo como QA…" }
```

Responde `200` con el borrador como en §2.2. El texto no puede estar vacío y tiene un máximo de 20 000 caracteres. Java le quita el carácter NUL, que PostgreSQL no acepta.

### 2.4 Aprobar

```
POST /api/v1/borradores/1/aprobar
X-Usuario: harrison

{ "consentimiento": true, "tiempoCuraduriaSeg": 95, "textoFinal": "…opcional…" }
```

| Campo | Obligatorio | Qué es |
|---|---|---|
| `consentimiento` | Sí en `POST_LINKEDIN` y `CASO_EXITO` | La casilla "el alumno dio su consentimiento" (D6) |
| `tiempoCuraduriaSeg` | Sí | Segundos desde que se abrió el borrador en el panel (0 a 604 800) |
| `textoFinal` | No | Si viene, se guarda la edición y se aprueba **en el mismo paso** |

Responde `200` con el borrador ya `APROBADO`. Queda guardado:

| Columna | Valor |
|---|---|
| `estado` | `APROBADO` |
| `texto_final` | El `textoFinal` del pedido, si vino. Si no, la última edición guardada. Si nadie editó, igual a `texto_ia` |
| `consentimiento_confirmado` | El `consentimiento` del pedido |
| `aprobado_por` / `aprobado_en` | `X-Usuario` y la hora de Java |
| `tiempo_curaduria_seg` | El del pedido |

Aprobar **solo cambia el estado en la base** (DEC-113): subir lo aprobado a OCI es la tarea T09.

### 2.5 Rechazar

```
POST /api/v1/borradores/4/rechazar
X-Usuario: harrison

{ "motivo": "Repite el post de ayer", "tiempoCuraduriaSeg": 20 }
```

Los dos campos son opcionales, y el cuerpo puede ser `{}`. `motivo` admite hasta 500 caracteres. Responde `200` con el borrador ya `RECHAZADO`, y guarda `rechazado_por`, `rechazado_en`, `motivo_rechazo` y `tiempo_curaduria_seg` (columnas de la V6).

### 2.6 Lo que quedó en `ERROR`

```
GET /api/v1/errores
```
```json
{
  "clasificacion": [
    {
      "mensajeId": 17,
      "discordId": "1554205178671009863",
      "canal": "dudas",
      "fecha": "2026-09-29T14:10:00Z",
      "autorNombre": "Ana Pérez",
      "extracto": "no me deja instalar python…",
      "intentos": 3,
      "motivo": null
    }
  ],
  "generacion": [
    {
      "mensajeId": 22,
      "discordId": "1554243551888416798",
      "canal": "logros",
      "fecha": "2026-09-28T18:58:11.331Z",
      "autorNombre": "Camila Rojas",
      "extracto": "me contrataron!!!…",
      "intentos": 3,
      "motivo": "La IA respondió HTTP 500"
    }
  ]
}
```

Hasta 200 de cada lista, la más reciente primero. La clasificación no guarda el motivo del error (solo queda en el registro de `api-java`), así que su `motivo` es `null`.

### 2.7 Reintentar (DEC-111)

```
POST /api/v1/errores/clasificacion/17/reintentar
X-Usuario: harrison

{}
```
```json
{ "mensajeId": 17, "etapa": "clasificacion", "estado": "PENDIENTE" }
```

| Puerta | Qué cambia en `mensajes` | Quién lo toma después |
|---|---|---|
| `…/clasificacion/{id}/reintentar` | `estado_clasificacion = PENDIENTE`, `intentos_clasificacion = 0`, sin reserva | La clasificación en segundo plano (T04), en su vuelta siguiente (cada 30 s) |
| `…/generacion/{id}/reintentar` | `generacion_estado = NULL` ("sin generar"), `generacion_intentos = 0`, sin motivo ni reserva. La respuesta dice `"estado": "SIN_GENERAR"` | La generación del Agente-Mod (T06), en su vuelta siguiente (cada 60 s) |

El cuerpo `{}` está para que el pedido lleve `Content-Length` (§1).

## 3. Reglas

1. **Solo se cambian los `PENDIENTE`.** Editar, aprobar o rechazar un borrador que ya está `APROBADO` o `RECHAZADO` da `409`.
2. **Dos personas a la vez: gana la primera.** Cada cambio es un solo `UPDATE … WHERE id = :id AND estado = 'PENDIENTE'`. Si dos personas aprueban o rechazan el mismo borrador a la vez, PostgreSQL bloquea la fila: la segunda ya no la encuentra `PENDIENTE`, no cambia nada y recibe `409`. Lo guardado es todo de la primera (usuario, texto y tiempo).
3. **Consentimiento (D6).** Un `POST_LINKEDIN` o un `CASO_EXITO` sin `"consentimiento": true` da `422` y sigue `PENDIENTE`. La FAQ no lo necesita, porque no nombra alumnos (DEC-100). La V6 lo impide también en la base (`borradores_consentimiento_check`): son dos capas.
4. **Ediciones.** Si dos personas editan a la vez (`PUT`), queda la última que guardó. Para evitar que se pierda una edición al aprobar, el panel envía el texto en el mismo `aprobar`.
5. **Reintentar** solo funciona si el mensaje sigue en `ERROR`. Si no, `409`.
6. El registro de Java nunca lleva textos de alumnos ni de la IA (S11): solo ids, tipos y el usuario del panel.

## 4. Errores

Todos usan el formato común de Java (`ErrorApi`, [JAVA_IA_v1.md §7](JAVA_IA_v1.md)):

```json
{
  "codigo": "DATO_INVALIDO",
  "mensaje": "Este borrador nombra a un alumno: hay que confirmar su consentimiento antes de aprobarlo (D6).",
  "errores": [ { "campo": "consentimiento", "problema": "…" } ],
  "idCorrelacion": "…"
}
```

| Código HTTP | `codigo` | Cuándo |
|---|---|---|
| `401` | `NO_AUTORIZADO` | Falta `X-Api-Key` o la clave no es de ningún cliente |
| `403` | `PROHIBIDO` | La clave es de otro cliente (`ingesta` o `bot`), también si escribe la ruta de otra forma (`;x=1`, `%65`, `//`) |
| `404` | `NO_ENCONTRADO` | El borrador o el mensaje no existe |
| `409` | `CONFLICTO` | El borrador ya no está `PENDIENTE`, o el mensaje ya no está en `ERROR` |
| `411` | `LONGITUD_REQUERIDA` | Un `POST` o `PUT` sin `Content-Length` |
| `422` | `DATO_INVALIDO` | Falta el consentimiento (D6), `X-Usuario` falta o no cumple el formato, el texto está vacío o es muy largo, falta `tiempoCuraduriaSeg`, o un filtro (`estado`, `tipo`, `limite`, `id`) no es válido |

## 5. CORS (S6)

Java **no** responde cabeceras CORS: se quitó `CorsConfig`, que aceptaba cualquier origen con credenciales. El panel llama a Java **desde su servidor** (el proceso de Streamlit), nunca desde el navegador, así que no las necesita. Un navegador en otra página no puede leer las respuestas de Java.

## 6. Fuera de este contrato

- Subir lo aprobado a OCI (T09, DEC-113). El dashboard (T08).
- Volver a generar un borrador, reintentar una semana de la FAQ en `ERROR` y publicar en LinkedIn.
- Roles o permisos distintos por usuario: todos los usuarios del panel pueden hacer todo.
