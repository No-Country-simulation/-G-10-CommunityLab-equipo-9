# Informe de la tarea T05 — El bot pasa por Java: dudas respondidas en vivo

| Dato | Valor |
|---|---|
| Fecha | 2026-10-04 |
| Modelo de Claude usado | Opus 5.5 (`claude-opus-5-5`) |
| Rama | `tarea/T05-bot-en-vivo` |
| Commits | Dos, uno por parte (ver `git log`): `feat(backend,ia): puerta en vivo del bot, respuesta guardada y tope de tiempo real (T05 parte A)` y `feat(bot): bot delgado que pasa por Java, en Docker (T05 parte B)` |

## 1. Resumen

El bot ya no va directo a la IA: arma el contrato v1 con `transform.py` de la ingesta, se lo envía a Java (`POST /api/v1/mensajes/en-vivo`, solo con la clave `bot`) y cumple la orden que recibe (`RESPONDER`, `DERIVAR`, `REACCIONAR` o `NADA`). Java guarda el mensaje y lo reserva en la misma transacción (no hay doble clasificación), llama a la IA en `tiempoReal` y guarda las etiquetas y la respuesta (migración `V3`). La IA tiene un tope total de 25 s y ya no existe `/procesar`. Pasan 72 pruebas de Java, 36 de la IA, 22 del bot y 36 de la ingesta. **La prueba real con Discord salió bien** (sección 4.5): respondió con la fuente, derivó al mentor, ignoró el saludo, puso 🎉 al logro y el lote de la hora no duplicó nada (49 de 49). En la prueba real apareció la ruta de la PC de un compañero en las fuentes; se corrigió con las decisiones 11 y 12.

## 2. Criterios de terminado

| Criterio | Estado | Evidencia |
|---|---|---|
| La puerta en vivo responde con la orden correcta, guarda las etiquetas y la respuesta, y solo la usa el cliente `bot` | ✅ | 🧪 `EnVivoApiTest`, casos 1, 2, 3 y 8 (sección 4.1) |
| Un mensaje en vivo se clasifica una sola vez, aunque corra la tarea en segundo plano o llegue el lote de la hora | ✅ | 🧪 Casos 5, 6 y 7: una sola llamada a la IA; el lote de la hora da `sinCambios` (o `actualizados` si cambió una reacción) sin tocar etiquetas ni respuesta |
| La IA respeta el tope total en `tiempoReal`, y la puerta vieja `/procesar` ya no existe | ✅ | 🧪 4 pruebas del tope y `test_la_puerta_vieja_procesar_ya_no_existe` (404) |
| El bot corre en Docker, solo en `#dudas` y `#logros`, sin menciones y sin textos en los registros | ✅ | 🧪 22 pruebas del bot con objetos falsos. Prueba real: `Bot conectado … Escucha ['#dudas', '#logros']`, y el registro tiene solo IDs, órdenes y milisegundos (sección 4.5) |
| `BOT_JAVA_v1.md` está escrito, y `JAVA_IA_v1.md` tiene el agregado del tope | ✅ | [BOT_JAVA_v1.md](../contratos/BOT_JAVA_v1.md); [JAVA_IA_v1.md](../contratos/JAVA_IA_v1.md) §6 (solo agrega, ningún campo cambió) |
| Las pruebas de Java y Python pasan, y la prueba real muestra las respuestas en Discord y en la base | ✅ | Secciones 4 y 4.5 |
| El informe está completo, y no se tocó nada fuera del alcance | ✅ con una excepción validada | No se tocó el contrato v1 (`contract.py`, `transform.py`, el schema), ni V1 ni V2, ni el código viejo de la IA salvo `/procesar`. **Excepción:** una línea de `agents/agent_faq/vectorstore/reranker.py` (decisión 11, validada por Harrison) |

## 3. Archivos cambiados

Rutas Java relativas a `backend-java/src/main/java/com/insightedulab/backend_java/`.

