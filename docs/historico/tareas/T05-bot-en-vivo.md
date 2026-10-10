# T05 · El bot pasa por Java: dudas respondidas en vivo

| Dato | Valor |
|---|---|
| Fase del plan | 3 · Clasificar y responder ([análisis §9](../ANALISIS_INGENIERIA_PROPUESTA_3.md#9-prioridades-y-orden)) |
| Objetivos | OE1 (captura **en vivo**) y OE4 (responder dudas en vivo con los PDFs) |
| Hallazgos que resuelve | C2, F5, F8, F9, S8, S10, S11 (bot), M3, DEC-54 y observaciones del [README](README.md) |
| Tamaño | L (Java, Python de la IA, bot y Docker) |
| Modelo de Claude recomendado | **Opus 5.5**: concurrencia con la clasificación en segundo plano, seguridad y tres piezas a la vez |
| Depende de | T03 ✅ (`ApiKeyFilter`, `LoteService`, formato de error) y T04 ✅ (`NlpDataClient`, `ClasificacionRepository` con su reserva y sus guardas). **Reutilizarlos** |
| Rama | `tarea/T05-bot-en-vivo` |
| Decisiones previas 👤 | Las 4 de la sección 1.1, **validadas por Harrison el 2026-10-04** (DEC-54, DEC-66, DEC-67 y DEC-68) |

## 1. Objetivo

Que un alumno escriba una duda en `#dudas` y el bot le responda en segundos con los PDFs de la institución, **pasando por Java**: Discord → bot → Java → IA → Java → bot (DEC-18). Java guarda cada mensaje en vivo, con sus etiquetas y con lo que respondió el bot, y la clasificación en segundo plano de T04 no lo vuelve a clasificar.

El bot queda como un servicio más de `docker compose`, solo en `#dudas` y `#logros`, sin poder mencionar a todo el servidor y sin escribir textos de alumnos en sus registros.

### 1.1 Decisiones previas 👤

| # | Pregunta | Decisión 👤 (2026-10-04) | Descartada |
|---|---|---|---|
| 1 | ¿Dónde se guarda lo que respondió el bot? (DEC-66) | **Columnas nuevas en `mensajes`** (migración `V3__…`): `respuesta_estado` (`RESPONDIDA` / `DERIVADA`), `respuesta_texto`, `respuesta_fuentes` y `respondido_en` | Una fila en `borradores` de tipo `RESPUESTA_BOT`: mezclaría la bandeja de aprobación (N6) con algo que no se aprueba (D3) |
| 2 | Tope total por pedido en la IA en `tiempoReal` (DEC-54) | **25 s.** Si se agota, la IA devuelve las etiquetas con `respuesta.encontrada = false` y el motivo, y el bot deriva al mentor | Sin tope, con tiempos de 60 s y 70 s: el alumno esperaría más de un minuto |
| 3 | ¿Qué hace el bot si Java o la IA fallan (no hay etiquetas)? (DEC-67) | **No responde nada** y lo registra (sin el texto). El lote de la hora rescata el mensaje y la duda aparece como "sin responder" | Responder "un mentor te responderá": el bot no sabe si era una duda o un "gracias" |
| 4 | ¿Quién decide qué hace el bot con cada mensaje? (DEC-68) | **Java**, con un contrato nuevo y chico, `docs/contratos/BOT_JAVA_v1.md`: Java devuelve una orden (`RESPONDER`, `DERIVAR`, `REACCIONAR` o `NADA`) y el bot solo la cumple | Que el bot decida con el resultado de la IA: las reglas quedarían repartidas entre dos piezas |

## 2. Contexto que hay que leer

| Qué | Dónde |
|---|---|
| El flujo en vivo de N1 y N4, y qué falta en el bot | [PDF de la propuesta 3](../propuesta-3/Propuesta_3_Arquitectura_InsightEdu.pdf), §6 (N1 y N4) |
| C2, F5, F8, F9, S8, S10, S11 y M3 | [Análisis](../ANALISIS_INGENIERIA_PROPUESTA_3.md) §2, §3 y §4 |
| D3 (el bot responde sin aprobación, solo con respaldo) y D4 (tiempos 20 / 30 / 40 s) | [DECISIONES.md](../../DECISIONES.md): DEC-19 y DEC-20 |
| El contrato Java ↔ IA: modo `tiempoReal`, campo `respuesta` (§4.2) y tiempos (§6) | [JAVA_IA_v1.md](../../contratos/JAVA_IA_v1.md) |
| El contrato v1 y su conversión desde el JSON de Discord | [CONTRACT.md](../../../ingestion/discord/docs/CONTRACT.md), `ingestion/discord/transform.py` (`a_contrato`, `armar_lote`, `Contexto`) y `extract.py` (cómo se arma el `Contexto`) |
| La reserva, las guardas por `actualizado_en` y el cliente de la IA | `backend-java/.../clasificacion/` y `client/NlpDataClient.java` ([T04-informe.md](T04-informe.md)) |
| La API key por cliente y el formato común de error | `backend-java/.../seguridad/ApiKeyFilter.java` y `error/` ([T03-informe.md](T03-informe.md)) |
| El bot de hoy (va directo a la puerta vieja `/procesar` de la IA) | `agents/bot_discord/bot_communitylab.py` |
| Observaciones que pasan a esta tarea: doble clasificación, "dudas sin responder", `Content-Length` | [README de tareas](README.md) |

## 3. Alcance: qué entra

### Parte A · Java y la IA

1. **Puerta en vivo en Java:** `POST /api/v1/mensajes/en-vivo`.
   - Recibe un **lote del contrato v1** con `modo = tiempoReal` y **exactamente un** mensaje (si no, 422). Reutiliza la validación de `LoteService`, la limpieza del carácter NUL y el upsert de T03.
   - **Solo la acepta el cliente `bot`** (`seguridad.api-keys.bot`, variable `API_KEY_BOT`); los demás clientes reciben 403. De paso, `POST /api/v1/lotes` queda **solo para el cliente `ingesta`**. El nombre del cliente ya lo deja `ApiKeyFilter` en el pedido.
   - El mensaje en vivo **no** se registra en `lotes_recibidos`: un mensaje se reconoce por su `discord_id`.
2. **Sin doble clasificación** (observación de T04): el upsert y la reserva (`reservado_hasta`) ocurren **en la misma transacción**, así que la clasificación en segundo plano no puede tomar el mensaje mientras se procesa en vivo. La IA se llama **sin transacción abierta**, y los resultados se guardan con las mismas guardas de T04 (`actualizado_en` y estado `PENDIENTE`).
3. **Llamada a la IA** con `modo = tiempoReal`, reutilizando `NlpDataClient` (lectura de 30 s, D4).
4. **Qué guarda Java y qué orden le devuelve al bot** (decisiones 1 y 4):

   | Resultado de la IA | Se guarda | Orden para el bot |
   |---|---|---|
   | `PREGUNTA_FAQ` con `respuesta.encontrada = true` | Etiquetas `OK` y `respuesta_estado = RESPONDIDA`, con texto, fuentes y `respondido_en` | `RESPONDER`, con el texto y las fuentes |
   | `PREGUNTA_FAQ` con `encontrada = false`, incluido el tope agotado | Etiquetas `OK` y `respuesta_estado = DERIVADA` | `DERIVAR` (el bot avisa que un mentor responderá) |
   | `TESTIMONIO` | Etiquetas `OK` | `REACCIONAR` (🎉, **sin texto**: F5) |
   | `COMENTARIO` u `OTRO` | Etiquetas `OK` | `NADA` |
   | `ERROR` en el mensaje, 500, tiempo agotado o IA caída | Lo mismo que en T04: suma un intento, sigue `PENDIENTE` y **se libera la reserva** para que lo clasifique la tarea en segundo plano | `NADA` (decisión 3) |

5. **Un mensaje no se responde dos veces:** si ya tiene `respuesta_estado`, o ya no está `PENDIENTE`, Java devuelve `NADA` sin llamar a la IA.
6. **Migración `V3__…`** con las columnas de la decisión 1 (`CHECK` en `respuesta_estado`). El upsert de la ingesta **no** las toca. Nunca editar V1 ni V2.
7. **Contrato Bot ↔ Java v1** (decisión 4): `docs/contratos/BOT_JAVA_v1.md`, con un ejemplo de pedido y de respuesta, los códigos de error y los tiempos. Lo que el bot envía es el contrato v1 tal cual: **no se inventa otro formato de mensaje**.
8. **Tope total en la IA para `tiempoReal`** (decisión 2): variable `TIEMPO_REAL_TOPE_S` (25 por defecto). Si la clasificación y el Agente FAQ juntos lo superan, la respuesta llega con las etiquetas y `respuesta = {encontrada: false, motivo: …}`, a tiempo para los 30 s de Java. Se documenta en `JAVA_IA_v1.md` §6: **solo agrega**, no cambia ningún campo.
9. **Quitar la puerta vieja `/procesar`** de `agents/orquestador/api.py`, con sus pruebas. **No** se borra el resto del código viejo (`orquestador.py`, `nodos/`, `aristas/`…): el Agente FAQ todavía depende de `contratos.py`. Esa limpieza queda como mejora 🟡. Sí se agrega una nota en `agents/orquestador/README.md` que diga qué código ya no se usa.

### Parte B · El bot y Docker

10. **Reescribir el bot** (`agents/bot_discord/`), delgado:
    - escucha **solo** `#dudas` y `#logros`, con sus IDs en el `.env` de la raíz (S10: `DISCORD_CHANNEL_DUDAS_ID` y `DISCORD_CHANNEL_LOGROS_ID`, los mismos nombres que usa la ingesta);
    - ignora sus propios mensajes y los de otros bots, pero **no** los de nuestros webhooks: son los alumnos simulados (`esSimulado = true`). Tampoco descarta los mensajes sin texto: los registra (la IA les pone `OTRO` por regla);
    - **arma el contrato v1 reutilizando `transform.py`** (`a_contrato` y `armar_lote`, con un `Contexto` armado igual que en `extract.py`), para que el mensaje en vivo y el del lote de la hora sean idénticos (C2). 🔎 Recomendado: pedir el JSON crudo con `GET /channels/{canal}/messages/{id}`, que tiene la misma forma que el que lee la ingesta. El chat de tarea lo verifica en la documentación de Discord (📘) y elige;
    - envía a Java con `X-Api-Key` (`API_KEY_BOT`) y un tiempo máximo de **40 s** (D4). Mientras espera, muestra **"escribiendo…"** en el canal;
    - cumple la orden de Java **respondiendo al mensaje** (así la respuesta queda enlazada con `respondeA`) y con **las menciones desactivadas** (S8: `AllowedMentions.none()` de discord.py);
    - **en los registros, solo IDs, la orden y los tiempos: nunca el texto** (S11).
11. **Un solo nombre para el token** (M3): `DISCORD_BOT_TOKEN`, el mismo de la ingesta.
12. **Docker:** un `Dockerfile` para el bot que se construya desde la raíz, como el de la IA, y que copie los módulos de la ingesta que reutiliza (sin duplicarlos). Servicio `bot` en `compose.yml`: **sin puertos publicados**, `depends_on` de `api-java` sano y `restart: unless-stopped`. Variables nuevas en `.env.example`: `DISCORD_BOT_TOKEN`, los dos IDs de canal y `API_KEY_BOT`.
13. **`scripts/generar_api_key.py --cliente bot`**: escribe `API_KEY_BOT` en el `.env` de la raíz sin mostrarla, igual que en T03 y T04.
14. **`docs/OPERACION.md`:** cómo encender y apagar el bot, y la regla de **un solo bot encendido**. Agregar también la nota de T04 sobre PowerShell y la tilde: buscar `Select-String "Clasificaci"`.

## 4. Fuera de alcance

- El Agente-Mod, los borradores de LinkedIn y la FAQ semanal (T06). El bot no publica nada fuera de Discord.
- El panel y el dashboard (T07 y T08). La consulta de "dudas sin responder" es de T08; esta tarea solo guarda el dato.
- Borrar el código viejo de la IA, más allá de la puerta `/procesar` (mejora 🟡).
- Cambiar el contrato v1 o un campo existente del contrato Java ↔ IA. Si hace falta, se consulta.
- Comandos de barra (`/ayuda`) o hilos de Discord.
- **No ejecutar `simulate_students.py`.**
- **No encender un segundo bot**: antes de la prueba real, comprobar que no quede corriendo el bot viejo ni otra copia con el mismo token.

## 5. Pruebas exigidas

**Java**, con PostgreSQL real (`insightedu_test`) y la IA simulada (`MockRestServiceServer`):

| # | Caso | Resultado esperado |
|---|---|---|
| 1 | Duda con respuesta encontrada | `RESPONDER`, con texto y fuentes; etiquetas `OK`; `respuesta_estado = RESPONDIDA` |
| 2 | Duda sin respuesta, o con el tope agotado | `DERIVAR`; `respuesta_estado = DERIVADA` |
| 3 | Testimonio / comentario | `REACCIONAR` / `NADA`, con sus etiquetas guardadas |
| 4 | La IA responde 500 o se agota el tiempo | `NADA`; el mensaje sigue `PENDIENTE`, con un intento más y **sin reserva**; la siguiente vuelta en segundo plano lo clasifica |
| 5 | Mientras la puerta en vivo espera a la IA, corre `procesarTanda()` | No toma ese mensaje: una sola llamada a la IA |
| 6 | El mismo mensaje llega dos veces a la puerta en vivo | La segunda vez, `NADA` y la IA no recibe nada |
| 7 | Después llega el lote de la hora con el mismo mensaje | No se duplica; las etiquetas y la respuesta guardada no cambian |
| 8 | Claves: sin clave, la de `ingesta` en la puerta en vivo o la de `bot` en `/api/v1/lotes` | 401, 403 y 403 |
| 9 | Dos mensajes, o `modo = historial`, en la puerta en vivo | 422 |
| 10 | Las pruebas de T01, T03 y T04 | Siguen pasando |

**Python, IA:** el tope total con un Agente FAQ falso que tarda más que el tope (responde a tiempo, con `encontrada = false`); `/procesar` devuelve 404; las 29 pruebas de antes siguen pasando, salvo las de `/procesar`, que se quitan o se adaptan.

**Python, bot** (sin conectarse a Discord, con objetos falsos): un canal no permitido o un mensaje propio se ignoran; un webhook propio se procesa; `RESPONDER` responde con las menciones desactivadas; `REACCIONAR` pone 🎉 sin texto; `NADA` y un fallo de Java no responden; los registros no contienen el texto; el contrato que arma el bot para un JSON crudo es **igual** al que arma la ingesta para el mismo JSON. Las 36 pruebas de la ingesta siguen pasando.

**Prueba real, la corre Harrison** (gasta unas 10 llamadas a Gemini: hasta 3 por duda):
1. Comprobar que no haya otro bot encendido con el mismo token.
2. `python scripts/generar_api_key.py --cliente bot`, copiar `DISCORD_BOT_TOKEN` y los dos IDs de canal al `.env` de la raíz (el chat de tarea dice cómo, sin leer el `.env`) y `docker compose up -d --build`.
3. En `#dudas`: una pregunta que esté en los PDFs (por ejemplo, "¿cuándo empiezan las inscripciones?") → el bot responde con la fuente. Una que no esté → avisa que responderá un mentor. Un saludo → nada.
4. En `#logros`: un logro → 🎉, sin texto.
5. Consulta de solo lectura con las etiquetas y `respuesta_estado` de esos mensajes; después, `build_batch.py` y `send_batch.py`: los mensajes no se duplican.
6. Pegar las salidas en el informe.

## 6. Criterios de terminado

- [ ] La puerta en vivo responde con la orden correcta, guarda las etiquetas y la respuesta, y solo la usa el cliente `bot`.
- [ ] Un mensaje en vivo se clasifica una sola vez, aunque corra la tarea en segundo plano o llegue el lote de la hora.
- [ ] La IA respeta el tope total en `tiempoReal`, y la puerta vieja `/procesar` ya no existe.
- [ ] El bot corre en Docker, solo en `#dudas` y `#logros`, sin menciones y sin textos en los registros.
- [ ] `BOT_JAVA_v1.md` está escrito, y `JAVA_IA_v1.md` tiene el agregado del tope.
- [ ] Las pruebas de Java y Python pasan, y la prueba real muestra las respuestas en Discord y en la base (🧪 con la salida en el informe).
- [ ] El informe `docs/tareas/T05-informe.md` está completo, y no se tocó nada fuera del alcance.

## 7. Comandos de git para Harrison

**Al empezar**, desde `C:\Users\LENOVO\Documents\Cursos\No Country\Hackaton ONE 10\insightedu-lab`:
```
git switch feature/integracion-arquitectura-3
git pull
git switch -c tarea/T05-bot-en-vivo
```

**Al terminar:** el chat de tarea da los comandos de commit, con un solo `-m` y **sin** `Co-Authored-By` (DEC-65). Se sugiere un commit por parte (A y B). Después:
```
git push -u origin tarea/T05-bot-en-vivo
```

Luego le dices al chat principal **"T05 terminó"**.

## 8. Cómo abrir el chat de esta tarea

1. En VS Code, abrir un chat nuevo de Claude Code **en esta misma carpeta**.
2. Elegir el modelo **Opus 5.5** con `/model`.
3. Primer mensaje: *"Eres el chat de la tarea T05. Lee CLAUDE.md y docs/tareas/T05-bot-en-vivo.md y empieza."*
