# Informe de la tarea T06b — FAQ semanal: las dudas repetidas se convierten en un borrador de preguntas frecuentes

| Dato | Valor |
|---|---|
| Fecha | 2026-10-04 |
| Modelo de Claude usado | Opus 5.5 (`claude-opus-5-5`) |
| Rama | `tarea/T06b-faq-semanal` |
| Commits | Dos, uno por parte (ver `git log`): `feat(ia): FAQ semanal y POST /v1/faq (T06b parte A)` y `feat(backend): FAQ semanal programada y migracion V5 (T06b parte B)` |

## 1. Resumen

Una vez por semana (lunes 8:00, hora de Bogotá), o al encender Java con `FAQ_SEMANAL_AL_ARRANCAR=true`, Java junta las dudas de los últimos 7 días y las envía a una puerta nueva de la IA, `POST /v1/faq`:
- **La IA** agrupa las dudas con una llamada a Gemini, cuenta con código las personas distintas (claves opacas `a1`, `a2`…) y deja solo las preguntas de 2 o más personas. La respuesta de cada grupo sale del bot o del buscador del Agente FAQ, solo con respaldo, y el texto lo arma el código.
- **Java** guarda un borrador `FAQ` `PENDIENTE` y registra la semana en la tabla nueva `faq_semanas` (V5), que impide dos FAQ de la misma semana.

Pasan 79 pruebas de la IA, 110 de Java, 22 del bot y 36 de la ingesta.

**Prueba real:** se juntaron 18 dudas y salieron 2 preguntas repetidas, las dos sin respuesta en los PDF (que son reglamentos). Al correr la tarea otra vez, no se creó una segunda FAQ. A Harrison le pareció bien.

## 2. Criterios de terminado

| Criterio | Estado | Evidencia |
|---|---|---|
| `/v1/faq` agrupa las dudas, responde solo con respaldo y lista aparte lo que los PDF no responden, sin nombres de alumnos | ✅ | `agents/agent_mod/faq_semanal.py`; 🧪 25 pruebas en `test_v1_faq.py`. Prueba real: sección "sin respuesta" con 2 preguntas y ningún nombre (§4.4) |
| Java genera **una** FAQ por semana, registra las semanas sin repetidas y reintenta los fallos hasta el máximo | ✅ | `faq_semanas.semana` es `UNIQUE` (V5). 🧪 `FaqSemanalTest` (10) y `FaqSemanalArranqueTest`. Prueba real: segunda corrida `OMITIDA`, `faqs = 1` |
| `JAVA_IA_v1.md` y su JSON Schema documentan `/v1/faq`, y las otras puertas no cambiaron | ✅ | `JAVA_IA_v1.md` §10 nueva, una línea en la cabecera y §8 actualizada. 💻 Schema: `git diff --numstat` = 313 líneas agregadas, 0 borradas. La prueba de T02 que compara el schema con los modelos pasa |
| Las pruebas de Java y Python pasan, y la prueba real muestra la FAQ en la base | ✅ | Sección 4 |
| Informe completo; no se tocó nada fuera del alcance | ✅ | No se tocaron el clasificador, el bot, el Agente-Mod (solo se importan funciones suyas), `/v1/procesar`, `/v1/generar`, las migraciones V1 a V4 ni el historial del Agente FAQ |

## 3. Archivos cambiados

Las rutas Java son relativas a `backend-java/src/main/java/com/insightedulab/backend_java/`.