### Parte A · Java y la IA

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `backend-java/src/main/resources/db/migration/V3__respuesta_bot.sql` | Nuevo: `respuesta_estado` (`CHECK` `RESPONDIDA`/`DERIVADA`), `respuesta_texto`, `respuesta_fuentes` (jsonb) y `respondido_en` | §3.6, DEC-66 |
| `envivo/EnVivoService.java` | Nuevo: valida (un mensaje, `tiempoReal`), upsert + reserva en una transacción, llama a la IA sin transacción, decide la orden y guarda con las guardas de T04. En `RESPONDER` publica el texto de la IA tal cual, sin pie de fuentes (decisión 12) | §3.1 a §3.5 |
| `envivo/EnVivoRepository.java` | Nuevo: reserva **un** mensaje por `discord_id` (solo si está `PENDIENTE`, sin respuesta y sin reserva vigente) y guarda etiquetas + respuesta en **una** sentencia | §3.2 y §3.5 |
| `envivo/OrdenBot.java` | Nuevo: la respuesta para el bot | §3.7, DEC-68 |
| `controller/MensajeEnVivoController.java` | Nuevo: `POST /api/v1/mensajes/en-vivo` | §3.1 |
| `seguridad/ApiKeyFilter.java` | Mapa ruta → cliente: `/api/v1/lotes` solo `ingesta`, `/api/v1/mensajes/en-vivo` solo `bot`. Los demás reciben 403 `PROHIBIDO`, antes de leer el cuerpo | §3.1, DEC-70 |
| `clasificacion/LoteParaIa.java` | Nuevo: el armado del lote para la IA, que antes estaba dentro de `ClasificacionService`. Lo usan las dos clasificaciones | Reutilizar (ficha: "reutilizarlos") |
| `clasificacion/ClasificacionService.java` | Usa `LoteParaIa`. Sin cambios de comportamiento | Ídem |
| `client/RespuestaIa.java` | + `respuesta` del Agente FAQ (record `Respuesta`). Un constructor de 8 argumentos deja intactas las pruebas de T04 | §3.4 |
| `service/LoteService.java` | + `validarYLimpiar(lote)` público: la misma validación y limpieza del NUL, sin escribir | §3.1 |
| `seguridad/SeguridadProperties.java`, `application.properties` | `seguridad.api-keys.bot=${API_KEY_BOT:}` | §3.1 |
| `agents/orquestador/config.py` | `TIEMPO_REAL_TOPE_S` (25 por defecto; 0 = sin tope) | §3.8, DEC-54 |
| `agents/orquestador/grafo_v1.py` | El plazo viaja en el estado del grafo; el Agente FAQ corre en un hilo con el tiempo que queda; si no alcanza, `encontrada = false` y el motivo. `sin_carpetas()`: `fuentes` lleva solo el nombre del PDF y la página | §3.8 y decisión 11 |
| `agents/agent_faq/vectorstore/reranker.py` | La cita corta la ruta con `/` **o** `\` (antes, solo con `/`): sin la ruta de la PC donde se armó el índice, ni en `fuentes` ni en el contexto que recibe Gemini | Decisión 11 |
| `agents/orquestador/clasificadores/etiquetador.py` | `etiquetar(mensaje, plazo=None)`: con plazo, cada intento espera como máximo lo que queda | §3.8 (el tope también cubre la clasificación) |
| `agents/orquestador/api.py`, `config_http.py` | Se quitó `POST /procesar`, `_get_orquestador` y la constante `ENDPOINT_PROCESAR` | §3.9 |
| `agents/orquestador/README.md` | Nota al principio: qué código se usa y cuál ya no | §3.9 |
| `docs/contratos/BOT_JAVA_v1.md` | Nuevo | §3.7 |
| `docs/contratos/JAVA_IA_v1.md` | Cabecera con el cambio de T05, §6 con el tope, `/procesar` quitado, §5 dice dónde se guarda la respuesta | §3.8 |

### Parte B · El bot y Docker

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `agents/bot_discord/bot_communitylab.py` | **Reescrito**, con el mismo nombre de archivo (§5, decisión 9) | §3.10 y §3.11 |
| `agents/bot_discord/tests/test_bot.py` | Nuevo: 22 pruebas | §5 de la ficha |
| `agents/bot_discord/Dockerfile`, `requirements.txt` | Nuevos. Se construye desde la raíz y copia `contract.py`, `transform.py`, `config.py` y `discord_api.py` de la ingesta (sin duplicarlos en git). Usuario sin privilegios | §3.12 |
| `compose.yml` | Servicio `bot` (sin puertos, `depends_on` de `api-java` sano, `restart: unless-stopped`); `API_KEY_BOT` para `api-java`; `TIEMPO_REAL_TOPE_S` para `ia` | §3.12 |
| `.env.example` (raíz) | `API_KEY_BOT` y la sección del bot, con las 8 variables de Discord | §3.12 y decisión 1 |
| `.dockerignore` | Solo el comentario (la IA **y el bot** se construyen desde la raíz) | — |
| `scripts/generar_api_key.py` | `--cliente bot` → `API_KEY_BOT` en el `.env` de la raíz | §3.13 |
| `docs/OPERACION.md` | Variables del bot, servicio `bot`, §7 nueva (encender, apagar, **un solo bot**), V3, la nota de `Select-String "Clasificaci"` y un problema común del bot | §3.14 |

## 4. Pruebas

| Comando ejecutado | Resultado (🧪) |
|---|---|
| Java, en Docker contra `insightedu_test` (OPERACION.md §5) | **72 pruebas, 0 fallas**: 21 nuevas de `EnVivoApiTest` + las 51 de T01, T03 y T04 |
| `python -m pytest agents/orquestador/tests -q` | **36 passed**: 29 de antes − 1 de `/procesar` (quitada) + 5 del tope y de `/procesar` + 3 de la fuente sin carpetas |
| `reranker.py` dentro del contenedor `ia` (sin cargar el modelo ni llamar a Gemini), con una ruta de Windows y una de Linux | `['06_Manual_del_Estudiante_V3.pdf (Pág. 1)', '11_Calendario_Academico_2027.pdf (Pág. 2)']` y `ruta en el contexto para Gemini: False` |
| `python -m pytest agents/bot_discord/tests -q` | **22 passed** |
| `python -m pytest -q` (desde `ingestion/discord`) | **36 passed**, sin cambios |
| `docker compose config --quiet` | Sin errores |
| `docker compose build bot` | `Image insightedu-bot Built` |
| `docker run --rm insightedu-bot` (sin variables) | `ERROR bot: Falta DISCORD_BOT_TOKEN…` y sale con código 1, sin conectarse a nada |
| `generar_api_key.generar` con `API_KEY_BOT` sobre un `.env` **temporal** | Escribe una clave de 43 caracteres, conserva los `\r\n` y las demás líneas; la segunda vez no la pisa |

### 4.1 Java (resumen de surefire)

```
Tests run: 1,  Failures: 0, Errors: 0 -- BackendJavaApplicationTests
Tests run: 15, Failures: 0, Errors: 0 -- ClasificacionTest
Tests run: 21, Failures: 0, Errors: 0 -- EnVivoApiTest
Tests run: 19, Failures: 0, Errors: 0 -- LotesApiTest
Tests run: 10, Failures: 0, Errors: 0 -- ModeloDatosTest
Tests run: 6,  Failures: 0, Errors: 0 -- NlpDataClientTest
EXIT 0
```

La corrida final (después de las decisiones 11 y 12) también dio 72 de 72. La primera corrida tuvo 2 fallas, las dos en pruebas nuevas mías: (1) con `textoOriginal: 42`, Jackson convierte el número en texto y el mensaje era válido, así que la cambié por `autor.tipo = "HUMANO"`, como en `LotesApiTest`; (2) volver a configurar con `when(...)` un simulador de Mockito que ya lanzaba una excepción la disparaba, así que pasé a `doAnswer(...)`. También agregué una guarda en `EnVivoService` por si la IA devolviera una respuesta vacía.

### 4.2 Pruebas de Java de la ficha (§5)

| # | Caso de la ficha | Prueba(s) |
|---|---|---|
| 1 | Duda con respuesta | `dudaConRespuestaEncontradaDaResponderYSeGuardaLaRespuesta`, `laIaRecibeElMensajeEnTiempoRealConElLoteIdDelBot`, `unaRespuestaLargaSeRecortaAlMaximoDeDiscord` |
| 2 | Duda sin respuesta / tope | `dudaSinRespuestaDaDerivar`, `dudaConElTopeAgotadoDaDerivar` |
| 3 | Testimonio / comentario | `testimonioDaReaccionarSinTexto`, `comentarioDaNadaYGuardaSusEtiquetas` |
| 4 | IA 500 o tiempo agotado | `siLaIaFallaDaNadaYLoClasificaLaSiguienteVueltaEnSegundoPlano`, `unErrorDeLaIaEnElMensajeDaNadaYSumaUnIntento`, `siElMensajeCambioMientrasLaIaPensabaNoSeResponde` |
| 5 | `procesarTanda()` mientras espera | `mientrasLaPuertaEnVivoEsperaALaIaLaTareaEnSegundoPlanoNoLoToma` |
| 6 | El mismo mensaje dos veces | `elMismoMensajeDosVecesNoSeVuelveAResponder`, `unMensajeQueYaClasificoElLoteDeLaHoraNoSeEnviaALaIa` |
| 7 | Después llega el lote de la hora | `elLoteDeLaHoraNoDuplicaNiCambiaLasEtiquetasNiLaRespuesta` |
| 8 | Claves: 401, 403, 403 | `sinClaveEs401`, `laClaveDeLaIngestaEnLaPuertaEnVivoEs403`, `laClaveDelBotEnLaPuertaDeLotesEs403` |
| 9 | Dos mensajes o `historial`: 422 | `dosMensajesEs422`, `modoHistorialEs422`, `unMensajeQueNoCumpleElContratoEs422SinRepetirLosDatos`, `elMensajeEnVivoNoSeRegistraEnLotesRecibidos` |
| 10 | T01, T03 y T04 siguen pasando | Las 51 anteriores, sin cambios |

### 4.3 IA (las 5 nuevas)

`test_la_puerta_vieja_procesar_ya_no_existe` (404) · `test_si_el_faq_supera_el_tope_responde_a_tiempo_con_encontrada_false` (Agente FAQ falso de 1 s, tope 0,3 s: responde en menos de 0,9 s con las etiquetas y `encontrada = false`) · `test_el_tope_tambien_corta_al_clasificador` · `test_con_tiempo_de_sobra_el_tope_no_cambia_nada` · `test_en_historial_no_hay_tope`. Después de la prueba real, 3 más: `test_la_fuente_nunca_lleva_la_ruta_de_una_pc` (Windows, Linux y solo el nombre).

### 4.4 Bot (22)

Canal no permitido, mensaje propio, otro bot y webhook ajeno → se ignoran; webhook propio, persona en `#logros` y mensaje sin texto → se procesan; mensaje directo → se ignora. El contrato del bot es **igual** al de la ingesta para una alumna simulada y para un mentor real que menciona al bot por su rol (discord.py incluye `@everyone` entre los roles y no cambia nada). Lo que se envía a Java: URL, `X-Api-Key`, `X-Id-Correlacion`, 40 s, `tiempoReal`, un mensaje y "escribiendo…". `RESPONDER` responde con las 4 menciones desactivadas y `mention_author=False`; `DERIVAR` responde con el texto de Java; `REACCIONAR` pone 🎉 sin texto; `NADA` no hace nada; Java con 500, 401, caído, tiempo agotado u orden desconocida → nada. Los registros tienen el ID y la orden, pero no el texto del alumno ni el de la IA, tampoco ante un error inesperado. Sin `API_KEY_BOT` no arranca, y los ajustes no muestran secretos.

