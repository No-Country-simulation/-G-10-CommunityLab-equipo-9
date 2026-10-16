# Informe de la tarea T14 — La ingesta corre sola cada hora, el panel avisa "Datos al día" y el bot resiste mejor a Gemini gratis

| Dato | Valor |
|---|---|
| Fecha | 2026-10-16 |
| Modelo de Claude usado | Opus 5.5 (el que recomendaba la ficha) |
| Rama | `tarea/T14-ingesta-automatica` |
| Commits | `7f6c524` (A, el servicio `ingesta`), `798d2f0` (B, la puerta de Java), `f189225` (C, el panel), `7ec9ceb` (D, la IA) y el de la Parte E (documentación y este informe) |

## 1. Resumen

El servicio `ingesta` (el sexto de Docker) corre la ingesta por lotes al arrancar y cada hora en punto, en hora de Bogotá, sin puertos y con su volumen. El panel muestra en la barra lateral, en todas las páginas, el recuadro "Estado de los datos" del prototipo, alimentado por la puerta nueva `GET /api/v1/dashboard/ingesta`. Los íconos del dashboard ya se ven. La IA reintenta un 503 o un 504 mientras quede tiempo del tope, después del respaldo, que ahora es `gemini-3.5-flash` por defecto. 🧪 Pasan las pruebas de todas las piezas: ingesta 53, Java 267, panel 153, IA 108 y bot 22. 🧪 La prueba real dio lo esperado: 6 servicios, la primera corrida rescató 42 mensajes y un mensaje escrito con el bot apagado llegó a la base con `--una-vez` (sección 7).

## 2. Criterios de terminado

| Criterio | Estado | Evidencia |
|---|---|---|
| El servicio `ingesta` corre al arrancar y cada hora en punto, sin puertos, con su volumen, sin `simulate_students.py` y sin textos en el registro | ✅ | `test_programador.py` (17 pruebas). La imagen revisada por dentro (sección 4.1). `docker compose config`: 6 servicios, `ingesta` sin `ports` |
| La barra lateral muestra el estado de los datos como el prototipo, en claro y en oscuro, y aguanta a Java caído | ✅ | `test_estado_datos.py` y capturas (sección 4.3) |
| El bot reintenta ante un 503 o un 504 solo mientras le queda tiempo, y nunca pasa del tope | ✅ | `test_reintento.py` (reloj simulado: se rinde a los 33,5 s con llamadas lentas) |
| El respaldo por defecto y los íconos del dashboard están hechos | ✅ | `compose.yml` y `.env.example`; capturas antes y después |
| La puerta nueva solo agrega y está en `PANEL_JAVA_v1.md` | ✅ | §7, con ejemplo y la nota "Agregado en T14" |
| Las pruebas de la ingesta, Java, el panel, la IA y el bot pasan, y la prueba real dio lo esperado | ✅ (falta solo ver la corrida de las 15:00, opcional) | Sección 4 y sección 7 |
| DEC-167 a DEC-170, DEC-140, ARQUITECTURA, AGENTS, README, OPERACION y ESTADO al día | ✅ | Sección 3 |
| El informe está completo y no se tocó nada fuera del alcance | ✅ | Sección 6: dos ajustes a pruebas existentes, explicados. No se tocaron el contrato v1, la puerta de lotes, `transform.py`, el Agente-Mod ni la FAQ semanal |

## 3. Archivos cambiados

**Parte A · El servicio `ingesta` (`7f6c524`)**

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `ingestion/discord/programador.py` (nuevo) | El servicio: `proxima_corrida` (hora en punto siguiente en Bogotá), `bloqueo` (archivo `corrida.lock` con `O_EXCL`, vence a los 30 min), `correr_una_vez` (nunca lanza), `servir` (al arrancar y cada hora; no corre dos veces la misma hora si el reloj despierta antes), `--una-vez` (0 bien, 1 falló, 2 en curso), `INGESTA_HABILITADA`, cierre limpio con SIGTERM y borrado de los lotes de más de 24 | Puntos 1 a 3 |
| `ingestion/discord/extract.py` | `ids_faltantes()` y `extraer()` separados de `main()`: devuelven solo números | Reutilizar sin copiar. `python extract.py` imprime lo mismo que antes |
| `ingestion/discord/build_batch.py` | `construir_lote()`, con `SinExtraccion` y `LoteInvalido`, separado de `main()` | Ídem |
| `ingestion/discord/Dockerfile` (nuevo) | `python:3.12-slim`, usuario `ingesta`, solo los 8 módulos necesarios, `data/` con dueño `ingesta` | Punto 1 |
| `compose.yml` | Servicio `ingesta` (sin puertos, `depends_on` de `api-java` sano, `restart: unless-stopped`), volumen `ingesta-datos`, `BACKEND_INGEST_URL=http://api-java:8080/api/v1/lotes`, `BACKEND_API_KEY=${API_KEY_INGESTA}` | Punto 3. 🔎 `send_batch.py` espera la URL **completa** de la puerta (hace `POST` a esa URL) |
| `.env.example` | `DISCORD_GUILD_ID`, `INGEST_REREAD_DAYS`, `INGESTA_HABILITADA` | Punto 3 |
| `ingestion/discord/tests/test_programador.py` (nuevo) | 17 pruebas | Pruebas 1 a 5 |