### Parte A · La IA

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `agents/agent_mod/faq_semanal.py` | **Nuevo.** Partes: `FaqSemanalAgente` (agrupa con una llamada a Gemini, con la guía de voz, y responde dentro de un tope total); `construir_entrada` (al LLM solo le llegan el número, el tema y el texto, sin autores ni respuestas, y sin menciones `<@id>`); `_grupos_repetidos` (el código cuenta las personas; ignora números inventados y que una duda esté en dos grupos); `responder_con_buscador` (llama a `agente.buscador.ejecutar`, no a `responder()`); `componer_texto` (Markdown armado por el código); `con_signo_de_apertura` | Ficha §3.1 a §3.3, DEC-95, DEC-96, DEC-98 y DEC-83 |
| `agents/orquestador/api.py` | `POST /v1/faq` (`def`, como las otras puertas); la FAQ se crea una sola vez. El control de `X-Api-Key` de `/v1/…` ya la cubre | §3.4 |
| `agents/orquestador/contrato_ia.py` | Modelos nuevos: `PedidoFaq` (máximo 200 dudas; `autor` con el patrón `^a[0-9]{1,6}$`), `DudaSemana`, `RespuestaGuardada`, `GrupoFaq` y `RespuestaFaqSemanal`, con sus validaciones de coherencia. El schema suma la clave `faq` | §3.4 y §3.5 |
| `agents/orquestador/config.py` | `FAQ_SEMANAL_TOPE_S` (120), `FAQ_AGRUPAR_TIMEOUT_S` (45) y `FAQ_AGRUPAR_TEMPERATURE` (0,2) | §3.3 |
| `agents/orquestador/config_http.py` | `ENDPOINT_FAQ_V1` | — |
| `agents/orquestador/tests/test_v1_faq.py` | **Nuevo**: 25 pruebas | §5 |
| `docs/contratos/JAVA_IA_v1.md` | Cabecera con el cambio de T06b, §8 actualizada y **§10 nueva** (la puerta, el pedido, qué ve el LLM, ejemplos, campos y qué hace Java) | §3.5 |
| `docs/contratos/JAVA_IA_v1.schema.json` | Regenerado con `python -m agents.orquestador.contrato_ia` (solo agrega) | §3.5 |

### Parte B · Java

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `backend-java/src/main/resources/db/migration/V5__faq_semanal.sql` | **Nuevo.** Tabla `faq_semanas`: `semana` `UNIQUE`; `desde` y `hasta` (la ventana, fija desde el primer intento); `estado` (`GENERADA`, `SIN_REPETIDAS`, `ERROR` o vacío); `motivo`, `intentos` y los conteos; `borrador_id` (con un `CHECK` que exige borrador si y solo si está `GENERADA`); `reservada_hasta`. Más un índice parcial para las dudas | §3.6 |
| `faqsemanal/FaqSemanalService.java` | **Nuevo.** Registra la semana, la reserva y junta las dudas. Las claves opacas `a1`, `a2`… se arman por pedido. Llama a la IA sin transacción y guarda en **una** transacción el borrador y el estado. Si las dudas son de menos de 2 personas, no llama a la IA | §3.7 |
| `faqsemanal/FaqSemanalRepository.java` | **Nuevo.** El SQL: `ON CONFLICT DO NOTHING`; reserva con vencimiento; reintento con `SKIP LOCKED`; las dudas (`PREGUNTA_FAQ`, `OK`, `persona`, tema distinto de `otro`, dentro de la ventana, recortadas a los topes del contrato); y la respuesta del bot solo si está `RESPONDIDA` | §3.7 |
| `faqsemanal/FaqSemanalProgramada.java`, `FaqSemanalProperties.java`, `FaqSemanalConfig.java` | **Nuevos.** Tres disparadores: cron semanal; reintento cada 30 min; y al encender, 90 s después, en otro hilo, si `faq.al-arrancar=true`. Registro solo con números | §3.7, §3.8 y DEC-99 |
| `client/NlpDataClient.java` | `faq(pedido, idCorrelacion)`, con su propio `RestClient`. El envío y las excepciones se comparten con las otras puertas | §3.7 |
| `client/RespuestaFaqSemanal.java` | **Nuevo** | — |
| `config/RestClientConfig.java` | Bean `iaRestClientFaq`, con 150 s de lectura (`faq.tiempo-lectura-s`) | §3.7 |
| `application.properties` | `faq.*`, y `spring.task.scheduling.pool.size=3` (ver la decisión 7) | §3.7 |
| `test/…/FaqSemanalTest.java` | **Nuevo**: 10 pruebas | §5 |
| `test/…/FaqSemanalArranqueTest.java` | **Nuevo**: 1 prueba | §5, caso 7 |
| `test/…/NlpDataClientTest.java` | El constructor recibe los dos clientes, y +3 pruebas de `faq()` | §5 |
| `test/…/ClasificacionTest`, `EnVivoApiTest`, `GeneracionTest`, `LotesApiTest` y `ModeloDatosTest` | Solo `faq.habilitada=false`. En `BackendJavaApplicationTests`, `faq.cron=-` | Que la tarea nueva no tome las dudas de esas pruebas |
| `compose.yml`, `.env.example` | En `api-java`: `FAQ_SEMANAL_AL_ARRANCAR`, `FAQ_SEMANAL_DIAS`, `FAQ_SEMANAL_HABILITADA`, `FAQ_SEMANAL_CRON` y `FAQ_SEMANAL_ZONA`. En `ia`: `FAQ_SEMANAL_TOPE_S` | §3.9 |
| `docs/OPERACION.md` | Las variables nuevas en §2, la numeración de las migraciones en §5 y una **§9 nueva** (cuándo corre, cómo armarla para la demo sin tocar el `.env`, consultas de solo lectura, estados y cómo reintentar un `ERROR`) | §3.9 |