### 4.5 Prueba real con Discord (la corrió Harrison, 2026-10-04)

**Preparación.** `generar_api_key.py --cliente bot` escribió `API_KEY_BOT`. La primera vez, el bot se detuvo con `Falta DISCORD_BOT_TOKEN`, porque las variables de Discord estaban solo en `ingestion/discord/.env`. Se copiaron 8 líneas al `.env` de la raíz con un comando que no las muestra. Después:

```
INFO bot: Bot conectado (id 1554158872585965578). Escucha ['#dudas', '#logros']; Java en http://api-java:8080
```

🧪 Antes de encenderlo se comprobó que no había otro bot: ni procesos de Python con `bot` ni contenedores.

**Primera ronda (15:05–15:08 UTC), con la versión inicial**

| Mensaje | Registro del bot | En la base |
|---|---|---|
| ¿Cuándo empiezan las inscripciones? (`#dudas`) | `orden RESPONDER · 13535 ms` | `PREGUNTA_FAQ`, `RESPONDIDA` |
| una pregunta, ¿cuál es la mejor pizzería de Bogotá? (`#dudas`) | `orden NADA · 1860 ms` | `COMENTARIO` |
| hola (`#dudas`) | `orden NADA · 2491 ms` | `OTRO` |
| Un logro (`#logros`) | `orden REACCIONAR · 2549 ms` | `TESTIMONIO`; en Discord, 🎉 sin texto |
| ¿Cuál es la mejor pizzería de Bogotá? (`#dudas`) | `orden NADA · 1826 ms` | `COMENTARIO` |