**Parte B · Java (`798d2f0`)**

| Archivo | Qué cambió |
|---|---|
| `DashboardController.java` | `GET /api/v1/dashboard/ingesta`, con la segunda revisión del cliente `panel` |
| `DashboardService.java`, `DashboardRepository.java`, `VistasDashboard.java` | `ingesta()`, la consulta `ULTIMO_LOTE` (solo `historial`, por `recibido_en` y `id`) y los records `UltimoLote` e `Ingesta` |
| `DashboardApiTest.java` | 11 pruebas más (sin lotes, varios lotes, claves, rutas disfrazadas, segunda capa). Reutiliza las propiedades de la clase (no abre otro contexto) |
| `docs/contratos/PANEL_JAVA_v1.md` | La puerta en §7: fila, ejemplo y nota "Agregado en T14" |

**Parte C · El panel (`f189225`)**

| Archivo | Qué cambió |
|---|---|
| `panel/app.py` | `_ultimo_lote()` (como mucho una vez por minuto, guardado en la sesión; cualquier error → "sin información") y `_estado_de_los_datos()`, entre la navegación y la sesión |
| `panel/estilo.py` | `estado_datos()`, `hace_minutos()`, `proxima_hora()`, las reglas `nav-datos-*` y los `ICONO_*` nuevos (fuente de íconos de Material en lugar de `<svg>`) |
| `panel/cliente_java.py` | `dashboard_ingesta()` |
| `panel/tests/test_estado_datos.py` (nuevo) | 17 pruebas |
| `panel/tests/test_paginas.py` | Una aserción ajustada (sección 6) |

**Parte D · La IA (`7ec9ceb`)**

| Archivo | Qué cambió |
|---|---|
| `agents/reintento_llm.py` (nuevo) | `ReintentoEnVivo`, `plazo_en_vivo` (un `contextvar` con la hora límite) y `codigo_pasajero` (`e.code` o su causa en 503/504) |
| `agents/orquestador/clasificadores/llm_models.py` y `agents/agent_faq/llm_models.py` | El clasificador y el Agente FAQ quedan envueltos: reintento → respaldo → modelo |
| `agents/orquestador/clasificadores/etiquetador.py` | En vivo: un solo intento propio (el reintento es del modelo), espera hasta el tope y el hilo hereda la hora límite. En historial, igual que antes |
| `agents/orquestador/grafo_v1.py` | El hilo del Agente FAQ hereda la hora límite |
| `compose.yml`, `.env.example` | `GEMINI_MODELO_RESPALDO` por defecto `gemini-3.5-flash` |
| `agents/orquestador/tests/test_reintento.py` (nuevo) y `test_v1_procesar.py` | 22 pruebas nuevas; 3 de T15 ajustadas (sección 6) |

**Parte E · Documentación**

DEC-167 a DEC-170 nuevas y DEC-140 al día (`DECISIONES.md`); ARQUITECTURA §1 (N1), §2 (el mapa), §3 (el sexto servicio), §4.1, §4.3, §4.7 (el aviso), §6, §8, §9, §10 y §12; AGENTS.md §3 (la fila de la ingesta, `reintento_llm.py`, 6 servicios y que la ingesta no es un segundo bot); README §1, §6, §7 y §8.3; OPERACION §2, §3, §4 y §16 (nueva); ESTADO §1, §2 (OE1 y OE8 ✅), §3 (despliegue sin la ingesta, Gemini) y §5.

## 4. Pruebas

Todas corrieron en contenedores desechables, sin tocar los servicios en marcha. Las de la ingesta, con una copia de `ingestion/discord` **sin** su `.env`, para que `config.py` no cargue claves reales.

