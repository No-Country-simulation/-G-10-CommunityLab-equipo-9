# Informe de la tarea T03 — Puerta de lotes en Java

| Dato | Valor |
|---|---|
| Fecha | 2026-10-03 (prueba real: 2026-10-04 01:08 UTC) |
| Modelo de Claude usado | Opus 5.5 (`claude-opus-5-5`); la ficha recomendaba Sonnet 5.5 |
| Rama | `tarea/T03-puerta-lotes` |
| Commits | Uno: `feat(backend): puerta POST /api/v1/lotes con contrato v1, idempotencia y API key (T03)` (ver `git log`) |

## 1. Resumen

La ingesta vuelve a llegar a Java: `send_batch.py` envía el contrato v1 tal cual (**D8 = opción a**) a `POST /api/v1/lotes`, con la cabecera `X-Api-Key`. Java valida el lote completo, guarda la fila del lote y hace el upsert de cada mensaje en una sola transacción, y reenviar un lote es seguro. Hay manejo global de errores con el formato común. Pasan 28 pruebas de Java y 36 de Python. La prueba real con los 39 mensajes del servidor no duplicó nada al reenviar.

## 2. Criterios de terminado

| Criterio | Estado | Evidencia |
|---|---|---|
| D8 validada por Harrison y anotada en el informe | ✅ | 👤 Opción (a), en el primer mensaje del chat (2026-10-03). Sección 5 |
| `POST /api/v1/lotes` guarda sin duplicar, en una sola transacción, y es idempotente por `loteId` | ✅ | 🧪 Pruebas 1, 2, 3 y 7 y `dosEnviosSimultaneosDelMismoLoteNoDuplican`. Al quitar la transacción a propósito fallan 3 pruebas. Prueba real: 39 mensajes y 39 distintos después de 3 envíos |
| La API key es obligatoria (salvo en `/actuator/health`), se genera sin mostrarla y está en las dos plantillas `.env.example` | ✅ | 🧪 Pruebas 4 y 5 y `otrasRutasDelActuadorSiPidenClave`. `scripts/generar_api_key.py` probado con `.env` falsos (sección 4). `API_KEY_INGESTA` en `.env.example` y `BACKEND_API_KEY` en `ingestion/discord/.env.example` |
| Manejo global de errores con el formato común | ✅ | 🧪 400, 401, 404, 413, 422 y 500 cubiertos; todos con `idCorrelacion` |
| `send_batch.py` envía al Java real con la clave, y el reenvío no duplica | ✅ | 🧪 Prueba real (sección 4) |
| Las pruebas de Java y Python pasan | ✅ | 🧪 `Tests run: 28, Failures: 0, Errors: 0` · `36 passed` |
| Informe completo; no se tocó nada fuera del alcance | ✅ | No se tocó `contract.py`, `transform.py`, el upsert de T01, `agents/` ni el bot. Ver la sección 3 |

## 3. Archivos cambiados