🧪 **Problema encontrado:** la respuesta publicada terminaba con `📚 Fuente: C:\Users\<compañero>\Documents\…\06_Manual_del_Estudiante_V3.pdf (Pág. 1)`, es decir, con la **ruta de la PC de otro integrante**. Además nombraba **otro documento** que el que Gemini citaba dentro del texto (`11_Calendario_Academico_2027.pdf (Pág. 2)`). Se corrigió con las decisiones 11 y 12. 🔎 Gemini clasificó las dos preguntas de la pizzería como `COMENTARIO`, no como dudas: no son del curso. Por eso `DERIVAR` se probó en la segunda ronda, con una duda del curso.

**Segunda ronda (16:13–16:14 UTC), con las decisiones 11 y 12** (`docker compose up -d --build ia api-java`)

| Mensaje | Lo que publicó el bot | Registro del bot | En la base |
|---|---|---|---|
| cuando empiezan las inscripciones?? | Las fechas de las convocatorias 2027-I y 2027-II y, al final, `Fuentes: 11_Calendario_Academico_2027.pdf (Pág. 2)`. **Sin ruta y con una sola fuente** | `orden RESPONDER · 5914 ms` | `RESPONDIDA`, `respuesta_fuentes = ["11_Calendario_Academico_2027.pdf (Pág. 2)"]` |
| ¿Puedo entregar el proyecto final en Kotlin en vez de Java? | "¡Gracias por tu pregunta! No encontré una respuesta segura en los documentos del curso, así que un mentor te responderá pronto. 🙏" | `orden DERIVAR · 3603 ms` | `PREGUNTA_FAQ`, `DERIVADA`, `respondido_en` con fecha |

