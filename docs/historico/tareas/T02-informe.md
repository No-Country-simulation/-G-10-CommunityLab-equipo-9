# Informe de la tarea T02 — Formato Java ↔ IA

| Dato | Valor |
|---|---|
| Fecha | 2026-10-03 |
| Modelo de Claude usado | Opus 5.5 (`claude-opus-5-5`) |
| Rama | `tarea/T02-formato-java-ia` |
| Commits | Uno: `feat(ia): puerta /v1/procesar con el contrato v1 y contrato Java-IA v1 (T02)` (ver `git log`) |

## 1. Resumen

La IA tiene una puerta nueva, `POST /v1/procesar`, que recibe un lote del contrato v1 (importado de `contract.py`, sin copiarlo) y devuelve, por cada mensaje, intención, confianza, sentimiento, tema y estado `OK`/`ERROR`, con una sola llamada al LLM por mensaje. En `tiempoReal` agrega la respuesta del Agente FAQ. El contrato está documentado en `docs/contratos/JAVA_IA_v1.md`, con su JSON Schema. Pasan 23 pruebas de la IA y 34 de la ingesta, y la prueba real con Docker funcionó. `/procesar` sigue igual.

## 2. Criterios de terminado

| Criterio | Estado | Evidencia |
|---|---|---|
| `/v1/procesar` acepta el contrato v1 y devuelve un resultado por mensaje, con intención, sentimiento, tema y estado | ✅ | 🧪 `test_lote_valido_devuelve_un_resultado_por_mensaje_en_orden` y la prueba real (sección 4) |
| `ERROR` es distinto de `OTRO` (F4) | ✅ | 🧪 `test_si_el_llm_falla_el_estado_es_error_sin_intencion`, `…no_responde_a_tiempo…`, `test_sin_llm_configurado_es_error_y_no_palabras_clave`. Al romper el código a propósito para que el error salga como `OTRO`, esas 3 pruebas fallan |
| La respuesta del FAQ aparece solo en `tiempoReal` | ✅ | 🧪 `test_pregunta_en_tiempo_real_trae_respuesta`, `test_pregunta_en_historial_no_trae_respuesta`. Al romper el código a propósito para que responda también en `historial`, la segunda falla |
| El LLM tiene un tiempo máximo de 20 s | ✅ | 💻 `LLM_TIMEOUT_S=20` en el SDK (`timeout`, `max_retries=0`) más un corte propio. 🧪 `test_si_el_llm_no_responde_a_tiempo_es_error_y_no_se_reintenta`: con un tope de 0.1 s, corta antes de 0.45 s y no reintenta |
| `/procesar` (el del bot) sigue funcionando igual | ✅ | 🧪 `test_procesar_viejo_sigue_respondiendo_con_su_formato` y las 5 pruebas que ya existían. Ver el riesgo 3 de la sección 6 |
| `docs/contratos/JAVA_IA_v1.md` y su JSON Schema están escritos | ✅ | `JAVA_IA_v1.md`, `JAVA_IA_v1.schema.json`. 🧪 `test_el_json_schema_publicado_esta_al_dia` |
| Las pruebas pasan y la prueba real con Docker está hecha | ✅ | Sección 4 |
| Informe completo; no se tocó nada fuera del alcance | ✅ | 💻 `git status`: solo cambian `agents/` y `docs/`. No se tocó `ingestion/`, `compose.yml`, el bot ni Java |

## 3. Archivos cambiados

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `agents/orquestador/contrato_ia.py` | Nuevo: modelos de la respuesta (camelCase), lista de temas, formato de error y generador del schema. Importa `Lote` de `ingestion/discord/contract.py` | Alcance 1, 3 y 10 |
| `agents/orquestador/clasificadores/etiquetador.py` | Nuevo: una llamada al LLM por mensaje con salida estructurada, tope de 20 s, 1 reintento y `ERROR` en vez de `OTRO`. Respaldo por palabras clave solo si se elige | Alcance 3, 4 y 7 |
| `agents/orquestador/grafo_v1.py` | Nuevo: grafo LangGraph `preparar → clasificar → (responder_faq)`, con arista condicional | Alcance 2, 5, 6, 8 y 9 |
| `agents/orquestador/api.py` | + `POST /v1/procesar` (`def`, se ejecuta en otro hilo) y el manejador del 422 sin datos recibidos | Alcance 1, S7 |
| `agents/orquestador/config.py`, `config_http.py` | + `LLM_TIMEOUT_S`, `LLM_REINTENTOS` y `ENDPOINT_PROCESAR_V1` | Alcance 7 |
| `agents/orquestador/clasificadores/llm_models.py` | `timeout=LLM_TIMEOUT_S` y `max_retries=0` en Gemini, OpenAI y Anthropic | Alcance 7 (F8) |
| `agents/agent_faq/config.py`, `llm_models.py` | El mismo tope de 20 s para el LLM del Agente FAQ | Alcance 7 (F8) |
| `agents/Dockerfile` | Copia `ingestion/discord/contract.py` a la imagen | Alcance 1 (la ficha lo permite) |
| `agents/requirements-ia.txt` | `pydantic>=2.11.0` | `contract.py` usa `validate_by_name` y `serialize_by_alias` |
| `agents/orquestador/tests/test_v1_procesar.py` | Nuevo: 18 pruebas | Sección 5 de la ficha |
| `docs/contratos/JAVA_IA_v1.md`, `JAVA_IA_v1.schema.json` | Nuevos | Alcance 10 |
| `docs/contratos/ejemplos/lote_prueba_tiempo_real.json` | Nuevo: lote de 4 mensajes, armado con `transform.py` y los datos de prueba de la ingesta | Prueba real; T04 lo puede reutilizar |