## 4. Pruebas

| Comando ejecutado | Resultado (🧪) |
|---|---|
| `python -m pytest agents/orquestador/tests -q` | **79 passed**: las 54 de antes + 25 nuevas |
| Java, en Docker contra `insightedu_test` (OPERACION.md §5) | **110 pruebas, 0 fallas**: las 96 de antes + 10 de `FaqSemanalTest` + 1 de `FaqSemanalArranqueTest` + 3 de `NlpDataClientTest` |
| `python -m pytest agents/bot_discord/tests -q` | **22 passed** (sin cambios) |
| `python -m pytest -q` (desde `ingestion/discord`) | **36 passed** (sin cambios) |
| `docker compose config --quiet` | Sin errores |

### 4.1 IA (25 nuevas, `test_v1_faq.py`)

| # de la ficha | Pruebas |
|---|---|
| 1 · Tres personas | `test_dudas_parecidas_de_3_personas_son_un_grupo_con_su_respuesta` (además, la respuesta cumple el schema) |
| 2 · Una sola persona | `test_un_grupo_de_una_sola_persona_no_entra_aunque_pregunte_dos_veces`, `test_el_llm_no_puede_contar_una_duda_dos_veces_ni_inventar_numeros` |
| 3 · Respuesta del bot | `test_con_una_respuesta_del_bot_la_usa_y_no_llama_al_agente_faq` |
| 4 · Agente FAQ | `test_sin_respuesta_guardada_le_pregunta_al_agente_faq_con_la_pregunta_del_grupo` |
| 5 · Sin respaldo | `test_sin_respaldo_en_los_pdf_va_a_la_seccion_sin_respuesta`, `test_si_todas_quedan_sin_respuesta_igual_hay_borrador`, `test_el_buscador_no_toca_el_historial_y_una_fidelidad_media_no_cuenta` (DEC-83 y DEC-49) |
| 6 · Ninguna repetida | `test_si_las_dudas_son_de_una_sola_persona_no_se_llama_al_llm`, `test_sin_dudas_no_hay_texto`, `test_las_dudas_del_tema_otro_no_cuentan` |
| 7 · Tope | `test_si_se_agota_el_tope_los_grupos_que_faltan_van_a_sin_respuesta` (la respuesta tardía no aparece; la del bot sí), `test_si_el_llm_que_agrupa_no_responde_a_tiempo_es_error`, `test_si_el_llm_falla_es_error_sin_el_detalle_del_proveedor`, `test_sin_llm_configurado_es_error` |
| 8 · Lo que recibe el LLM | `test_el_llm_recibe_solo_numero_tema_y_texto_sin_autores_ni_ids`, `test_una_clave_de_autor_que_no_es_opaca_es_422`, `test_una_duda_no_puede_salirse_de_su_etiqueta`, `test_la_guia_de_voz_llega_al_llm` |
| 9 · Fuentes | `test_las_fuentes_llevan_solo_el_documento_y_la_pagina` (rutas de Windows y de Linux) |
| 10 · 401 y 422 | `test_sin_clave_es_401_y_no_llama_al_llm`, `test_un_cuerpo_invalido_es_422_sin_repetir_los_datos`, `test_mas_de_200_dudas_es_422` |
| Contrato | `test_el_json_schema_documenta_faq_y_las_otras_puertas_no_cambiaron` |
| Después de la prueba real | `test_si_el_llm_olvida_el_signo_de_apertura_se_agrega` (ver la sección 6, punto 1) |
| 11 · Las 54 de antes | Pasan |

### 4.2 Java (10 de `FaqSemanalTest`, 1 de `FaqSemanalArranqueTest` y 3 de `NlpDataClientTest`)