**Lote de la hora** (con el entorno virtual activado; sin activarlo, `extract.py` falla con `No module named 'httpx'`)

```
✅ #dudas   36 mensajes (últimos 7 días o desde el marcador) → data/raw/dudas.json
✅ #logros  13 mensajes (últimos 7 días o desde el marcador) → data/raw/logros.json
✅ 49 mensajes cumplen el contrato v1.0 → data/batches/batch_20261004T162305392Z.json
✅ Java recibió el lote 952d902a-…: total 49 (nuevos 3, actualizados 2, sin cambios 44).

 count | count          ← SELECT count(*), count(DISTINCT discord_id) FROM mensajes
    49 |    49
```

| Dato | Qué significa |
|---|---|
| 49 = 49 | Ningún duplicado |
| `nuevos 3` | Las 3 respuestas del bot (`botPropio`, `OTRO` por regla): el bot no se envía a sí mismo |
| Los mensajes que envió el bot quedaron en `sin cambios` | 🧪 Su `actualizado_en` no cambió: **el contrato del bot es idéntico al de la ingesta** (C2). Etiquetas y respuestas, intactas |
| `actualizados 2` | El logro, porque ahora tiene la reacción 🎉 (sigue `TESTIMONIO`/`OK`), y un mensaje anterior con una imagen, porque Discord renueva la URL firmada del adjunto en cada lectura (no viene de T05) |

## 5. Decisiones que se tomaron

| # | Decisión | Alternativas descartadas | ¿Cambia el contrato, la arquitectura o D1 a D7? |
|---|---|---|---|
| 1 | 👤 **Harrison (2026-10-04):** además de las 4 variables de la ficha, el `.env` de la raíz lleva `DISCORD_WEBHOOK_DUDAS_URL`, `DISCORD_WEBHOOK_LOGROS_URL`, `DISCORD_MENTOR_ROLE_IDS`, `DISCORD_STAFF_ROLE_IDS` y `SIMULATED_MENTORS`, con los nombres de la ingesta. 💻 Sin ellas, el `Contexto` del bot no reconoce a los simulados ni a los mentores y el contrato sale distinto del lote (rompe C2) | Que el bot lea `ingestion/discord/.env` con `env_file` (recibiría también la clave de la ingesta, contra DEC-70); solo las 4 de la ficha | No. Agrega variables de entorno |
| 2 | 📘 El JSON crudo se pide con `GET /channels/{canal}/messages/{id}` (documentación de Discord: devuelve el mismo objeto `message` que lee `extract.py`), con `DiscordAPI` de la ingesta, en otro hilo. Los roles del autor salen del `Member` de discord.py, porque el mensaje REST no los trae | Armar el JSON a mano desde el objeto de discord.py (otra implementación del contrato); `on_socket_raw_receive` (eventos de depuración) | No |
| 3 | Java arma el **texto final** (respuesta + "📚 Fuente: …", recortado a 2000 caracteres) y elige el emoji: el bot no decide nada (DEC-68). El texto de `DERIVAR` también lo pone Java | Que el bot agregue las fuentes o el aviso del mentor | No: es el contrato nuevo `BOT_JAVA_v1` |
| 4 | `respondido_en` se guarda en `RESPONDIDA` **y** en `DERIVADA` (cuándo decidió Java). `respuesta_texto` y `respuesta_fuentes` solo en `RESPONDIDA`: lo que no se publica (D3) no se guarda como respuesta | Guardar también el texto no publicado | No |
| 5 | El 403 se resuelve en `ApiKeyFilter`, con un mapa ruta → cliente, **antes de leer el cuerpo**. Código `PROHIBIDO` | Revisarlo en cada controlador (después de leer el cuerpo y fácil de olvidar en una puerta nueva) | No |
| 6 | El tope de 25 s también corta la **clasificación** (el etiquetador recibe el plazo), no solo al Agente FAQ. Si la clasificación lo agota, el resultado es `ERROR` (F4) y Java devuelve `NADA` | Cortar solo al Agente FAQ: con un reintento del LLM, el pedido podía pasar de 30 s | No (solo agrega, §6 de JAVA_IA_v1) |
| 7 | La IA simulada de `EnVivoApiTest` es un `@MockitoBean NlpDataClient`, como en `ClasificacionTest`. El HTTP real hacia la IA ya lo prueba `NlpDataClientTest` con `MockRestServiceServer` | `MockRestServiceServer` también en `EnVivoApiTest` (la ficha lo nombra): habría que reemplazar el `RestClient` del contexto completo solo para eso | No |
| 8 | La reserva en vivo usa `clasificacion.reserva-segundos` (120 s), más que los 30 s de espera a la IA | Una propiedad nueva | No |
| 9 | El bot se reescribió **en el mismo archivo**, `bot_communitylab.py`: el análisis y otros documentos lo citan por ese nombre | Un archivo nuevo y borrar el viejo | No |
| 10 | Para las pruebas del bot se instaló `discord.py` 2.7.1 en `%USERPROFILE%\.venvs\insightedu-discord` (como antes `fastapi`) | — | No |
| 11 | 👤 **Harrison (2026-10-04), después de la prueba real:** las fuentes llevan solo el nombre del PDF y la página. Se corrige en el origen (`reranker.py` cortaba la ruta solo con `/`, y el índice se armó en Windows) y, como defensa, en `grafo_v1.py` | Reconstruir el índice: en otra PC guardaría otra ruta, así que el problema seguiría | No: hace que `fuentes` cumpla lo que ya dice JAVA_IA_v1 ("documento y página"). Sale del alcance de la ficha por una línea del Agente FAQ |
| 12 | 👤 **Harrison (2026-10-04):** Java ya no agrega `📚 Fuente: …` al final, sino que publica el texto del Agente FAQ tal cual, que ya cita el documento que usó. `respuesta_fuentes` se sigue guardando | Mantener el pie con el nombre limpio: repetía la fuente y, a veces, mostraba otro documento (`buscador.py` usa `citaciones[0]`, el primero de los 3 fragmentos, no el que citó Gemini) | No: solo cambia el texto de `RESPONDER`. Actualizado en BOT_JAVA_v1 §3 y §4 |