## 4. Pruebas

| Comando ejecutado | Resultado (🧪) |
|---|---|
| `python -m pytest agents/orquestador/tests -q` (desde la raíz, entorno `insightedu-discord`) | `23 passed` (5 que ya existían y 18 nuevas) |
| `python -m pytest -q` (desde `ingestion/discord`) | `34 passed` |
| Romper el código a propósito: responder también en `historial` | `1 failed, 22 passed` (la detecta `test_pregunta_en_historial_no_trae_respuesta`) |
| Romper el código a propósito: disfrazar el error como `OTRO` | `3 failed, 20 passed` (la detectan las pruebas de F4) |
| `docker compose up -d --build ia` y `curl.exe http://127.0.0.1:8000/health` (Harrison) | `{"status":"ok",…,"faq_listo":true}` |
| `curl.exe -s -X POST http://127.0.0.1:8000/v1/procesar … --data-binary "@docs/contratos/ejemplos/lote_prueba_tiempo_real.json"` (Harrison, Gemini real) | 4 resultados, todos `OK`, en 11,3 s (ver abajo) |

Casos de la ficha y sus pruebas:

| # | Caso | Prueba |
|---|---|---|
| 1 | Lote válido → un resultado por mensaje | `test_lote_valido_devuelve_un_resultado_por_mensaje_en_orden`, `test_la_respuesta_cumple_el_json_schema_publicado` |
| 2 | Lote que no cumple el contrato → 422 claro (S7) | `test_lote_invalido_da_422_claro_sin_repetir_los_datos`, `test_cuerpo_que_no_es_json_da_422` |
| 3 | `botPropio`, `avisoSistema`, sin texto → `OTRO` sin LLM | `test_bot_aviso_y_sin_texto_son_otro_sin_llamar_al_llm` (incluye `otroBot`) |
| 4 | El LLM falla → `ERROR` sin intención | `test_si_el_llm_falla_…`, `test_un_fallo_pasajero_se_reintenta_y_sale_ok`, `test_si_el_llm_no_responde_a_tiempo_…`, `test_sin_llm_configurado_…` |
| 5 | `PREGUNTA_FAQ` en `tiempoReal` → trae `respuesta` | `test_pregunta_en_tiempo_real_trae_respuesta` |
| 6 | `PREGUNTA_FAQ` en `historial` → sin `respuesta` | `test_pregunta_en_historial_no_trae_respuesta`, `test_pregunta_con_error_no_va_al_faq` |
| 7 | El JSON Schema coincide con los modelos | `test_el_json_schema_publicado_esta_al_dia` |
| 8 | Las pruebas que ya existían | Las 5 de `test_invocador_faq.py` pasan, más `test_procesar_viejo_sigue_respondiendo_con_su_formato` |
| extra | D3: fidelidad media o FAQ caído → `encontrada=false` | `test_faq_con_fidelidad_media_…`, `test_faq_que_falla_no_rompe_el_lote` |

**Prueba real (Gemini, modo `tiempoReal`)**, resumida:

| Mensaje | Esperado | Resultado |
|---|---|---|
| "como instalo pyhton en windows?? …" | `PREGUNTA_FAQ` con respuesta | `PREGUNTA_FAQ` · 0.99 · `NEGATIVO` · `herramientas_entorno` · respuesta `encontrada: false`, motivo *"El contexto no cubre la pregunta."* |
| "me contrataron!!!!! …" | `TESTIMONIO` | `TESTIMONIO` · 1.0 · `MUY_POSITIVO` · `empleo` |
| "me gustó mucho la clase de ayer, por fin entendí recursividad" | `COMENTARIO` | ⚠️ **`TESTIMONIO`** · 0.95 · `MUY_POSITIVO` · `contenido_curso` (ver la sección 6) |
| "hola buenas noches" | `OTRO` | `OTRO` · 1.0 · `NEUTRO` · `comunidad` |
| Métricas | — | `duracionMs: 11301`, `tokensIn: 2073`, `tokensOut: 270` (unos 520 tokens de entrada por mensaje) |

La respuesta del FAQ con `encontrada: false` es correcta. Los PDFs son reglamentos de la institución y no explican cómo instalar Python, así que por D3 el bot no publicaría nada y derivaría a un mentor.

## 5. Decisiones que se tomaron

Todas validadas por Harrison el 2026-10-03 ("ok todo").