Rutas Java relativas a `backend-java/src/main/java/com/insightedulab/backend_java/`.

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `controller/LoteController.java` | Nuevo: `POST /api/v1/lotes` | §3.2 |
| `dto/lote/LoteEntrada.java`, `MensajeEntrada.java`, `ReciboLote.java` | Nuevos: el lote con cada mensaje como `Map` (la caja), los campos que van a columnas con su validación en español, y el recibo | §3.2.1, §3.2.2 y §3.2.5 |
| `service/LoteService.java` | Nuevo: valida el lote entero; si el `loteId` ya existe, devuelve el mismo recibo; si no, en una transacción inserta la fila del lote **primero** y luego hace el upsert de cada mensaje | §3.2.2 a §3.2.4 |
| `seguridad/ApiKeyFilter.java` | Nuevo: exige `X-Api-Key` en todo salvo `/actuator/health`; compara huellas SHA-256 en tiempo constante; nunca registra la clave | §3.2.6 (S1) |
| `seguridad/IdCorrelacionFilter.java` | Nuevo: toma `X-Id-Correlacion` (validada) o crea uno; lo devuelve en la respuesta y lo pone en el registro | §3.2.7 |
| `seguridad/LimiteCuerpoFilter.java` | Nuevo: 413 si el cuerpo pasa de 5 MB; 411 si falta `Content-Length` en POST, PUT o PATCH | §3.2.2 |
| `seguridad/SeguridadProperties.java`, `SeguridadConfig.java`, `RespuestaError.java` | Nuevos: claves por cliente (`seguridad.api-keys.*`), tope de bytes y el error en JSON desde los filtros | §3.2.6 |
| `error/ErrorApi.java`, `ManejadorErrores.java`, `ContratoInvalidoException.java`, `NoEncontradoException.java` | Nuevos: formato común `{codigo, mensaje, errores, idCorrelacion}` y manejo global | §3.2.7 (F13, S7) |
| `backend-java/src/main/resources/application.properties` | + `seguridad.api-keys.ingesta=${API_KEY_INGESTA:}` y `seguridad.max-bytes-cuerpo` | §3.2.6 |
| `backend-java/src/test/java/.../LotesApiTest.java` | Nuevo: 17 pruebas | §5 |
| `compose.yml` | + `API_KEY_INGESTA` en `api-java` | §3.2.8 |
| `.env.example` | + `API_KEY_INGESTA`, con la explicación | §3.2.8 |
| `scripts/generar_api_key.py` | Nuevo: crea la clave y la escribe en los dos `.env` sin mostrarla; no pisa una clave existente sin `--reemplazar`; conserva los saltos de línea | §3.2.8 |
| `ingestion/discord/send_batch.py` | Envía el `Lote` tal cual con `X-Api-Key`; acepta el recibo nuevo y `yaRecibido`. **Se borraron `a_formato_backend`, `a_interaccion` y `TIPO_AUTOR_BACKEND`** | §3.2.9 |
| `ingestion/discord/config.py` | + `api_key_backend` (`BACKEND_API_KEY`, con `repr=False`) | §3.2.9 |
| `ingestion/discord/tests/test_send.py` | Reescrito: 7 pruebas (antes, 5) | §3.2.9 |
| `ingestion/discord/.env.example` | `BACKEND_INGEST_URL=http://127.0.0.1:8008/api/v1/lotes` y `BACKEND_API_KEY=` | §3.2.9 |
| `ingestion/discord/README.md` | Se quitó la opción C de la descripción de `send_batch.py`; + `BACKEND_API_KEY` | Que el README no contradiga D8 |
| `docs/OPERACION.md` | + `API_KEY_INGESTA` en la tabla de variables | Operación |

## 4. Pruebas

| Comando ejecutado | Resultado (🧪) |
|---|---|
| `docker run … maven:3.9-eclipse-temurin-21 mvn test` (base `insightedu_test`, [OPERACION.md §5](../../OPERACION.md)) | `Tests run: 28, Failures: 0, Errors: 0, Skipped: 0` · `BUILD SUCCESS` (17 de `LotesApiTest`, 10 de `ModeloDatosTest` y 1 de `BackendJavaApplicationTests`) |
| Lo mismo, quitando a propósito la transacción de `LoteService` (y restaurándola después) | `Failures: 3`: `siLaBaseFallaEnMedioSeDeshaceTodo`, `elMismoLoteDosVecesDevuelveElMismoRecibo` y `dosEnviosSimultaneosDelMismoLoteNoDuplican`. Las pruebas detectan la falta de transacción |
| `python -m pytest -q` (desde `ingestion/discord`) | `36 passed` (34 de antes; `test_send.py` pasó de 5 a 7) |
| `generar_api_key.py` con dos `.env` falsos en una carpeta temporal | Misma clave en los dos (43 caracteres), nunca en pantalla; `\r\n` y `\n` conservados; las otras líneas, intactas; sin `--reemplazar` no pisa; con `--reemplazar` crea una nueva |

Casos de la ficha y sus pruebas:

| # | Caso | Prueba |
|---|---|---|
| 1 | Lote válido de 3 | `loteValidoGuardaLosMensajesYElLote` (además, comprueba que la caja tiene `nombreVisible`) |
| 2 | Mismo `loteId` otra vez | `elMismoLoteDosVecesDevuelveElMismoRecibo` (recibo idéntico, incluido `recibidoEn`) y `dosEnviosSimultaneosDelMismoLoteNoDuplican` (4 hilos a la vez: 1 guarda y 3 reciben `yaRecibido`) |
| 3 | `loteId` nuevo y uno con más reacciones | `loteNuevoConUnMensajeCambiadoCuentaUnActualizado` |
| 4 | Sin clave o con una incorrecta | `sinApiKeyEs401YNoGuardaNada`, `conApiKeyIncorrectaEs401YNoGuardaNada` |
| 5 | `/actuator/health` sin clave | `healthNoPideClave` (y `otrasRutasDelActuadorSiPidenClave`) |
| 6 | Versión distinta o valor fuera de la lista | `valoresFueraDelContratoSon422SinRepetirLosDatos`, `tipoDeDatoIncorrectoEs422ConLaRuta`, `fechaImposibleEs422`, `jsonRotoEs400`, `masDeMilMensajesEs422` |
| 7 | Un mensaje inválido en medio | `unMensajeInvalidoEnMedioNoGuardaNada` (422) y `siLaBaseFallaEnMedioSeDeshaceTodo`: el 2.º upsert falla dentro de la transacción y no queda nada |
| 8 | Las 11 pruebas de T01 | Pasan |
| extra | Topes y errores generales | `cuerpoDemasiadoGrandeEs413`, `rutaInexistenteEs404ConElFormatoComun` |

**Prueba real (Harrison, 2026-10-04, servidor de pruebas)**

```
extract.py      ✅ #dudas 27 mensajes · #logros 12 mensajes (todo el historial) · contexto: rol del bot, roles de 1 autor real
build_batch.py  ✅ 39 mensajes cumplen el contrato v1.0 (32 simulados y 7 reales; 2 sin texto, 1 con adjunto)
send_batch.py   ✅ Java recibió el lote 96ff34b8-…: total 39 (nuevos 39, actualizados 0, sin cambios 0).
send_batch.py   ✅ Java recibió el lote 96ff34b8-…: total 39 (nuevos 39, …). Java ya lo tenía: no se guardó nada otra vez.
build_batch.py  ✅ 39 mensajes → lote nuevo
send_batch.py   ✅ Java recibió el lote de119cd3-…: total 39 (nuevos 0, actualizados 0, sin cambios 39).
```

Consulta de solo lectura en la base principal (la corrió el chat de tarea):

```
 mensajes | distintos          lote_id                              | total | nuevos | actualizados
       39 |        39          96ff34b8-c5ba-433e-8598-58340f4a7e42 |    39 |     39 |            0
                               de119cd3-bfee-4248-ad21-660b24eefe15 |    39 |      0 |            0
 autor_tipo / autor_rol / es_simulado: persona/mentor/f 7 · persona/mentor/t 2 · persona/miembro/t 30
 estado_clasificacion: PENDIENTE 39   (esperan a la IA: T04)
```

Registro de `api-java`: `API keys configuradas para: [ingesta]` (el nombre del cliente, nunca la clave), `Lote 96ff34b8-… guardado`, `Lote 96ff34b8-… ya recibido: se devuelve el mismo recibo`, `Lote de119cd3-… guardado: total 39, nuevos 0, actualizados 0`.

## 5. Decisiones que se tomaron

👤 D8 y las 6 decisiones de diseño fueron validadas por Harrison el 2026-10-03 ("ok a todo").

| Decisión | Alternativas descartadas | ¿Cambia el contrato, la arquitectura o D1 a D7? |
|---|---|---|
| **D8 = (a):** Java recibe el contrato v1 tal cual | (b) Mantener la opción C | Reemplaza la opción C de `INGESTION_GUIDE.md` §11. No cambia el contrato v1 |
| API key con un filtro propio, exigida **en todas las rutas** salvo `/actuator/health`; claves por cliente (`seguridad.api-keys.*`) | Spring Security; proteger ruta por ruta | No |
| Sin `API_KEY_INGESTA`, la API arranca y rechaza todo con 401 | No dejar arrancar la API | No |
| Validación de los campos que van a columnas (con el texto de los valores cerrados), juntando todos los errores en un solo 422 | Validar la caja completa contra el JSON Schema | No. Ver el riesgo 1 |
| JSON ilegible → 400 `CUERPO_INVALIDO`; JSON que no cumple el contrato → 422 `CONTRATO_INVALIDO` | Todo 422 | No |
| Topes: 1000 mensajes (422) y 5 MB (413); `Content-Length` obligatorio en POST, PUT y PATCH (411) | Leer el cuerpo contando bytes | No |
| La clave la genera un script que corre Harrison, sin mostrarla | Generarla a mano | No |
| Idempotencia: la fila de `lotes_recibidos` se inserta **primero** dentro de la transacción; un envío simultáneo del mismo lote espera, choca con la columna única, se deshace y devuelve el recibo guardado | Revisar si existe y luego insertar | No |
| `recibidoEn` en microsegundos | Nanosegundos de Java | No: así el recibo repetido es idéntico, porque PostgreSQL guarda microsegundos |