## 6. Dudas, riesgos y pendientes

| # | Qué | Para quién |
|---|---|---|
| 1 | 🔎 `RESPONDIDA` se guarda **antes** de que el bot publique. Si Discord rechaza la respuesta (por ejemplo, por permisos), la base dice `RESPONDIDA` pero el alumno no la vio. El bot lo registra como error | Chat principal: ¿aceptarlo o agregar una confirmación del bot (cambiaría `BOT_JAVA_v1`)? |
| 2 | 🔎 Cuando se agota el tope, el Agente FAQ sigue trabajando en segundo plano (Python no detiene hilos) y **gasta esa llamada a Gemini**. Hay 4 hilos para el FAQ: si se trabaran todos, las dudas siguientes se derivarían | Aceptable para el MVP |
| 3 | El "escribiendo…" aparece en todos los mensajes de los dos canales, también en logros y comentarios (dura lo que tarda Java en responder) | Si molesta, se puede quitar en `#logros` |
| 4 | Las ediciones de mensajes no pasan por el bot: las toma el lote de la hora. Si se edita una duda ya respondida, vuelve a `PENDIENTE` pero **no** se responde otra vez (tiene `respuesta_estado`) | Comportamiento esperado (§3.5) |
| 5 | Si faltan variables, el bot se detiene y Docker lo reintenta cada tanto (`restart: unless-stopped`). Está documentado en OPERACION.md §7 | — |
| 6 | La entidad JPA `Mensaje` no tiene las 4 columnas de V3 (`ddl-auto=validate` lo permite). T08 puede agregarlas cuando las lea | T08 |
| 7 | Las URLs de los webhooks (que permiten publicar en esos canales) ahora también están en el `.env` de la raíz y en el contenedor `bot` (decisión 1) | Riesgo aceptado con la decisión |
| 8 | El aviso del bot cuando falta el token lo escribe `config.py` de la ingesta ("Copia .env.example como .env…"): sirve igual, pero no menciona el `.env` de la raíz | Mejora 🟡 |
| 9 | 🔎 Se recomienda registrar las decisiones 1, 11 y 12 en `DECISIONES.md` | Chat principal |
| 10 | `respuesta_fuentes` guarda **el primero** de los 3 fragmentos que encontró la búsqueda (`buscador.py`, `citaciones[0]`), que no siempre es el documento que citó Gemini. La fuente citada queda en `respuesta_texto`. Para guardarla bien habría que cambiar el Agente FAQ (devolver las 3 citas o la que usó) | Mejora 🟡, tarea futura |
| 11 | La fila `1556321387579449385`, de la primera ronda, quedó guardada **con la ruta de la PC del compañero** en `respuesta_fuentes`, porque se guardó antes de la corrección | ✅ Resuelto: Harrison la limpió con un `UPDATE` de esa sola fila (`UPDATE 1`) |
| 12 | El clasificador tomaba una pregunta fuera del curso ("¿cuál es la mejor pizzería?") como `COMENTARIO`, y el bot no respondía ni derivaba | ✅ Resuelto en la auditoría (sección 8): ahora es `PREGUNTA_FAQ` con tema `otro` y se deriva |
| 13 | 🔎 Pegar en el chat el contenido de `ingestion/discord/.env` expuso el token del bot, los webhooks y la clave de la ingesta | ⚠️ **Riesgo aceptado** por Harrison: no se cambian las claves |