| # de la ficha | Pruebas |
|---|---|
| 1 · Semana con repetidas | `unaSemanaConDudasRepetidasTieneUnBorradorFaqPendienteSinMensaje`, `laSemanaSeCuentaEnLaZonaConfigurada` |
| 2 · Otra vez | `correrOtraVezEnLaMismaSemanaNoCreaUnaSegundaFaq`, `dosEjecucionesALaVezArmanUnaSolaFaq` |
| 3 · Sin repetidas | `sinRepetidasLaSemanaQuedaRegistradaSinBorradorYSinReintentos`, `conDudasDeUnaSolaPersonaNoSeLlamaALaIa` |
| 4 · La IA falla | `siLaIaFallaSumaIntentosConLaMismaVentanaHastaQuedarEnError`, `unErrorDeLaIaUn422YUnaRespuestaIncoherenteCuentanComoIntento` |
| 5 · No viajan | `temaOtroComentariosBotsPendientesYFueraDeLaVentanaNoViajan` (tema `otro`, `COMENTARIO`, `botPropio`, `otroBot`, `PENDIENTE`, `ERROR`, hace 8 días y después de la ventana) |
| 6 · El pedido | `elPedidoLlevaLasRespuestasDelBotYClavesOpacasSinNombresNiIds`: en el JSON no aparecen el nombre visible, el usuario, los IDs de los autores ni los de los mensajes, ni el canal |
| 7 · Al arrancar | `FaqSemanalArranqueTest.conLaOpcionEncendidaCorreUnaSolaVezAlArrancar` |
| HTTP | `faqEnviaElPedidoConLaClaveYLeeLosGrupos`, `faqCon500Y422LanzaLasMismasExcepciones`, `laFaqEsperaMasQueElTopeDeLaIa` |
| 8 · Las 96 de antes | Pasan |

`FaqSemanalArranqueTest` falló en la primera corrida. 🧪 El registro mostraba que la tarea **sí** se había disparado, pero con 0 ms de espera corría antes de que empezara la prueba, y Spring reinicia el doble de prueba al empezar. Se le dio una espera de 2 s, solo en la prueba, y pasa.

### 4.3 Comprobaciones antes de la prueba real

🧪 Consulta de solo lectura, con números y sin textos: había 20 dudas `PREGUNTA_FAQ` `OK` de 8 personas, entre el 2026-09-28 y el 2026-10-04.
- 2 eran del tema `otro`.
- 2 de `inscripciones` eran de **una sola persona** y estaban respondidas por el bot.
- Con la ventana de 7 días entraban todas, así que no hizo falta cambiar `FAQ_SEMANAL_DIAS`.

### 4.4 Prueba real (la corrió Harrison, 2026-10-04)

En vez de agregar la línea al `.env`, se usó una **variable de la terminal** (`$env:FAQ_SEMANAL_AL_ARRANCAR = "true"`), que le gana al `.env` en `docker compose` y no exige abrirlo. Después: `docker compose up -d --build`. Había un solo bot encendido.

**Registro de `api-java`:**

```
Migrating schema "public" to version "5 - faq semanal"
FAQ semanal: se arma una vez al encender, en 90 s
FAQ semanal (al encender) 2026-W40: GENERADA · dudas 18, repetidas 2, con respuesta 0 · 4277 ms
--- docker compose restart api-java ---
FAQ semanal: se arma una vez al encender, en 90 s
FAQ semanal (al encender) 2026-W40: OMITIDA · dudas 0, repetidas 0, con respuesta 0 · 0 ms
```

**Registro de la semana:**

```
  semana  |  estado  | intentos | dudas | repetidas | con_respuesta | borrador_id |                          motivo
----------+----------+----------+-------+-----------+---------------+-------------+-----------------------------------------------------------
 2026-W40 | GENERADA |        1 |    18 |         2 |             0 |          11 | 2 preguntas repetidas, 0 con respuesta en los documentos.
```

**El borrador**, tal como quedó:

```
# Preguntas frecuentes de la semana (27/09 al 04/10/2026)

Cada paso en tu camino de aprendizaje cuenta y estamos aquí para acompañarte a resolver tus dudas. Consulta las respuestas a las preguntas más frecuentes de nuestra comunidad.

## Preguntas frecuentes sin respuesta en los documentos

Estas preguntas se repitieron, pero los documentos de la institución no las responden. Conviene sumarlas a la documentación o pedirle a un mentor que las responda.

- Cómo instalo Python en Windows? (la preguntaron 2 personas)
- Cuál es la diferencia entre una lista y una tupla? (la preguntaron 2 personas)
```