## 6. Dudas, riesgos y pendientes

1. **La caja no se valida completa en Java.** Se validan los campos que van a columnas y los valores cerrados. Un mensaje con un campo raro **fuera** de esos campos pasaría Java y lo rechazaría la IA (`/v1/procesar` valida el contrato completo). **Para T04:** tratar un 422 de la IA como un error de ese lote y no reintentarlo sin fin.
2. **Adjuntos que inflan los "actualizados"** (observación de T01, solo evaluada). 🧪 En la prueba real, el segundo lote se armó con los **mismos** datos extraídos, así que las URL eran iguales: `sin cambios 39`. 🔎 Al volver a extraer días después, Discord entrega el adjunto con otra URL firmada (`ex`, `is`, `hm`): ese mensaje contará como `ACTUALIZADO` aunque nada cambió de verdad. No reinicia la clasificación (solo lo hace un cambio de texto, F2), así que el efecto se limita al contador y a `actualizado_en`. Si molesta, se puede ignorar `adjuntos[].url` y `urlExpiraEn` en la comparación del upsert, con una migración o en `MensajeUpsertRepository`. **No se cambió.**
3. **El carácter NUL (`\u0000`) en un texto hace fallar el lote entero con 500.** PostgreSQL no lo acepta en `text` ni en `jsonb`. 🔎 Discord no suele permitirlo, pero un solo mensaje así bloquearía cada lote que lo incluya. Se usa en la prueba de la transacción. Opciones: rechazarlo con 422 o quitarlo al recibir. Decidir antes del despliegue.
4. **La API key viaja como texto plano por HTTP.** En esta máquina no importa, porque el puerto escucha solo en `127.0.0.1` (S5). En el servidor, la ingesta y Java tienen que hablar por la red interna de Docker, o por HTTPS si cruzan internet (fase 6).
5. **CORS y la clave.** Un navegador que haga un pedido de verificación previo (`OPTIONS`) recibirá 401. 🔎 No afecta: el panel llama a Java desde el servidor (S6). Si algún día llama desde el navegador, habrá que revisarlo.
6. **Documentos de la rama de la ingesta que todavía nombran la opción C:** `ingestion/discord/CLAUDE.md` (líneas 45 y 48), `ingestion/discord/docs/SCOPE.md:88` e `INGESTION_GUIDE.md` §11. No se tocaron: el `CLAUDE.md` de la raíz ya marca la opción C como histórica. Revisarlos en el chat principal.
7. **Primera extracción en este clone.** `data/` estaba vacía, así que hubo que correr `extract.py`, que solo lee, antes de `build_batch.py`. Ahora `data/markers.json` existe y la próxima extracción es incremental.

## 7. Comandos que ejecutó Harrison

Desde la raíz del repositorio, salvo donde se indica:

| # | Comando | Resultado (🧪) |
|---|---|---|
| 1 | `git switch feature/integracion-arquitectura-3` · `git commit` (docs: auditoría de T02 y ficha T03) · `git push` | `e165307` |
| 2 | `git add …` · `git commit` (docs: D8 validada y ficha T04) · `git push` · `git switch tarea/T03-puerta-lotes` · `git merge --ff-only feature/integracion-arquitectura-3` | `ac2dd67`, rama al día y limpia |
| 3 | `python scripts\generar_api_key.py` | `✅ Clave nueva escrita en .env (API_KEY_INGESTA) y en ingestion/discord/.env (BACKEND_API_KEY).` |
| 4 | A mano: `BACKEND_INGEST_URL=http://127.0.0.1:8008/api/v1/lotes` en `ingestion/discord/.env` | 🧪 Comprobado sin mostrar valores: la URL es la esperada y las dos claves coinciden |
| 5 | `docker compose up -d --build api-java` · `docker compose ps` | `api-java … (healthy)` |
| 6 | Desde `ingestion\discord`: `extract.py`, `build_batch.py`, `send_batch.py` (×2), `build_batch.py`, `send_batch.py` | Sección 4 |
| 7 | `git add …` y `git commit` | Commit de la tarea |

El chat de tarea corrió las pruebas de Java y de Python, la prueba del script con archivos falsos y las consultas de solo lectura.