## 7. Comandos que ejecutó Harrison

Desde la raíz, salvo donde se indica:

1. `python scripts/generar_api_key.py --cliente bot`
2. `docker compose up -d --build` (el bot se detenía: faltaban las variables de Discord)
3. El comando de PowerShell que copia 8 líneas de `ingestion/discord/.env` al `.env` de la raíz sin mostrarlas (`Copiadas 8 lineas`)
4. `docker compose up -d bot` y `docker compose logs bot`
5. Primera ronda en Discord y la consulta a `mensajes`
6. `docker compose up -d --build ia api-java` (decisiones 11 y 12)
7. Segunda ronda en Discord
8. Desde `ingestion\discord`, con el entorno activado: `python extract.py`, `python build_batch.py` y `python send_batch.py`
9. `docker compose logs bot --since 30m` y las consultas a la base
10. Los dos commits y el `git push` (sección 1)

## 8. Cambios después de la auditoría

El chat principal auditó la rama (commits `4a43e16` y `1985b6b`) y pidió dos cambios antes de fusionar.

### 8.1 Seguridad: la regla de DEC-70 se podía esquivar

🧪 **Hallazgo del chat principal:** `ApiKeyFilter` comparaba la ruta **cruda** (`getRequestURI`) con un mapa exacto. Con la clave del bot, `POST /api/v1/lotes;x=1` y `POST /api/v1/lote%73` llegaban al controlador (422) en vez de dar 403. Lo mismo pasaba con la clave de la ingesta en `/api/v1/mensajes/en-vivo`. Spring sí resuelve esas rutas al controlador: quita lo que va después de `;`, decodifica `%73` como `s` y junta las barras dobles.

**Corrección, en dos capas:**

| Capa | Qué hace | Archivo |
|---|---|---|
| a · El filtro | Compara la ruta **normalizada** como la resuelve Spring: `UrlPathHelper.defaultInstance.getPathWithinApplication(request)` (sin `;…`, decodificada y sin barras dobles) | `seguridad/ApiKeyFilter.java` (`rutaNormalizada`) |
| b · Cada controlador | Vuelve a exigir su cliente con el atributo `clienteApi` que deja el filtro. Si no es el suyo (o no hay), lanza `ProhibidoException` → 403 `PROHIBIDO`, con el formato común de error | `seguridad/ClientePermitido.java` (nuevo), `error/ProhibidoException.java` (nuevo), `error/ManejadorErrores.java`, `controller/LoteController.java`, `controller/MensajeEnVivoController.java` |

`/actuator/health` se sigue comparando con la ruta cruda: es más estricto y la salud no pide clave.

**Pruebas nuevas** (`EnVivoApiTest`, 8 más; la ruta se envía tal cual con `post(URI.create(...))`, para que MockMvc no la codifique):

| Prueba | Rutas | Resultado |
|---|---|---|
| `laClaveDelBotNoEntraALotesConUnaRutaDisfrazada` | `/api/v1/lotes;x=1`, `/api/v1/lote%73`, `/api//v1/lotes` | 403 `PROHIBIDO`; nada en `mensajes` ni en `lotes_recibidos` |
| `laClaveDeLaIngestaNoEntraALaPuertaEnVivoConUnaRutaDisfrazada` | `/api/v1/mensajes/en-vivo;x=1`, `/api/v1/mensajes/en-viv%6F`, `/api//v1/mensajes/en-vivo` | 403 `PROHIBIDO`; nada guardado y la IA no recibe nada |
| `elClienteCorrectoConUnPuntoYComaEnLaRutaSigueFuncionando` | El bot en `/api/v1/mensajes/en-vivo;x=1` | 200: la normalización no rompe al cliente correcto |
| `cadaControladorExigeSuClienteAunqueElFiltroNoLoFrene` | Llama a los dos controladores directamente, con el cliente equivocado y sin cliente | `ProhibidoException` en los 4 casos (capa b sola) |