| # | Comando | Resultado (🧪) |
|---|---|---|
| 1–5, 7 | `python -m pytest -q` (desde `ingestion/discord`, en `python:3.12-slim`) | ✅ `53 passed` (36 + 17) |
| 6 | `docker build -f ingestion/discord/Dockerfile` y revisar la imagen (después se borró) | ✅ Usuario `ingesta`; solo `build_batch.py`, `config.py`, `contract.py`, `discord_api.py`, `extract.py`, `programador.py`, `send_batch.py`, `transform.py` y `data/`; `find` no encuentra `simulate_students.py`, `simulation` ni `.env*` |
| 8–10 | `mvn test` (OPERACION §5, contra `insightedu_test`) | ✅ `Tests run: 267, Failures: 0, Errors: 0`, `BUILD SUCCESS` (256 + 11; `DashboardApiTest`: 55) |
| 11–14 | `python -m pytest tests -q` (desde `panel`, en la imagen `panel`) | ✅ `153 passed` (136 + 17) |
| 15–17 | `python -m pytest agents/orquestador/tests -q` (imagen `ia`) | ✅ `108 passed` (86 + 22) |
| 17 | `python -m pytest agents/bot_discord/tests -q` (imagen `bot`) | ✅ `22 passed` |
| — | El Agente FAQ y el clasificador arrancan con el envoltorio (clave falsa, sin Gemini) | ✅ `ReintentoEnVivo -> RunnableWithFallbacks` en los dos, y en la revisión |
| — | `docker compose config -q` | ✅ Válido; 6 servicios |

### 4.1 Lo que se comprobó antes de diseñar