| Decisión | Alternativas descartadas | ¿Cambia el contrato, la arquitectura o D1 a D7? |
|---|---|---|
| **Lista de 11 temas**: los de la ficha más `calendario_clases` y `herramientas_entorno` | La lista de 9 de la ficha | No. 🧪 6 de las 14 dudas simuladas son de instalación o de errores de entorno, y el calendario tiene su propio PDF |
| Mensajes que no se clasifican: `OTRO`, `OK`, confianza `1.0`, `sentimiento` y `tema` en `null`, y `metodo: "regla"` | Sentimiento `NEUTRO` y tema `otro` | No. Así no ensucian el dashboard |
| Campo nuevo `metodo` (`llm` / `palabrasClave` / `regla`), que no estaba en la forma propuesta por la ficha | No informar quién decidió | No. Java distingue un `OTRO` del LLM de uno por regla |
| Sin LLM configurado → `ERROR`. Palabras clave solo con `ORQ_CLASIFICADOR_PROVIDER=keyword` | Pasar a palabras clave en silencio, como hace `/procesar` | No (es F4) |
| Tope de 20 s en dos capas (SDK más un corte propio), 1 reintento, sin reintentar si se agotó el tiempo | Un solo tope en el SDK | No. 🧪 Gemini venía con `max_retries=6` y `timeout=None` (langchain-google-genai 4.4.0, en la imagen `ia`) |
| D3: una respuesta del FAQ con fidelidad media cuenta como `encontrada=false` | Publicarla | No: aplica D3 |
| Error 422 con `{codigo, mensaje, errores[campo, problema], idCorrelacion}`, sin el `input` | El 422 de FastAPI, que repite los datos recibidos | No (aplica S7 y el formato común del análisis §2) |
| Pruebas en el entorno `insightedu-discord`, con `fastapi==0.142.2`, `langgraph==1.2.12` y `langchain-core==1.6.6` instalados (las mismas versiones que la imagen) | Correrlas dentro de Docker | No |

## 6. Dudas, riesgos y pendientes

1. **Logro o comentario.** En la prueba real, *"me gustó mucho la clase de ayer, por fin entendí recursividad"* salió `TESTIMONIO`. Lo provocan las instrucciones del clasificador, que cuentan como logro "superó una dificultad", y en la simulación *"hoy entendí recursividad!!!"* está en `#logros`. No se ajustó con un solo ejemplo. **Decidir en la fase 4** si los logros de aprendizaje generan borradores, o si el Agente-Mod los filtra por relevancia.
2. **Tiempos en `tiempoReal` (para T04).** Una duda encadena hasta 3 llamadas al LLM (clasificar, responder y el control anti-alucinación), cada una con un tope de 20 s. En el peor caso la suma supera los 30 s de Java → IA (D4). 🧪 En la prueba real, el lote de 4 mensajes con 1 duda tardó 11,3 s. Está documentado en `JAVA_IA_v1.md` §6.
3. **`/procesar` también recibió el tope de 20 s**, porque comparte `build_llm()`. Su formato no cambia, pero un fallo de Gemini ahora deja de esperar a los 20 s (`max_retries=0`), en vez de reintentar 6 veces sin límite. 🔎 Es una mejora, pero es un cambio de comportamiento.
4. **Tokens del Agente FAQ.** `metricas` solo cuenta los tokens del clasificador: el buscador del FAQ no los expone.
5. **El historial de preguntas.** En `tiempoReal`, el Agente FAQ sigue guardando cada pregunta en su índice de preguntas repetidas, como antes. Es una copia derivada (análisis §5).
6. **T04 puede agregar los `CHECK`** de `sentimiento` y `tema` en una migración `V2__…`, con las listas de `JAVA_IA_v1.md` §4.3.
7. **Entorno local.** Se instalaron `fastapi`, `langgraph` y `langchain-core` en `insightedu-discord`. 🔎 Conviene anotarlo en `docs/OPERACION.md` o en `CLAUDE.md` §4 (chat principal).
8. Advertencia sin efecto: `oci_client.py:49` usa `datetime.utcnow()`, que está obsoleta. Es código viejo de `/procesar` y no se tocó.

## 7. Comandos que ejecutó Harrison

Desde la raíz del repositorio:

| # | Comando | Resultado (🧪) |
|---|---|---|
| 1 | `git switch -c tarea/T02-formato-java-ia` (y los anteriores de la ficha §7) | Rama creada antes de empezar |
| 2 | `docker compose up -d --build ia` | Imagen reconstruida |
| 3 | `curl.exe http://127.0.0.1:8000/health` | `{"status":"ok","service":"orquestador","port":8000,"faq_listo":true}` |
| 4 | `curl.exe -s -X POST http://127.0.0.1:8000/v1/procesar -H "Content-Type: application/json" --data-binary "@docs/contratos/ejemplos/lote_prueba_tiempo_real.json"` | 4 resultados `OK` (sección 4) |
| 5 | `git add agents docs` y `git commit` | Commit de la tarea |

El chat de tarea instaló las 3 librerías en el entorno local con `pip install` y corrió las pruebas, con permiso de Harrison.