🧪 En el registro de esa corrida, las 6 rutas disfrazadas las frenó **el filtro** (capa a), ya normalizadas: `Pedido rechazado: el cliente bot no puede usar POST /api/v1/lotes` y `… el cliente ingesta no puede usar POST /api/v1/mensajes/en-vivo`.

### 8.2 Preguntas que no son del curso: se derivan al mentor

👤 **Decisión de Harrison:** una pregunta fuera del curso (por ejemplo, "¿cuál es la mejor pizzería de Bogotá?") es `PREGUNTA_FAQ` con tema `otro`. El Agente FAQ no le encuentra respaldo y el bot la deriva al mentor (`DERIVAR`). Antes, Gemini la clasificaba como `COMENTARIO` y el bot no hacía nada (sección 4.5, primera ronda).

**Cambio** en `SYSTEM_PROMPT` (`agents/orquestador/clasificadores/etiquetador.py`):
- `PREGUNTA_FAQ`: "…pide ayuda con una duda concreta, **AUNQUE NO SEA DEL CURSO** (por ejemplo, "¿cuál es la mejor pizzería de Bogotá?")".
- Reglas: "Si contiene una pregunta real, es PREGUNTA_FAQ, sea o no del curso: una pregunta que no es del curso NUNCA es COMENTARIO ni OTRO, y su tema es otro (así la revisa un mentor)".
- Tema `otro`: "nada de lo anterior, incluidas las preguntas que no son del curso".

No cambia el contrato Java ↔ IA: los valores son los mismos.

**Pruebas nuevas** (`test_v1_procesar.py`, 2 más):
- `test_las_reglas_dicen_que_una_pregunta_fuera_del_curso_es_pregunta_faq_con_tema_otro`: el prompt tiene las tres reglas.
- `test_una_pregunta_fuera_del_curso_va_al_faq_y_vuelve_sin_respaldo`: el LLM recibe ese prompt; la pregunta de la pizzería sale `PREGUNTA_FAQ`/`otro`, pasa por el Agente FAQ y vuelve con `encontrada = false`. Que Java convierta eso en `DERIVAR` ya lo prueba `dudaSinRespuestaDaDerivar`.

🔎 Una prueba sin Gemini solo demuestra que **el prompt** tiene la regla, no que Gemini la siga. Eso lo demuestra la prueba real (8.4).

### 8.3 Pruebas después de la auditoría

| Comando | Resultado (🧪) |
|---|---|
| Java, en Docker contra `insightedu_test` | **80 pruebas, 0 fallas**: `EnVivoApiTest` 29 (antes 21), `ClasificacionTest` 15, `LotesApiTest` 19, `ModeloDatosTest` 10, `NlpDataClientTest` 6 y `BackendJavaApplicationTests` 1 |
| `python -m pytest agents/orquestador/tests -q` | **38 passed** (antes 36) |
| `python -m pytest agents/bot_discord/tests -q` | **22 passed** (sin cambios en el bot) |

### 8.4 Prueba real después de la auditoría

Después de `docker compose up -d --build ia api-java` (los 4 servicios sanos; el bot no cambió y siguió encendido):

**Pregunta fuera del curso, en `#dudas` (la escribió Harrison):** "Cual es la mejor pizzeria en bogota?"

| Dónde | Resultado (🧪) |
|---|---|
| Discord | "¡Gracias por tu pregunta! No encontré una respuesta segura en los documentos del curso, así que un mentor te responderá pronto. 🙏" |
| Registro del bot | `Mensaje 1556354969073090765 (#dudas, …): orden DERIVAR · 4751 ms` |
| Base | `PREGUNTA_FAQ`, tema `otro`, método `llm`, `OK`, `respuesta_estado = DERIVADA`, `respondido_en` con fecha |

**Rutas disfrazadas contra el Java real.** Las corrió el chat de tarea desde el contenedor `bot`, con su `API_KEY_BOT` leída del entorno y sin imprimirla, y con cuerpo `{}`, así que nada podía guardarse:

```
/api/v1/lotes 403 PROHIBIDO
/api/v1/lotes;x=1 403 PROHIBIDO
/api/v1/lote%73 403 PROHIBIDO
/api//v1/lotes 403 PROHIBIDO
```

Antes de la corrección, las dos del medio llegaban al controlador (hallazgo del chat principal).