**Después de correrla otra vez:** `SELECT count(*) FROM borradores WHERE tipo = 'FAQ'` dio **`1`**. Al terminar, `Remove-Item Env:FAQ_SEMANAL_AL_ARRANCAR` y `docker compose up -d api-java`.

**Opinión de Harrison** 👤: *"me parece [bien] el FAQ semanal"*.

**Lectura de los resultados:**
- 🧪 Dudas: 18 = las 20 menos las 2 del tema `otro`.
- 🔎 Las 2 de `inscripciones` (una sola persona) no formaron grupo, como debe ser (DEC-98).
- 🔎 Que ninguna pregunta tenga respuesta es **correcto**: los 12 PDF del Agente FAQ son reglamentos, políticas y el calendario (💻 `agents/agent_faq/data`), y ninguno explica cómo instalar Python ni qué diferencia hay entre listas y tuplas. Es justo el aviso que busca DEC-96.
- 🔎 Gasto: una llamada para agrupar más dos consultas al buscador, unas 3 a 5 llamadas a Gemini. Menos de lo que estimaba la ficha, porque hubo solo 2 grupos.
- No aparece ningún nombre de alumno en el borrador.

## 5. Decisiones que se tomaron

👤 = aprobada por Harrison el 2026-10-04 ("apruebo" al diseño). Las demás son detalles de implementación.

| # | Decisión | Alternativas descartadas | ¿Cambia el contrato, la arquitectura o D1 a D7? |
|---|---|---|---|
| 1 | 👤 El proceso vive en `agents/agent_mod/faq_semanal.py`, junto al Agente-Mod, y reutiliza su guía de voz y `sin_menciones` | Un paquete aparte | No |
| 2 | 👤 **El LLM no recibe las claves de autor**: solo el número, el tema y el texto. Las personas distintas las cuenta el código | Pedirle al LLM que cuente | No (refuerza DEC-98) |
| 3 | 👤 Para las respuestas se llama a **`agente.buscador.ejecutar()`**, no a `AgenteFAQ.responder()`: 💻 `responder()` guarda cada pregunta en el historial interno (`ReporteTool`) | Usar `responder()` y ensuciar el historial con las preguntas de la FAQ | No (cumple DEC-83) |
| 4 | 👤 **El texto lo arma el código.** El LLM solo escribe las preguntas de los grupos y la introducción; las respuestas van tal cual | Que el LLM redacte el borrador completo: podría "mejorar" una respuesta con datos sin respaldo (D3) | No |
| 5 | 👤 Tabla **`faq_semanas`**: una fila por semana ISO en la zona configurada (`2026-W40`), con `semana` `UNIQUE`. La ventana se fija en el primer intento | Marcar la semana dentro de `borradores`: no puede registrar las semanas sin repetidas ni los fallos | No (V5 solo agrega) |
| 6 | 👤 Tres disparadores: **cron** (lunes 8:00, `America/Bogota`), **reintento** cada 30 min (solo de semanas sin terminar) y **al encender** (90 s después, en otro hilo). Si Java está apagado el lunes a las 8:00, esa semana se salta | Ponerse al día solo al encender: gastaría Gemini sin que nadie lo pida | No |
| 7 | 👤 `spring.task.scheduling.pool.size=3`: 💻 Spring corre todas las tareas programadas en un solo hilo, y la FAQ (hasta 150 s) habría frenado la clasificación y la generación | Dejar 1 hilo | No. Las otras tareas ya estaban protegidas con reservas para correr en paralelo |
| 8 | 👤 Si no hay dudas, o son de menos de 2 personas, Java registra `SIN_REPETIDAS` **sin llamar a la IA** | Llamar siempre | No |
| 9 | Un `RestClient` aparte para `/v1/faq`, con 150 s de lectura; la IA corta a los 120 s | Subir los 30 s de todas las puertas | No (D4 se mantiene en las otras) |
| 10 | La clave opaca exige el patrón `^a[0-9]{1,6}$`: un nombre o un ID de Discord da `422` | Aceptar cualquier texto | No (solo agrega) |
| 11 | Si el tope se agota, o el Agente FAQ falla, el grupo va a "sin respuesta" con su motivo. Si falla la llamada que **agrupa**, toda la respuesta es `ERROR` y Java reintenta | Devolver una FAQ a medias | No (F4) |
| 12 | Si **todos** los grupos quedan sin respuesta, igual hay borrador, con la sección "sin respuesta" | No generar borrador: se perdería el aviso de DEC-96 | No |
| 13 | Viajan como máximo 200 dudas, **las más recientes**. Los textos se recortan a 4000 caracteres, y la respuesta del bot a 8000 | — | No |
| 14 | Las dudas del tema `otro` las filtra Java y, como segunda defensa, también la IA | — | No |
| 15 | Los tokens guardados son los de la llamada que agrupa; los del Agente FAQ no se miden, igual que en `/v1/procesar` | — | No |
| 16 | La prueba real se hizo con una variable de la terminal en vez de editar el `.env` (OPERACION.md §9) | Agregar la línea al `.env` y acordarse de quitarla | No |