| Pregunta | Respuesta |
|---|---|
| ¿La corrida de cada hora gasta Gemini? | 💻 No: `MensajeUpsertRepository` vuelve a `PENDIENTE` solo si cambió el **texto** |
| ¿La primera corrida lee 7 días? | 💻 No: sin marcador, `extract.py` lee **todo el historial** (`desde_donde` devuelve `None`). 🧪 Hoy hay 108 mensajes (88 en `#dudas` y 20 en `#logros`), y Java acepta hasta 1.000 por lote. Anotado como límite en ARQUITECTURA §12 |
| ¿El bot registra lotes? | 🧪 No: `lotes_recibidos` tiene 5 filas, todas `historial` |
| ¿La imagen de Python trae la hora de Bogotá? | 🧪 Sí: `zoneinfo.ZoneInfo('America/Bogota')` funciona en `python:3.12-slim` |
| ¿Cómo reconocer un 503? | 💻 LangChain convierte los errores del servidor en `GoogleAPIError` (hereda de `google.genai.errors.ServerError`) con `code`; los 4xx en `ChatGoogleGenerativeAIError` (sin `code`) |
| ¿`gemini-3.5-flash` existe? | 📘 [Bajas de modelos](https://ai.google.dev/gemini-api/docs/deprecations): cierre "N/A", "the endpoint is not shutting down", reemplazo `gemini-3.6-flash`, y ya no se puede elegir en AI Studio. 📘 No aparece en la [lista de modelos](https://ai.google.dev/gemini-api/docs/models). 🧪 La API lo lista (`models.list`) y respondió en 2,4 s (T15) |

### 4.2 El registro de la ingesta (prueba 5)

`test_el_registro_lleva_numeros_y_nunca_el_texto_de_un_mensaje` arma una corrida completa (Discord y Java de mentira) con un mensaje cuyo texto es `TEXTO-DE-ALUMNO-QUE-NUNCA-DEBE-IR-AL-REGISTRO`: el registro y la salida no lo contienen. Un error inesperado que trae ese texto en su mensaje (`KeyError`) se registra solo por su tipo.

### 4.3 Capturas

Como en T13: dos copias del panel (la de `main` y la de esta rama) en una red propia (`t14-capturas`), **sin puertos publicados**, con un Java de mentira (el `DashboardSimulado` de las pruebas más la puerta de la ingesta) y la sesión abierta por un lanzador que solo existió en el scratchpad. Chromium sin pantalla (Playwright 1.49.1) a 1440 px; el tema se cambió con `prefers-color-scheme`, **sin recargar**. Al terminar se borraron los contenedores y la red.

| Captura | Qué se vio |
|---|---|
| Barra lateral, después, claro y oscuro | El recuadro como el prototipo: ícono verde (medido: `rgb(12, 163, 12)` = `#0ca30c` en los dos temas), "Datos al día", "Última actualización: hace 12 min", "Próxima: 15:00 (cada hora, sola)". El fondo cambió de `rgb(255,255,255)` a `rgb(14,17,23)` sin recargar. La primera captura mostró las líneas montadas y el ícono sin color: se corrigió el CSS (el ícono de un markdown es `span[role="img"]`, y quitar el margen del párrafo rompía la compensación de Streamlit) y se repitió |
| Dashboard, antes | "Esperan respuesta", "A quién escribir" y "Qué falta en los documentos" **sin ícono** (el `<svg>` no se dibuja) |
| Dashboard, después, claro y oscuro | Reloj ámbar `rgb(209,143,12)`, alerta roja `rgb(224,82,74)` y documento con el color del texto, de **20 px** cada uno (medido en el navegador: la ligadura de la fuente funcionó; si no, la palabra mediría mucho más). También el reloj de "El más antiguo espera…" en Contenido |

## 5. Decisiones que se tomaron

| Decisión | Alternativas descartadas | ¿Cambia el contrato, la arquitectura o D1 a D7? |
|---|---|---|
| DEC-167: el servicio con reloj propio (decisión 1 de la ficha) | `cron` (no funciona igual en Windows) | **Arquitectura: sí**, un sexto servicio (la ingesta deja de ser manual). Contrato: no |
| DEC-168: el aviso y su puerta (decisión 2) | — | Contrato del panel: solo agrega |
| DEC-169: cuenta gratuita y respaldo `gemini-3.5-flash` por defecto (decisiones 3 y 5) | Una clave de pago (Harrison no la quiere) | No |
| DEC-170: el reintento (decisión 4) | `with_retry` de LangChain (no sabe del tope) | No |
| La puerta mira **solo los lotes `historial`** | Todos los lotes, como decía la ficha | Hoy da lo mismo (el bot no registra lotes); así el aviso mide la ingesta aunque eso cambie |
| **Orden:** el principal, enseguida el respaldo, y solo si los dos fallan, esperar 1,5 s y reintentar el par (como mucho 2 veces) | Reintentar el principal antes del respaldo | Un modelo saturado siguió así varios segundos el 2026-10-16, y cambiar de modelo no cuesta tiempo |
| Para reintentar hace falta que queden **espera + una llamada completa** (1,5 s + 20 s) | Reintentar con lo que quede | Es lo que pide la ficha: nunca empezar una llamada que el tope cortaría |
| En vivo, el clasificador **ya no repite** ante cualquier error (antes repetía 1 vez, también ante un 429) | Dejar los dos reintentos | Un 429 gasta la cuota; en vivo reintenta solo el envoltorio. En historial no cambia |
| `agents/reintento_llm.py`, fuera de `agents/agent_faq/` | Dentro del Agente FAQ | Importar `agents.agent_faq` carga el Agente FAQ entero (FAISS, modelos), y las pruebas de la IA corren sin eso |
| La hora límite viaja en un `contextvar`, copiado a los hilos | Pasar el plazo como parámetro al Agente FAQ | El Agente FAQ es de otro equipo: no cambia su firma |
| El estado de los datos se guarda **en la sesión** (60 s), no con `st.cache_data` | `st.cache_data(ttl=60)` | La caché global se mezclaba entre las pruebas y entre personas |
| Los íconos del dashboard con la **fuente** de Material dentro del mismo HTML | Pasarlos a markdown | Así los encabezados siguen en el HTML donde los buscan las pruebas del dashboard, que no cambiaron |
| Borrar los lotes de más de 24 h del volumen | Guardarlos todos | Traen datos personales, y uno por hora crece sin fin |

## 6. Dudas, riesgos y pendientes

1. **Ajustes a pruebas que ya existían** (no cambian lo que comprueban):
   - `panel/tests/test_paginas.py`: contaba exactamente 2 markdown en la barra lateral; ahora son 3 (el título del recuadro).
   - `agents/orquestador/tests/test_v1_procesar.py`: 3 pruebas de T15 miraban el tipo exacto del modelo; ahora el respaldo va **dentro** del reintento, y comprueban lo mismo un nivel más adentro.
2. **`gemini-3.5-flash`** ya no se elige en AI Studio y Google lo reemplazó por `gemini-3.6-flash` (que el 2026-10-16 tardó 24,6 s en una llamada mínima). Si un día deja de responder, cambiar el respaldo en el `.env` (OPERACION §15).
3. **Primera corrida y el tope de 1.000 mensajes por lote:** sin marcadores se lee todo el historial. Hoy son 108 mensajes; con más de 1.000 en una corrida, Java la rechaza (422) y la ingesta registra el error cada hora. Para la demo no es un problema.
4. **Un 429 detrás de un 503:** si el principal da 503 y el respaldo 429, LangChain informa el 503 (el error del primero) y el reintento repite el par. Caso raro; lo limita el máximo de 2 reintentos.
5. **El hilo del Agente FAQ** sigue corriendo en segundo plano cuando el tope corta (ya pasaba antes, ESTADO 🟡). Con el reintento no se agrava: no reintenta si no le alcanza el tiempo.
6. **Registro del panel en las pruebas:** los Java simulados de pruebas viejas no tienen `dashboard_ingesta`; el recuadro dice "sin información" y deja un aviso en el registro, sin romper nada.
7. El aviso de **dos bots**: AGENTS.md ahora dice que la ingesta usa el mismo token pero solo lee, y no cuenta como un segundo bot.

## 7. Comandos que ejecutó Harrison

1. Agregó `DISCORD_GUILD_ID` a su `.env` de la raíz (🧪 comprobado solo por el nombre: tiene valor).
2. `git add …` y `git commit -m "feat: servicio ingesta con reloj propio, al arrancar y cada hora en punto (T14 parte A)"` → `7f6c524`
3. `git add …` y `git commit -m "feat: puerta GET /api/v1/dashboard/ingesta con el ultimo lote de la ingesta (T14 parte B)"` → `798d2f0`
4. `git add …` y `git commit -m "feat: recuadro Estado de los datos en la barra lateral e iconos del dashboard visibles (T14 parte C)"` → `f189225`
5. `git add …` y `git commit -m "feat: reintento ante un 503 o 504 en vivo mientras quede tiempo y respaldo gemini-3.5-flash por defecto (T14 parte D)"` → `7ec9ceb`

### Prueba real

6. `docker compose up -d --build`
7. `docker compose stop bot`; escribió "Prueba de la ingesta T14" en `#dudas`; `docker compose exec ingesta python programador.py --una-vez`; `docker compose start bot`

### Prueba real (2026-10-16)

| Paso | Resultado (🧪) |
|---|---|
| 1 · `DISCORD_GUILD_ID` en el `.env` | ✅ Tiene valor (comprobado solo por el nombre) |
| 2 · `docker compose up -d --build` | ✅ **6 servicios**: `postgres`, `api-java`, `ia` y `panel` `(healthy)`; `bot` e `ingesta` `Up`. `ingesta` y `bot` **sin puertos** |
| 3 · La primera corrida (`docker compose logs ingesta`) | ✅ `Servicio de ingesta encendido…`; `Corrida terminada en 6.0 s: leídos #dudas 126, #logros 24; lote 7e2bb41f…: total 150, nuevos 42, actualizados 6, sin cambios 102`; `Próxima corrida: 2026-10-16 15:00 (hora de Bogotá)`. Sin marcadores leyó todo el historial, como se esperaba. Los **42 nuevos** son mensajes que la base no tenía (respuestas del bot y mensajes de las pruebas del día): justo lo que la ingesta debe rescatar |
| 4 · El panel | ✅ Desde el contenedor `panel`, con su propia clave: `GET /api/v1/dashboard/ingesta` devuelve el último lote (`total 79, nuevos 1`), y el recuadro queda "**Datos al día** · Última actualización: hace 1 min · Próxima: 15:00 (cada hora, sola)". Los íconos del dashboard, comprobados en las capturas (sección 4.3) |
| 5 · El rescate | ✅ Con el bot apagado, `--una-vez` dio `Corrida terminada en 4.6 s: leídos #dudas 73, #logros 6; lote 43b7846b…: total 79, nuevos 1, actualizados 0, sin cambios 78` (ya con marcadores: solo los últimos 7 días). En la base (sin mostrar el texto): 151 → **152** mensajes; el nuevo es el id 520, de `#dudas`, de una persona, de las 14:45 de Bogotá, con un texto de 24 caracteres (el de la prueba), **sin respuesta del bot** y en `PENDIENTE`: la clasificación en segundo plano lo toma en su turno (5 cada 30 s) |
| 6 · La corrida de la hora en punto | Pendiente: la próxima es a las 15:00 |

**Lo que se gastó de Gemini:** los 42 rescatados se clasifican en segundo plano, casi todos por regla (las respuestas del propio bot no van al LLM). Entre ellos había **logros** que la base no tenía: el Agente-Mod les redactó borradores (3 llamadas a `/v1/generar` en los primeros minutos). Es el comportamiento normal de un logro nuevo, no un efecto de la ingesta; las corridas siguientes ya no traen nada nuevo salvo los mensajes reales.