## 6. Dudas, riesgos y pendientes

| # | Qué | Para quién |
|---|---|---|
| 1 | 🧪 En la prueba real, el LLM escribió las preguntas **sin el "¿" inicial**. Se corrigió **después** de la prueba, con código (`con_signo_de_apertura`) y una prueba. Para verlo en vivo hay que reconstruir la IA: `docker compose up -d --build ia`. La FAQ ya guardada no cambia | Harrison (opcional) |
| 2 | 🧪 La IA avisa: *"Model 'gemini-3.5-flash-lite' uses fixed sampling defaults; the sampling parameter(s) temperature will be ignored"*. Con este modelo, `FAQ_AGRUPAR_TEMPERATURE` **no tiene efecto**, y 🔎 tampoco el `MOD_TEMPERATURE` de T06 (DEC-88) | Chat principal |
| 3 | 🔎 En el registro de `ia` no aparecen las líneas `log.info` de la IA (por ejemplo, `FAQ 2026-W40: dudas…`), y tampoco las de `/v1/generar`: el servicio no configura el registro de Python en nivel INFO. Ya pasaba antes de esta tarea | Chat principal (mejora 🟡) |
| 4 | 🔎 **Dato personal:** si un alumno escribe su nombre **dentro** de una duda, las instrucciones le prohíben al LLM copiarlo en la pregunta del grupo o en la introducción, pero no hay una defensa en código como la de DEC-87. Java no envía nombres, así que la IA no tiene contra qué compararlo. En la prueba real no apareció ningún nombre. Marketing revisa el borrador antes de publicarlo (N6) | Chat principal |
| 5 | Si Java está apagado el lunes a las 8:00, esa semana no tiene FAQ (decisión 6). Para armarla: `FAQ_SEMANAL_AL_ARRANCAR` (OPERACION.md §9) | — |
| 6 | Si se agota el tope, la consulta del Agente FAQ sigue en segundo plano hasta terminar y su resultado se descarta. 💻 Pasa lo mismo en `/v1/procesar` (Python no puede detener un hilo) | — |
| 7 | La FAQ usa el modelo del Agente-Mod (`MOD_MODEL_NAME`); hoy es el mismo que clasifica | — |
| 8 | `CLAUDE.md` §3 podría mencionar la FAQ semanal (`ia`: `POST /v1/faq`; `api-java`: la tarea semanal) | Chat principal |
| 9 | 🔎 Se recomienda registrar en `DECISIONES.md` las decisiones 2, 3, 4, 5, 6, 7 y 8 | Chat principal |

## 7. Comandos que ejecutó Harrison

1. 👤 Aprobó el diseño ("apruebo").
2. Desde la raíz, en PowerShell: `$env:FAQ_SEMANAL_AL_ARRANCAR = "true"` y `docker compose up -d --build`.
3. `docker compose ps` y `docker compose logs api-java | Select-String "FAQ semanal"`.
4. Las consultas de solo lectura de `faq_semanas` y del texto del borrador.
5. `docker compose restart api-java`, el registro otra vez y el conteo de borradores `FAQ`.
6. `Remove-Item Env:FAQ_SEMANAL_AL_ARRANCAR` y `docker compose up -d api-java`.
7. Los dos commits y el `git push` (en el cierre del chat).
