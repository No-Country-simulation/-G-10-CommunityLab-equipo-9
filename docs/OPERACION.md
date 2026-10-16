# Operación — levantar InsightEdu Lab con Docker

> **Estado:** v0.8 · **Fecha:** 2026-10-16 · **Rama:** `main`
> Cubre los servicios que ya están en `compose.yml`: base de datos, API Java, IA, bot de Discord (T05), panel (T07, T08) e ingesta automática (T14, sección 16), la subida de borradores a OCI (T09, sección 12), la publicación en LinkedIn (sección 13), cómo agregar un PDF al Agente FAQ (sección 14) y qué hacer si Gemini está lento o saturado (sección 15). Cómo funciona cada pieza: [ARQUITECTURA.md](ARQUITECTURA.md). Las menciones a T01–T10 remiten a la traza de [historico/tareas/](historico/tareas/).

Todos los comandos se ejecutan **desde la raíz del repositorio**, en PowerShell.

## 1. Requisitos

- **Docker Desktop** instalado y abierto. No hace falta instalar Java, Maven ni las librerías de la IA: todo se instala dentro de los contenedores.
- Unos 10 GB libres de disco, para las imágenes y los modelos de la IA.

## 2. Primera vez: el archivo `.env`

```powershell
Copy-Item .env.example .env
```

Abrir `.env` y completar:

| Variable | Obligatoria | Qué poner |
|---|---|---|
| `POSTGRES_PASSWORD` | Sí | Una contraseña larga inventada. Sin ella, la base de datos no arranca |
| `GEMINI_API_KEY` | No | La clave de Google AI Studio. Sin ella, la IA clasifica por palabras clave y el Agente FAQ no responde |
| `GEMINI_MODEL` | No | El modelo de Gemini del clasificador, del Agente FAQ y del Agente-Mod. `gemini-3.5-flash-lite` por defecto. Si Google lo rechaza con 503, ver la sección 15 |
| `GEMINI_MODELO_RESPALDO` | No | DEC-165 · Si Google rechaza `GEMINI_MODEL` (503), el clasificador y el Agente FAQ repiten la llamada con este modelo. Vacío: `gemini-3.5-flash` (DEC-169). Para no usar respaldo, el mismo valor de `GEMINI_MODEL`. Si los dos dan 503 o 504, en vivo se reintenta mientras quede tiempo (DEC-170). Cómo elegirlo: sección 15 |
| `DISCORD_GUILD_ID` | Sí, para la ingesta | T14 · El ID de tu servidor de Discord: el mismo valor de `ingestion/discord/.env`. Es un ID, no un secreto. Sin él, la ingesta automática registra "Faltan IDs" y no envía nada (sección 16) |
| `INGESTA_HABILITADA`, `INGEST_REREAD_DAYS` | No | T14 · `true` y `7` por defecto. `INGESTA_HABILITADA=false` apaga el reloj de la ingesta sin quitar el servicio; `INGEST_REREAD_DAYS` son los días que se releen cada hora (sección 16) |
| `TIEMPO_REAL_TOPE_S`, `IA_TIEMPO_LECTURA_S`, `TIEMPO_JAVA_S` | No | DEC-166 · Cuánto puede tardar una duda en vivo: tope de la IA (40 s), espera de Java a la IA (45 s) y espera del bot a Java (55 s). Si se cambian, **cada uno tiene que ser mayor que el anterior** |
| `MOD_MODEL_NAME` | No | T06 · El modelo de Gemini que redacta los posts y casos de éxito (DEC-85). Vacío: el mismo de `GEMINI_MODEL` |
| `GENERACION_HABILITADA` | No | T06 · `true` por defecto. Con `false`, Java no pide borradores al Agente-Mod (cada logro nuevo gasta una llamada a Gemini) |
| `FAQ_SEMANAL_AL_ARRANCAR` | No | T06b · `false` por defecto. Con `true`, Java arma la FAQ semanal una vez al encender, para la demo (ver la sección 9) |
| `FAQ_SEMANAL_DIAS` | No | T06b · Cuántos días hacia atrás se juntan las dudas para la FAQ. `7` por defecto |
| `OCI_PAR_URL` | No | T09 · La URL PAR **nueva** del bucket de OCI (solo escritura y con vencimiento). **Es una credencial: no se pega en un chat.** Cómo crearla: sección 12. Sin ella, la API arranca igual pero no sube nada a OCI |
| `OCI_HABILITADA` | No | T09 · `true` por defecto. Con `false`, Java no sube borradores a OCI aunque haya PAR |
| `LINKEDIN_HABILITADA` | No | DEC-149 · **`false` por defecto**: aprobar un post no publica nada. Con `true`, cada post de LinkedIn aprobado **se publica de verdad** si hay token y autor (sin ellos, solo se simula en el registro). Cómo encenderla: sección 13 |
| `LINKEDIN_ACCESS_TOKEN` | No | DEC-149 · El token de LinkedIn de la cuenta que publica. **Es una credencial: no se pega en un chat** |
| `LINKEDIN_AUTHOR_URN` | No | DEC-149 · Quién publica: `urn:li:person:<id>` (un perfil) o `urn:li:organization:<id>` (una página de empresa), sin punto final |
| `API_KEY_INGESTA` | Sí, para recibir lotes | **No se escribe a mano.** Desde la raíz, `python scripts/generar_api_key.py` la crea al azar y la escribe aquí y en `ingestion/discord/.env` (`BACKEND_API_KEY`), sin mostrarla. Sin ella, la API Java rechaza todo con 401, salvo `/actuator/health` |
| `API_KEY_IA` | Sí, para clasificar | **No se escribe a mano.** `python scripts/generar_api_key.py --cliente ia` la crea y la escribe aquí, sin mostrarla. La usan los dos servicios: la API Java la envía y la IA la exige en `/v1/procesar`. Sin ella, los mensajes se quedan en `PENDIENTE` |
| `API_KEY_BOT` | Sí, para el bot | **No se escribe a mano.** `python scripts/generar_api_key.py --cliente bot`. El bot la envía y la API Java la exige en `/api/v1/mensajes/en-vivo`, **su única puerta** (DEC-70) |
| `API_KEY_PANEL` | Sí, para el panel | **No se escribe a mano.** `python scripts/generar_api_key.py --cliente panel`. El panel la envía y la API Java la exige en `/api/v1/borradores` y `/api/v1/errores`, **sus únicas puertas** (DEC-70) |
| `PANEL_USUARIOS` | Sí, para el panel | **No se escribe a mano.** `python scripts/crear_usuario_panel.py` agrega un usuario con el hash de su contraseña (nunca la contraseña). Vacía: nadie entra al panel (sección 10) |
| `DISCORD_BOT_TOKEN`, `DISCORD_CHANNEL_DUDAS_ID`, `DISCORD_CHANNEL_LOGROS_ID` | Sí, para el bot | **Copiar las líneas de `ingestion/discord/.env`**, con el mismo nombre y valor. Sin el token, el bot no arranca y se reinicia cada tanto (ver la sección 7) |
| `DISCORD_WEBHOOK_DUDAS_URL`, `DISCORD_WEBHOOK_LOGROS_URL`, `DISCORD_MENTOR_ROLE_IDS`, `DISCORD_STAFF_ROLE_IDS`, `SIMULATED_MENTORS` | Sí, para el bot | También se copian de `ingestion/discord/.env`. Con ellas el bot reconoce a los alumnos simulados y a los mentores igual que el lote de la hora (C2) |

El `.env` nunca se sube a git (está en `.gitignore`) ni entra a una imagen de Docker (está en `.dockerignore`).

## 3. Levantar, revisar y detener

| Para… | Comando | Qué debería pasar |
|---|---|---|
| Levantar todo | `docker compose up -d --build` | La primera vez tarda (descarga PyTorch y los modelos de la IA). Termina con los 6 servicios en `Started`. ⚠️ **Enciende el bot**: antes, leer la sección 7. También enciende la ingesta automática (sección 16) |
| Ver el estado | `docker compose ps` | `postgres`, `api-java`, `ia` y `panel` con `(healthy)` después de uno o dos minutos; `bot` e `ingesta` en `Up` (no tienen prueba de salud) |
| Probar la API Java | `Invoke-RestMethod http://127.0.0.1:8008/actuator/health` | `status: UP` |
| Probar la IA | `Invoke-RestMethod http://127.0.0.1:8000/health` | `status: ok` |
| Abrir el panel | `http://127.0.0.1:8501` en el navegador | La pantalla "Iniciar sesión" (sección 10) |
| Ver los registros de un servicio | `docker compose logs -f ia` (o `api-java`, `postgres`, `bot`, `panel`, `ingesta`) | Se cortan con `Ctrl+C` |
| Entrar a la base de datos | `docker compose exec postgres psql -U insightedu -d insightedu` | Se sale con `\q` |
| Detener todo | `docker compose down` | Los datos se conservan en los volúmenes |
| ⚠️ Detener y **borrar los datos** | `docker compose down -v` | Borra la base de datos y el estado de la IA. No tiene vuelta atrás |

## 4. Servicios y puertos

| Servicio | Puerto en esta máquina | Desde otros contenedores | Volumen |
|---|---|---|---|
| `postgres` | ninguno (privado) | `postgres:5432` | `postgres-datos` |
| `api-java` | `127.0.0.1:8008` | `api-java:8080` | — |
| `ia` | `127.0.0.1:8000` | `ia:8000` | `ia-preguntas`, `ia-chroma` |
| `bot` | ninguno (no recibe conexiones: solo sale hacia Discord y hacia `api-java`) | — | — |
| `panel` | `127.0.0.1:8501` | — | — (no guarda nada: todo pasa por `api-java`) |
| `ingesta` (T14) | ninguno (solo sale hacia Discord, para leer, y hacia `api-java`) | — | `ingesta-datos` (marcadores, crudos y los lotes de las últimas 24 horas) |

Los puertos escuchan solo en `127.0.0.1`: funcionan desde esta misma máquina y no quedan abiertos a la red. Si uno está ocupado por otro programa, se cambia el número de la izquierda en `compose.yml` (por ejemplo, `127.0.0.1:8009:8080`).

## 5. Base de datos y pruebas del backend

**Las tablas las crea Flyway** cuando arranca `api-java`, con los archivos SQL de `backend-java/src/main/resources/db/migration/` (`V1__…` a `V9__…`). Hibernate solo comprueba que coincidan (`ddl-auto=validate`).

⚠️ **Una migración ya aplicada nunca se edita.** Los cambios van en un archivo nuevo (el siguiente es `V10__…`).

**Pruebas de Java** (no hace falta instalar Java en Windows). Usan una base aparte, `insightedu_test`. La prueba se niega a correr si la base no termina en `_test`, para no borrar la base principal.

| Paso | Comando |
|---|---|
| Crear la base de pruebas (solo la primera vez) | `docker compose exec postgres sh -c 'createdb -U "$POSTGRES_USER" insightedu_test'` |
| Correr las pruebas | `docker run --rm --network insightedu_default --env-file .env -e POSTGRES_HOST=postgres -e POSTGRES_DB=insightedu_test -v "${PWD}\backend-java:/app" -v insightedu-maven:/root/.m2 -w /app maven:3.9-eclipse-temurin-21 mvn test` |

Debería terminar con `Tests run: …, Failures: 0, Errors: 0` y `BUILD SUCCESS`.

## 6. Problemas comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| `postgres` no pasa a `healthy` | Falta `POSTGRES_PASSWORD` en `.env` | Completarla, y luego `docker compose down -v` y `docker compose up -d` (la base se crea con la primera contraseña) |
| `api-java` se reinicia una y otra vez | No conecta con la base | Revisar `docker compose logs api-java` |
| `port is already allocated` | Otro programa usa ese puerto | Cambiar el puerto, como en la sección 4 |
| La IA responde a todo como derivado a un mentor | Falta `GEMINI_API_KEY` | Completarla y `docker compose up -d` |
| `api-java` no arranca y el registro habla de Flyway y de un *"non-empty schema"* | La base tiene tablas que no creó Flyway | Si son datos de prueba: `docker compose stop api-java`, luego `docker compose exec postgres sh -c 'dropdb --force -U "$POSTGRES_USER" "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'` y `docker compose up -d api-java` |
| El bot está encendido pero no responde | Falta `API_KEY_BOT`, el bot y Java tienen claves distintas o la IA está caída | `docker compose logs bot` muestra `Java respondió HTTP 401` (o `403`) o la orden `NADA`. Revisar la sección 7 |
| Buscar en los registros con PowerShell no encuentra "Clasificación" | PowerShell 5.1 lee la salida de Docker con otra codificación y la tilde se rompe | Buscar sin la tilde: `docker compose logs api-java \| Select-String "Clasificaci"` (nota de T04) |

## 7. El bot de Discord (T05)

El bot escucha **solo** `#dudas` y `#logros`, envía cada mensaje a la API Java (`POST /api/v1/mensajes/en-vivo`) y cumple la orden que recibe: responder la duda, avisar que responderá un mentor, poner 🎉 a un logro o no hacer nada. Su contrato está en [contratos/BOT_JAVA_v1.md](contratos/BOT_JAVA_v1.md).

⚠️ **Regla: un solo bot encendido con el mismo token.** Si hay dos (por ejemplo, el de Docker y uno abierto a mano en una terminal, o el de otro clon del repositorio), **cada mensaje se responde dos veces**. Antes de encenderlo, comprobar que no quede otro corriendo:

| Para… | Comando | Qué debería pasar |
|---|---|---|
| Ver si hay otro bot en Docker | `docker ps --format "{{.Names}}"` | Solo debe aparecer `insightedu-bot-1` (o nada, si todavía no se encendió) |
| Ver si hay un bot abierto a mano | Revisar las terminales abiertas: no tiene que haber ninguna corriendo `bot_communitylab.py` | — |
| Encender **solo** el bot (con Java ya encendido) | `docker compose up -d --build bot` | `insightedu-bot-1  Started` |
| Ver qué hace | `docker compose logs -f bot` | `Bot conectado …` y, por cada mensaje, una línea con su ID, la orden y los milisegundos. **Nunca el texto** (S11) |
| Apagarlo | `docker compose stop bot` | El resto sigue funcionando. Los mensajes que lleguen mientras tanto los rescata el lote de la hora |
| Volver a encenderlo | `docker compose start bot` | — |

Si Java o la IA fallan, el bot **no responde nada** y lo registra (DEC-67). El mensaje queda `PENDIENTE` en la base, lo clasifica la tarea en segundo plano y, si era una duda, aparece como "sin responder".

Si falta `DISCORD_BOT_TOKEN`, `API_KEY_BOT` o el ID de un canal, el bot se detiene con un aviso en `docker compose logs bot` y Docker lo vuelve a intentar cada tanto (`restart: unless-stopped`). Para que deje de intentarlo: `docker compose stop bot`.

## 8. Borradores del Agente-Mod (T06)

Cada logro (`TESTIMONIO`, ya clasificado, de una persona) se convierte solo en dos borradores: un **post de LinkedIn** y un **caso de éxito**. Java revisa cada minuto si hay logros nuevos, de a 3 por vez, y se los pide a la IA (`POST /v1/generar`). Antes de redactar, la IA decide si el logro **vale la pena publicarse**: si no, no hay borrador y queda escrito el motivo. **Nada se publica**: los borradores quedan `PENDIENTE` hasta que Marketing los apruebe en el panel (T07).

La voz de los textos sale de [agents/agent_mod/guia_de_voz.md](../agents/agent_mod/guia_de_voz.md). Para cambiarla, se edita ese archivo y se reconstruye la IA: `docker compose up -d --build ia`.

| Para… | Comando (desde la raíz) |
|---|---|
| Ver qué pasó con cada logro | `docker compose exec postgres psql -U insightedu -d insightedu -P pager=off -c "SELECT discord_id, generacion_estado, generacion_intentos, generado_en, generacion_motivo FROM mensajes WHERE intencion = 'TESTIMONIO' ORDER BY fecha;"` |
| Ver los borradores (los primeros 300 caracteres) | `docker compose exec postgres psql -U insightedu -d insightedu -P pager=off -c "SELECT b.id, m.discord_id, b.tipo, b.estado, b.tokens_in, b.tokens_out, left(b.texto_ia, 300) AS texto FROM borradores b JOIN mensajes m ON m.id = b.mensaje_id ORDER BY b.id;"` |
| Comprobar que **ningún** borrador tiene el nombre completo ni el usuario del autor | `docker compose exec postgres psql -U insightedu -d insightedu -P pager=off -c "SELECT count(*) AS con_nombre_completo FROM borradores b JOIN mensajes m ON m.id = b.mensaje_id WHERE (position(' ' in m.contrato->'autor'->>'nombreVisible') > 0 AND b.texto_ia ILIKE concat('%', m.contrato->'autor'->>'nombreVisible', '%')) OR b.texto_ia ILIKE concat('%', m.contrato->'autor'->>'nombreUsuario', '%');"` (debería dar `0`) |
| Ver la tarea en el registro de Java | `docker compose logs api-java \| Select-String "Generaci"` (una línea por tanda, con números y sin textos) |
| Apagar la generación (por ejemplo, para no gastar llamadas a Gemini) | Poner `GENERACION_HABILITADA=false` en el `.env` y `docker compose up -d api-java` |

| Estado de generación | Qué significa |
|---|---|
| (vacío) | Todavía no se pidió, o falló y se va a reintentar |
| `GENERADO` | Tiene sus dos borradores `PENDIENTE` |
| `NO_PUBLICABLE` | La IA decidió que no vale un post; el motivo está en `generacion_motivo` |
| `ERROR` | Falló 3 veces (la IA caída, sin clave de Gemini o una respuesta inválida). No se vuelve a intentar solo |

⚠️ Si la IA estuvo caída un buen rato, varios logros pueden quedar en `ERROR`. Para que se vuelvan a intentar, se usa el botón **Reintentar** de la página "Errores" del panel (sección 10, DEC-111).

## 9. FAQ semanal (T06b)

Una vez por semana, Java junta las dudas de los alumnos de los últimos 7 días y le pide a la IA un **borrador de preguntas frecuentes** (`POST /v1/faq`). El borrador tiene:
- las preguntas que hicieron **al menos 2 personas distintas**, cada una con su respuesta: la del bot, si ya respondió, o la que encuentre el Agente FAQ en los PDF;
- aparte, las preguntas repetidas que los PDF **no responden**, para que la institución sepa qué falta en su documentación.

**Nada se publica**: el borrador queda `PENDIENTE` (`tipo = FAQ`) hasta que Marketing lo apruebe en el panel (T07).

**Cuándo corre:**

| Disparador | Cuándo | Variable |
|---|---|---|
| Semanal | Los lunes a las 8:00, hora de Bogotá | `FAQ_SEMANAL_CRON` y `FAQ_SEMANAL_ZONA` (opcionales) |
| Reintento | Cada 30 minutos, solo si la semana falló. Al tercer fallo queda en `ERROR` | — |
| Al encender | Una vez, 90 s después de encender Java (para que la IA termine de cargar). Para la demo | `FAQ_SEMANAL_AL_ARRANCAR=true` |

**Nunca hay dos FAQ de la misma semana**: la tabla `faq_semanas` tiene una fila por semana, con su estado. Si Java está apagado el lunes a las 8:00, esa semana se salta.

Cuánto gasta: una llamada a Gemini para agrupar las dudas, más 2 o 3 por cada pregunta repetida que el bot no había respondido. Con las dudas de la demo, unas 15 a 20.

| Para… | Comando (desde la raíz) |
|---|---|
| Armarla ahora, para la demo, **sin tocar el `.env`** | `$env:FAQ_SEMANAL_AL_ARRANCAR = "true"` y después `docker compose up -d api-java`. La variable de la terminal le gana a la del `.env`, y solo dura mientras la terminal esté abierta. Esperar unos 2 a 4 minutos |
| Juntar más días de dudas (por ejemplo, 10) | Antes de levantar: `$env:FAQ_SEMANAL_DIAS = "10"` |
| Ver la tarea en el registro de Java | `docker compose logs api-java \| Select-String "FAQ semanal"` (con números y sin textos) |
| Ver cada semana | `docker compose exec postgres psql -U insightedu -d insightedu -P pager=off -c "SELECT semana, estado, intentos, dudas, repetidas, con_respuesta, borrador_id, desde, hasta, motivo FROM faq_semanas ORDER BY semana;"` |
| Leer el texto de la última FAQ | `docker compose exec postgres psql -U insightedu -d insightedu -P pager=off -A -t -c "SELECT texto_ia FROM borradores WHERE tipo = 'FAQ' ORDER BY id DESC LIMIT 1;"` |
| Volver a la normalidad después de la demo | `Remove-Item Env:FAQ_SEMANAL_AL_ARRANCAR` y `docker compose up -d api-java` (o cerrar la terminal y abrir otra) |
| Apagar la FAQ semanal | Poner `FAQ_SEMANAL_HABILITADA=false` en el `.env` y `docker compose up -d api-java` |

| Estado de la semana | Qué significa |
|---|---|
| (vacío) | Se está armando, o falló y se va a reintentar (mirar `intentos` y `motivo`) |
| `GENERADA` | Tiene su borrador FAQ (`borrador_id`) |
| `SIN_REPETIDAS` | Ninguna pregunta la hicieron 2 personas distintas. No se vuelve a intentar |
| `ERROR` | Falló 3 veces (la IA caída, sin clave de Gemini o una respuesta inválida). No se vuelve a intentar solo |

Para que una semana en `ERROR` se vuelva a intentar (T13, DEC-161): en el panel, página **Errores** → lista **"FAQ semanal en ERROR"** → **Reintentar**. Java la devuelve a la cola y la arma enseguida, en segundo plano: tarda hasta unos minutos y gasta una llamada a Gemini. Si sale bien, aparece en **Borradores**; si vuelve a fallar, sigue con los reintentos de siempre (cada 30 minutos, hasta 3 intentos). Ya no hace falta SQL.

## 10. Panel de curaduría (T07)

En el panel, una persona de Marketing entra con **su usuario y su contraseña**, revisa los borradores (posts de LinkedIn, casos de éxito y la FAQ semanal) junto al mensaje que les dio origen, y los **edita, aprueba o rechaza**. El panel habla solo con la API Java ([contratos/PANEL_JAVA_v1.md](contratos/PANEL_JAVA_v1.md)): nunca con la base ni con la IA.

**Primera vez** (desde la raíz, en la terminal de VS Code):

| Paso | Comando | Qué debería pasar |
|---|---|---|
| 1. Crear la clave del panel | `python scripts/generar_api_key.py --cliente panel` | `✅ Clave nueva escrita en .env (API_KEY_PANEL)` |
| 2. Crear tu usuario | `python scripts/crear_usuario_panel.py --usuario harrison` | Pide la contraseña **dos veces sin mostrarla** (al menos 10 caracteres). Termina con `✅ Usuario harrison guardado…` |
| 3. Levantar Java (con la V6) y el panel | `docker compose up -d --build api-java panel` | `panel` en `(healthy)` en `docker compose ps` |
| 4. Entrar | Abrir `http://127.0.0.1:8501` | La pantalla "Iniciar sesión" |

⚠️ **Nunca escribas tu contraseña en un chat** ni en un archivo: el script te la pide en la terminal. En el `.env` queda solo un hash, del que no se puede sacar la contraseña.

**Uso diario:**

| Para… | Cómo |
|---|---|
| Revisar un logro | Página **Borradores** (T13): arriba, **Por revisar (n)**, **Aprobados** o **Rechazados** (n son tarjetas, no borradores). A la izquierda, la cola: una tarjeta por logro (su post y su caso de éxito) y una por FAQ, del más antiguo al más nuevo; un clic la abre. A la derecha, el mensaje original, por qué lo propuso la IA y una pestaña por texto, con **dónde se publica**, el texto editable y su contador |
| Aprobar un post o un caso de éxito | Marcar la casilla **"… dio su consentimiento para publicar su nombre y su historia. Vale para los dos textos."** (D6), una por logro. Sin ella, los botones **Aprobar** quedan apagados, y Java y la base tampoco lo aceptan. Cada texto se aprueba con **su** botón, en su pestaña; la tarjeta sale de la cola cuando no le queda nada pendiente |
| Saber si aprobar el post lo publica | El botón del post lo dice antes: **"Aprobar post"** con la nota "La publicación en LinkedIn está apagada…" (o "modo simulado"), o **"Aprobar y publicar en LinkedIn"**, que pide confirmar ("Publicar ahora" o "Cancelar"). Ver la sección 13 |
| Editar | Cambiar el texto y **Aprobar** (la edición viaja con la aprobación), o **Guardar edición** para dejarlo pendiente. Una edición sin guardar no se pierde al cambiar de pestaña o de tarjeta, pero sí al cerrar la sesión |
| Copiar un texto | **Copiar texto** y el ícono de copiar en la esquina del cuadro |
| Rechazar | **Rechazar…** (en la pestaña de ese texto), escribir el motivo (opcional) y **Rechazar el post** o **Rechazar el caso de éxito**. El otro texto no cambia |
| Reintentar lo que quedó en `ERROR` | Página **Errores**: un botón **Reintentar** por mensaje o por semana. La clasificación vuelve a la cola (se procesa en unos 30 s) y la generación también (unos 60 s; gasta una llamada a Gemini). La FAQ semanal se arma enseguida, en segundo plano (hasta unos minutos; gasta una llamada a Gemini) |
| Cerrar sesión | Botón **Cerrar sesión**, en la barra de la izquierda. La sesión también se cierra sola tras 8 horas sin uso |
| Agregar a otra persona | `python scripts/crear_usuario_panel.py --usuario ana` y `docker compose up -d panel` |
| Cambiar una contraseña | `python scripts/crear_usuario_panel.py --usuario harrison --reemplazar` y `docker compose up -d panel` |
| Quitar a una persona | Borrar su parte (`ana:scrypt:…`) de la línea `PANEL_USUARIOS` del `.env`, sin tocar las demás, y `docker compose up -d panel` |
| Apagar el panel | `docker compose stop panel` (el resto sigue funcionando). Para volver: `docker compose start panel` |
| Ver qué pasó | `docker compose logs panel` (inicios de sesión, sin contraseñas ni textos) y `docker compose logs api-java \| Select-String "Borrador"` (quién aprobó o rechazó qué) |

**Reglas que cuida Java:**
- Solo se cambian los borradores `PENDIENTE`. Si otra persona aprobó o rechazó el mismo borrador un momento antes, el panel avisa "otra persona lo revisó" y no cambia nada.
- Al aprobar se guardan quién (`aprobado_por`), cuándo (`aprobado_en`), cuánto tardó la revisión (`tiempo_curaduria_seg`: desde que se abrió la tarjeta, o desde el texto anterior revisado en ella) y el consentimiento (`consentimiento_confirmado`).
- Aprobar cambia el estado en la base, y una tarea en segundo plano lo guarda en OCI (sección 12). Un post aprobado, además, se manda a LinkedIn **solo si la publicación está encendida** (sección 13); si está apagada, Marketing lo publica a mano.

**Si algo falla:**

| Síntoma | Causa probable | Solución |
|---|---|---|
| "El panel no tiene usuarios configurados" | `PANEL_USUARIOS` está vacía | Paso 2 de arriba y `docker compose up -d panel` |
| "Usuario o contraseña incorrectos" con la contraseña correcta | El panel no tomó el usuario nuevo | `docker compose up -d panel` (lee el `.env` al encenderse) |
| "Demasiados intentos fallidos" | 5 contraseñas equivocadas seguidas con ese usuario | Esperar 5 minutos, o `docker compose restart panel` |
| "Falta API_KEY_PANEL" | No se creó la clave | Paso 1 y `docker compose up -d api-java panel` |
| "No se pudo conectar con la API Java" | `api-java` está apagado o reiniciándose | `docker compose ps` y `docker compose logs api-java` |
| "Esta clave no puede usar esta ruta" | El panel y Java tienen claves distintas | `docker compose up -d api-java panel`, para que los dos lean la misma |

**Consulta de solo lectura** (para revisar las aprobaciones en la base):
`docker compose exec postgres psql -U insightedu -d insightedu -P pager=off -c "SELECT id, tipo, estado, aprobado_por, aprobado_en, tiempo_curaduria_seg, consentimiento_confirmado, rechazado_por, motivo_rechazo, (texto_final IS NOT NULL AND texto_final <> texto_ia) AS editado FROM borradores ORDER BY id;"`

## 11. Dashboard (T08 y T12)

En el mismo panel, la página **Dashboard** tiene **una vista por rol** (DEC-153): **Comunidad**, para el Community Manager, y **Contenido**, para Marketing. No usa IA ni gasta Gemini: todo sale de las etiquetas que ya guardaron la clasificación y el bot. Java calcula y el panel dibuja ([contratos/PANEL_JAVA_v1.md §7](contratos/PANEL_JAVA_v1.md#7-dashboard-t08)).

| Para… | Cómo |
|---|---|
| Levantarlo (después de actualizar el código) | `docker compose up -d --build api-java panel`. T12 no tiene migración nueva |
| Abrirlo | Entrar al panel (`http://127.0.0.1:8501`) y elegir **Dashboard** en la barra de la izquierda |
| Cambiar de vista | **Vista**: *Comunidad* o *Contenido*. Cada una pide a Java solo lo suyo |
| Cambiar el período | **Período**: 7, 30 (por defecto) o 90 días hasta hoy, o **Elegir fechas** (solo entonces aparece el calendario; hay que elegir las dos fechas) |
| Ajustar las alertas (vista Comunidad) | **Ajustes de las alertas**: días sin escribir para la posible deserción (14 por defecto, DEC-119) y horas para una duda sin respuesta (24 por defecto) |
| Cambiar el tema (claro u oscuro) | Menú **⋮** (arriba a la derecha) → **Settings** → elegir el tema. Por defecto sigue el del sistema operativo. Los gráficos cambian de colores con el tema (DEC-156) |
| Cambiar el supuesto de las horas ahorradas | `PANEL_MINUTOS_POR_HISTORIA` en el `.env` (30 por defecto) y `docker compose up -d panel` |

**Cómo leerlo.** Cada porcentaje o índice lleva su **n** (cuántos datos hay detrás) y los tiempos son **medianas** (DEC-155): con pocos datos, mirar primero la n. Los datos de prueba se muestran tal como están.

| Indicador | Cómo se calcula |
|---|---|
| **Franja (las dos vistas):** horas ahorradas a Marketing (estimado) | (minutos por historia − mediana de revisión de los posts del período) × logros del período con su post aprobado. **Es una estimación** (DEC-154): supone `PANEL_MINUTOS_POR_HISTORIA` minutos por historia encontrada y redactada a mano, y el panel lo dice junto al número |
| **Franja:** historias encontradas solas | Logros del período que la IA marcó como publicables, junto a los mensajes de personas y los logros del período |
| Clima de los alumnos | (% positivos + muy positivos) − (% negativos + muy negativos), de −100 a +100, solo de alumnos; debajo, el de toda la comunidad. Compara con el período anterior del mismo largo **solo si ese período tiene mensajes** |
| Dudas que respondió el bot | Respondidas / (respondidas + derivadas): sobre las dudas que vio el bot. Debajo, la mediana de segundos que tardó, cuántas derivó y cuántas llegaron por lote sin pasar por él |
| Dudas sin respuesta | Dudas de alumnos con más horas que el umbral, que el bot no respondió y a las que **ninguna otra persona contestó con "Responder" de Discord** (DEC-123). Una duda derivada a un mentor sigue aquí hasta que alguien la conteste. **"Abrir en Discord"** lleva al mensaje |
| Alumnos que necesitan apoyo | Posible deserción: alumnos cuyo último mensaje tiene más días que el umbral, **contados desde hoy** (si el servidor está quieto, este número sube). Posible frustración: un mensaje `MUY_NEGATIVO` en el período, o 2 negativos entre sus últimos 3 mensajes **del período** (DEC-121, DEC-157) |
| Clima por semana | Barras divergentes: los negativos a la izquierda del 0, los positivos a la derecha y el neutro partido al medio. Cada fila suma 100 % y lleva su índice y su n; **Ver los números** abre la tabla. Con 7 días, va por día |
| Alumnos activos | Alumnos con al menos un mensaje en los 7 y en los 30 días que terminan en la fecha final, sobre todos los que escribieron alguna vez |
| De qué hablan los alumnos · Qué falta en los documentos | Mensajes de alumnos por tema · dudas que el bot derivó a un mentor, por tema: lo que conviene sumar a los PDF |
| Por revisar | Borradores pendientes **hoy**, por tipo, y cuántos días espera el más antiguo |
| Tiempo de revisión · Tasa de aprobación | Mediana de segundos de revisión de lo aprobado o rechazado en el período, por tipo · aprobados / (aprobados + rechazados) |
| Del logro al post aprobado | Mediana desde el mensaje del logro hasta la aprobación de su post, de los posts aprobados en el período |
| De logro a contenido aprobado | Embudo: logros del período → publicables según la IA (con el %) → con su post aprobado (con el %). Los no publicables los decidió la IA antes de redactar (DEC-53) |
| Contenido aprobado por semana · Listos para publicar | Lo aprobado por semana de aprobación · los aprobados más recientes, con dónde se usa cada tipo y su texto final para copiar |
| Archivos guardados en OCI (barra lateral) | Subidas a OCI en `SUBIDO`, sin importar el período |

⚠️ **Para que una duda cuente como atendida, el mentor tiene que usar "Responder" en Discord** sobre el mensaje del alumno. Si escribe en el canal sin responder, el sistema no sabe a qué duda contestó.

**Consultas de solo lectura** para comprobar un número del dashboard (desde la raíz):

| Número | Comando |
|---|---|
| Sentimiento por día (hora de Bogotá) | `docker compose exec postgres psql -U insightedu -d insightedu -P pager=off -c "SELECT (fecha AT TIME ZONE 'America/Bogota')::date AS dia, sentimiento, count(*) FROM mensajes WHERE estado_clasificacion = 'OK' AND autor_tipo = 'persona' AND sentimiento IS NOT NULL GROUP BY 1, 2 ORDER BY 1, 2;"` |
| Último mensaje de cada alumno | `docker compose exec postgres psql -U insightedu -d insightedu -P pager=off -c "SELECT autor_id, max(fecha) AS ultimo, count(*) FROM mensajes WHERE autor_tipo = 'persona' AND autor_rol = 'miembro' GROUP BY autor_id ORDER BY ultimo;"` |

## 12. Borradores en OCI (T09)

**OCI** (Oracle Cloud Infrastructure) es la nube donde guardamos los archivos. Un **bucket** es una carpeta en esa nube. Una **PAR** (*pre-authenticated request*) es una dirección web con una clave secreta incluida: quien la tenga puede escribir en el bucket sin usuario ni contraseña. Por eso **es una credencial**: no se pega en un chat, no se sube a git y nunca aparece en un registro.

Una tarea de fondo de Java guarda cada borrador (post de LinkedIn, caso de éxito o FAQ) como un archivo **JSON** en el bucket:

| Carpeta | Qué va | Cuándo |
|---|---|---|
| `generados/` | **Todo** borrador que creó la IA, también el que después se rechazó | Al crearse (la tarea lo ve en menos de un minuto) |
| `aprobados/` | **Solo** los aprobados, con el texto final que dejó Marketing | Al aprobarse en el panel |

Las respuestas del bot no se guardan (no se aprueban). El nombre del archivo es estable y legible: `generados/POST_LINKEDIN/2026-10-04/borrador-12.json` (tipo, fecha en hora de Bogotá e id del borrador). Si OCI está caído, **generar y aprobar siguen funcionando**: la subida se reintenta sola, esperando 1, 2, 3 y 4 minutos entre intentos, y al quinto fallo queda en `ERROR`.

**Qué trae cada archivo** (y qué no): el borrador y sus datos. **Nunca** datos de Discord del alumno (ni su usuario, ni ids de Discord, ni el mensaje original completo): el primer nombre y la cita ya van dentro del texto.

| Campo | Qué es |
|---|---|
| `version`, `id`, `tipo`, `estado` | La forma del archivo (`1.0`), el id del borrador, su tipo y su estado al subirlo (`PENDIENTE`, `APROBADO` o `RECHAZADO`) |
| `textoIa`, `textoFinal` | Lo que propuso la IA y lo que dejó Marketing (`null` si nadie lo editó o lo aprobó) |
| `consentimientoConfirmado`, `aprobadoPor`, `aprobadoEn`, `tiempoCuraduriaSeg` | La aprobación: si se confirmó el consentimiento, quién (su usuario del panel), cuándo y cuánto tardó |
| `creadoEn`, `motivoIa`, `semana` | Cuándo lo generó la IA, por qué lo vio publicable (en la FAQ, el resumen de la semana) y, solo en la FAQ, la semana |

⚠️ **El archivo de `generados/` es una foto del borrador en el momento de subirlo.** Normalmente dice `PENDIENTE`; si OCI estuvo caído y ya lo revisaron, trae su estado actual. Y no se vuelve a subir: la PAR es de solo escritura, así que si el borrador se edita después, el archivo de `generados/` queda como estaba (el de `aprobados/` tiene la versión final).

### Crear la PAR (una sola vez)

La crea el dueño del bucket (o alguien con acceso a él en la consola de Oracle). 📘 Según la [documentación de Oracle](https://docs.oracle.com/en-us/iaas/Content/Object/Tasks/usingpreauthenticatedrequests_topic-To_create_a_preauthenticated_request_for_all_objects_in_a_bucket.htm):

1. Entrar a la consola de OCI y abrir **Storage → Buckets**, y luego el bucket.
2. En **Pre-authenticated requests** (a veces dentro de *Management* o *Recursos*), pulsar **Create pre-authenticated request**.
3. Completar: **Name**, por ejemplo `insightedu-t09`; **Target**: **Bucket**; **Access type**: **Permit object writes** (solo escritura); **Enable object listing**: **sin marcar**; **Expiration**: por ejemplo, el `2026-11-30` (después de la entrega).
4. Pulsar **Create** y **copiar la URL en ese momento**: 📘 *"The URL is displayed only at the time of creation… You can't access and retrieve it again"*. Si se cierra la ventana, hay que crear otra.
5. Pegarla en el `.env` de la raíz, en la línea `OCI_PAR_URL=`, **reemplazando la anterior**. Tiene que empezar con `https://objectstorage.` y terminar en `/o/`. **No la pegues en el chat.**
6. Aplicar el cambio: `docker compose up -d --build api-java`. Java la revisa al arrancar (sin mostrarla) y la tarea empieza a los 30 segundos. La primera vez sube **todos** los borradores que ya existían (de a 10 cada 30 segundos), no solo los nuevos.

⚠️ La PAR que un compañero había dejado en el `.env` **no se usa** (DEC-129): puede ser la que quedó en el historial público. Antes de levantar `api-java` con el código de T09, comprobar que `OCI_PAR_URL` tiene la PAR nueva. Con la PAR vieja, Java subiría los borradores a un bucket que no es el nuestro.

### Comprobar que llegaron los archivos

| Para… | Cómo |
|---|---|
| Ver la tarea en el registro de Java | `docker compose logs api-java \| Select-String "OCI"` (nombres de archivo, números y códigos HTTP; **nunca** la PAR). Al arrancar dice `OCI: hay una PAR con la forma esperada…`. Si dice `no hay URL PAR` o `no parece una PAR de bucket`, hay que corregir el `.env` |
| Ver los archivos en el bucket | En la consola de Oracle: **Storage → Buckets →** el bucket **→ Objects**. Aparecen las carpetas `generados/` y `aprobados/`. Abrir un archivo con **View object details** y revisar que no tenga datos de Discord |
| Ver el estado de cada subida | `docker compose exec postgres psql -U insightedu -d insightedu -P pager=off -c "SELECT s.id, s.borrador_id, b.tipo, s.carpeta, s.estado, s.intentos, s.subido_en, s.ultimo_error FROM subidas_oci s JOIN borradores b ON b.id = s.borrador_id ORDER BY s.id;"` |
| Contar por estado | `docker compose exec postgres psql -U insightedu -d insightedu -P pager=off -c "SELECT carpeta, estado, count(*) FROM subidas_oci GROUP BY 1, 2 ORDER BY 1, 2;"` |
| Ver el estado en el panel | Página **Borradores**, en el borrador elegido: **Guardado en OCI** (solo el estado, sin la ruta) |

| Estado de la subida | Qué significa |
|---|---|
| `PENDIENTE` | Falta subirla, o falló y está esperando para reintentar (mirar `intentos` y `ultimo_error`) |
| `SUBIDO` | Ya está en el bucket (la columna `ruta` tiene el nombre del archivo) |
| `ERROR` | Falló 5 veces (OCI caído, PAR vencida o sin permiso). No se reintenta sola |

### Cuando algo falla

| Síntoma | Causa probable | Solución |
|---|---|---|
| `ultimo_error` dice `OCI respondió HTTP 401`, `403` o `404` | La PAR venció, se borró o no es de ese bucket | Crear una PAR nueva (arriba), cambiarla en el `.env` y `docker compose up -d api-java`. Después, reintentar los `ERROR` (abajo) |
| `ultimo_error` dice `No se pudo hablar con OCI: …` | Sin internet, o OCI no respondió en 30 s | Esperar: se reintenta solo. Si quedaron en `ERROR`, reintentar (abajo) |
| No hay ninguna fila en `subidas_oci` | Falta la PAR, o `OCI_HABILITADA=false` | Mirar el primer aviso de `docker compose logs api-java \| Select-String "OCI"` |

**Reintentar los `ERROR`** (cuando ya se arregló la causa):

`docker compose exec postgres psql -U insightedu -d insightedu -c "UPDATE subidas_oci SET estado = 'PENDIENTE', intentos = 0, ultimo_error = NULL, reservada_hasta = NULL WHERE estado = 'ERROR';"`

La tarea los toma en menos de un minuto. Para **volver a subir uno que ya estaba `SUBIDO`** (por ejemplo, si alguien lo borró del bucket): `UPDATE subidas_oci SET estado = 'PENDIENTE', ruta = NULL, subido_en = NULL, intentos = 0 WHERE id = 1;`

**Cambiar de PAR o de bucket** (por ejemplo, pasar de una PAR de prueba a la definitiva, o a un bucket propio): lo que ya está `SUBIDO` **no se vuelve a subir solo**, porque Java ya lo dio por guardado. Por eso, después de cambiar `OCI_PAR_URL` en el `.env` y correr `docker compose up -d api-java`, hay que decirle a Java que lo suba todo otra vez al bucket nuevo:

`docker compose exec postgres psql -U insightedu -d insightedu -c "UPDATE subidas_oci SET estado = 'PENDIENTE', ruta = NULL, subido_en = NULL, intentos = 0, ultimo_error = NULL, reservada_hasta = NULL;"`

La tarea los toma de a 10 cada 30 segundos y los archivos conservan el mismo nombre. Los archivos del bucket anterior no se borran (la PAR es de solo escritura): si hace falta, se limpian desde la consola de Oracle. 🧪 Esta consulta se probó dentro de una transacción que se deshizo: pasó las 27 subidas a `PENDIENTE` sin romper ninguna regla de la tabla.

**Apagar la subida**: `OCI_HABILITADA=false` en el `.env` y `docker compose up -d api-java`. Los borradores se siguen creando y aprobando; cuando se vuelva a encender (con una PAR), se sube todo lo que faltó.

**Lo que esta tarea no hace**: no borra ni actualiza archivos del bucket (la PAR es de solo escritura), no lee desde OCI y no sube los registros de la IA (DEC-130).

## 13. Publicar en LinkedIn (DEC-149)

Cuando Marketing aprueba un **post de LinkedIn** en el panel, Java puede publicarlo solo en LinkedIn. **Viene apagado.** Los casos de éxito y la FAQ nunca se publican solos: quedan en OCI (`aprobados/`) para la web o una presentación.

| Modo | Cómo se activa | Qué pasa al aprobar un post |
|---|---|---|
| **Apagado** (por defecto) | `LINKEDIN_HABILITADA=false`, o sin la variable | Nada. El registro dice `Publicación en LinkedIn deshabilitada por configuración` |
| **Simulado** | `LINKEDIN_HABILITADA=true`, sin token o sin autor | No sale nada de la PC. El registro dice `[LinkedIn SIMULADO]` y el largo del texto (nunca el texto) |
| **Real** | `LINKEDIN_HABILITADA=true`, con token y autor | **Se publica en público**, en segundo plano: el panel no espera a LinkedIn. El registro dice `Post publicado en LinkedIn exitosamente. ID: urn:li:share:…` |

⚠️ En modo real **cada aprobación publica al instante y no se deshace desde el panel**: un post publicado se borra en LinkedIn. Por eso, en modo real el botón del post dice **"Aprobar y publicar en LinkedIn"** y pide confirmar (T13, DEC-159).

**Dónde se ve si un post se publicó** (T13, DEC-160): Java guarda el resultado en el borrador. En **Borradores**, filtro **Aprobados**, pestaña del post: "Publicado en LinkedIn el …" con el botón **Ver en LinkedIn**, "No publicado: la publicación en LinkedIn está apagada", "Simulado: LinkedIn está encendido sin token", "Falló: <motivo>" o "Sin dato" (aprobado antes de T13). En el **Dashboard → Contenido → Listos para publicar**, la columna **"En LinkedIn"** (Publicado · No: apagado · Simulado · Falló · Sin dato). Consulta de solo lectura: `docker compose exec postgres psql -U insightedu -d insightedu -P pager=off -c "SELECT id, aprobado_en, linkedin_estado, linkedin_post_id, linkedin_motivo FROM borradores WHERE tipo = 'POST_LINKEDIN' AND estado = 'APROBADO' ORDER BY id;"`

### Antes de una prueba real o de la demo

| Paso | Qué hacer |
|---|---|
| 1 | Acordar con el **dueño de la cuenta** en qué perfil o página se publica, y avisarle cuándo. La publicación es pública |
| 2 | Conseguir un token vigente de esa cuenta. 🔎 Los tokens de LinkedIn vencen (suelen durar unos 60 días): si la prueba da `401`, hace falta uno nuevo |
| 3 | Escribir en el `.env` de la raíz, **directo en el archivo y nunca a través de un chat**: `LINKEDIN_HABILITADA=true`, `LINKEDIN_ACCESS_TOKEN=…` y `LINKEDIN_AUTHOR_URN=urn:li:person:<id>` (o `urn:li:organization:<id>`). Ojo: es `person`, no `persom`, y sin punto final |
| 4 | Aplicar el cambio: `docker compose up -d api-java` |
| 5 | Comprobar que llegaron **sin mostrar los valores**: `docker compose exec api-java sh -c 'for v in LINKEDIN_HABILITADA LINKEDIN_ACCESS_TOKEN LINKEDIN_AUTHOR_URN; do eval "x=\${$v}"; if [ -n "$x" ]; then echo "$v: con valor"; else echo "$v: VACIA"; fi; done'` |
| 6 | **Primera publicación de prueba**: en **Borradores**, elegir un post pendiente, reemplazar todo su texto por uno neutro (por ejemplo, *"Prueba técnica de InsightEdu Lab: publicación automática desde el panel. Este post se borrará en unos minutos."*), marcar el consentimiento y aprobar |
| 7 | Ver la respuesta en el panel (el post aprobado dice "Publicado en LinkedIn el …") o en el registro: `docker compose logs api-java \| Select-String "LinkedIn"`. Si dice `publicado exitosamente`, el dueño de la cuenta lo ve en su perfil y lo borra |

🧪 Así se probó el 2026-10-13, en el perfil de un integrante y con su permiso: el borrador 14 se publicó en 1,4 s (`urn:li:share:7515972755511603201`).

### Durante la demo

- Aprobar solo posts revisados y con el consentimiento confirmado: cada uno se publica en el momento.
- Un post de más de **3.000 caracteres** no se deja aprobar: el contador se pone en rojo y avisa "LinkedIn acepta hasta 3.000 caracteres: acorta el post para aprobarlo" (DEC-160). Los posts de la guía de voz rondan los 1.000 caracteres.
- **No** correr `scripts/publicar_linkedin.py`: publica sin aprobación (DEC-150).

### Después

1. En el `.env`: `LINKEDIN_HABILITADA=false`, y borrar o comentar el token.
2. `docker compose up -d api-java`.
3. Borrar en LinkedIn los posts de prueba.

### Cuando algo falla

| El registro dice… | Causa probable | Solución |
|---|---|---|
| `deshabilitada por configuración` | `LINKEDIN_HABILITADA` no es `true` | Corregir el `.env` y `docker compose up -d api-java` |
| `[LinkedIn SIMULADO]` | Falta el token o el autor | Revisar las dos variables (paso 5) |
| `Error al publicar … 401` | 🔎 Token vencido o inválido | Pedir un token nuevo al dueño de la cuenta |
| `Error al publicar … 403` o `422` | 🔎 El token no tiene permiso para publicar, o el autor está mal escrito o no corresponde a ese token | Revisar el autor (`person`, sin punto) y que el token sea de esa misma cuenta |

**Lo que no hace**: no reintenta si LinkedIn falla (podría publicar dos veces; el panel muestra el motivo y se publica a mano) y no publica casos de éxito ni la FAQ. Las pruebas de Java **nunca** publican: el `pom.xml` apaga LinkedIn, igual que OCI.

**Los scripts de prueba** (DEC-150): `scripts/publicar_linkedin.py` muestra el JSON que se enviaría, pero **si el `.env` tiene token y autor, publica en el acto**. `scripts/insertar_borrador_prueba.sql` escribe un borrador directo en la base, sin pasar por Java y con una alumna inventada: solo para una base de pruebas. Detalle del módulo: [LINKEDIN_AUTOMATIZACION.md](LINKEDIN_AUTOMATIZACION.md).

## 14. Agregar o cambiar un PDF del Agente FAQ

El bot responde **solo** con los PDF de `agents/agent_faq/data/pdfs/` (DEC-19). El buscador usa un índice ya armado (`agents/agent_faq/data/vectorstore/faiss_pdfs/`), que está **guardado en git** y se copia a la imagen de la IA. Por eso, copiar un PDF a la carpeta no alcanza: hay que rehacer el índice.

| Paso | Comando o acción | Qué debería pasar |
|---|---|---|
| 1 | Copiar el PDF a `agents/agent_faq/data/pdfs/`, con un nombre que siga la numeración (el próximo es `14_…`), y sumarlo a `PDFS_NUEVOS` y a `PREGUNTAS` en `scripts/revisar_buscador_faq.py`, con 3 o 4 preguntas que solo él responda | — |
| 2 | `Remove-Item -Recurse -Force agents\agent_faq\data\vectorstore\faiss_pdfs` | Borra el índice viejo. La IA lo arma de nuevo al arrancar |
| 3 | `docker compose up -d --no-deps --build ia` | Esperar a que `docker compose ps` muestre `ia` como `(healthy)` (1 o 2 minutos) |
| 4 | `docker compose cp scripts/revisar_buscador_faq.py ia:/tmp/revisar_buscador_faq.py` y luego `docker compose exec -e PYTHONIOENCODING=utf-8 ia python /tmp/revisar_buscador_faq.py` | Prueba el buscador sin gastar Gemini: las preguntas que responden los documentos oficiales los siguen encontrando primero, las de cada PDF nuevo encuentran primero a su PDF, y **cada** PDF nuevo ocupa como máximo el 35 % del índice (también muestra el total). Debe terminar con `Resultado: todo OK` |
| 5 | `docker compose cp ia:/app/agents/agent_faq/data/vectorstore/faiss_pdfs agents/agent_faq/data/vectorstore/` | Copia el índice nuevo a la carpeta del repositorio |
| 6 | `git add -f agents/agent_faq/data/pdfs/<el PDF> agents/agent_faq/data/vectorstore/faiss_pdfs` | El `.gitignore` ignora `agents/*/data/`: por eso va `-f` |

Si no se rehace el índice, el bot sigue sin ver el PDF nuevo. Un PDF que todavía no está listo va a `agents/agent_faq/data/pdfs_en_revision/`, que la IA no lee (DEC-152).

**"Debilidad conocida" (DEC-164).** Tres preguntas oficiales (nota final, ChatGPT y publicar el nombre en LinkedIn) ya las resolvía mal el buscador **antes** de los PDF 12 y 13. El script las muestra como `DÉBIL` u `OK`, con el motivo escrito, pero no las cuenta como falla. Una pregunta nueva solo entra a esa categoría si se midió que ya fallaba sin el PDF nuevo y que el bot no responde peor. Cualquier otra falla sigue frenando el PDF.

**El PDF 13** (programa del bootcamp) se genera desde `scripts/pdf_programa/`: para cambiarlo se edita el `.md` y se corre el comando del comienzo de `generar.py`, en un contenedor desechable. Después, los pasos 2 a 6.

## 15. Gemini lento o saturado (DEC-165 y DEC-166)

**Síntoma.** El bot responde "No encontré una respuesta segura en los documentos…" a dudas que antes respondía. El buscador no tiene la culpa: el registro de la IA dice por qué.

```powershell
docker compose logs ia --since 15m
```

| El registro dice | Qué pasa | Qué hacer |
|---|---|---|
| `503 UNAVAILABLE` … `high demand` | Google está saturado con ese modelo. A la cuenta gratuita la rechaza primero | Configurar un modelo de respaldo (abajo). Para la demo, usar una clave **con facturación** |
| `se agotó el tope de 40 s` | Gemini responde, pero lento: las 3 llamadas de una duda no entran en el tope | Esperar a que baje la demanda, o subir los tres tiempos de la sección 2, manteniendo el orden |
| `404 NOT_FOUND` | El nombre del modelo no existe para esa clave | Corregir `GEMINI_MODEL` o `GEMINI_MODELO_RESPALDO` |

**Cambiar la clave no arregla un 503:** la saturación es del modelo, para todos. Una clave de **otro proyecto** de Google solo pone en cero la cuota diaria.

**Elegir el modelo principal y el de respaldo.** Primero se listan los modelos que acepta la clave. El comando imprime solo nombres, nunca la clave, y no gasta cuota:

```powershell
docker compose exec ia python -c "import os; from google import genai; c = genai.Client(api_key=os.environ['GEMINI_API_KEY']); [print(m.name) for m in c.models.list() if 'generateContent' in (m.supported_actions or []) and 'lite' in m.name]"
```

Después se prueba cada candidato con **una** llamada mínima: unas pocas palabras, y un 503 o un 404 no se cobran.

```powershell
docker compose exec ia python -c "import os, time; from google import genai; c = genai.Client(api_key=os.environ['GEMINI_API_KEY']); t = time.time(); print(c.models.generate_content(model='NOMBRE', contents='Responde solo: ok').text, round(time.time() - t, 1), 's')"
```

Conviene un modelo "lite" que responda en menos de 5 s. Uno que tarde 20 s no sirve: una duda hace 3 llamadas. Se escriben `GEMINI_MODEL` y `GEMINI_MODELO_RESPALDO` en el `.env` (dos modelos **distintos**), y se aplica con `docker compose up -d ia`.

⚠️ `GEMINI_MODEL` también cambia el modelo de la clasificación de todos los mensajes y de los borradores (D5).

## 16. La ingesta automática (T14, DEC-167)

El servicio `ingesta` corre la ingesta por lotes (extraer → armar → enviar) **una vez al arrancar** y después **cada hora en punto**, en hora de Bogotá. Rescata los mensajes que el bot no vio: si el bot estuvo apagado, o si Java o la IA fallaron en vivo.

| Para… | Comando | Qué debería pasar |
|---|---|---|
| Ver qué hizo | `docker compose logs ingesta` | Una línea por corrida: `Corrida terminada en N s: leídos #dudas N, #logros N; lote …: total N, nuevos N, actualizados N, sin cambios N`, y `Próxima corrida: AAAA-MM-DD HH:00`. Solo números y estados: nunca el texto de un mensaje |
| Correrla ya, sin esperar a la hora | `docker compose exec ingesta python programador.py --una-vez` | Termina con código 0 si salió bien, 1 si falló y 2 si ya había otra corrida en curso (nunca corren dos a la vez) |
| Apagar el reloj sin quitar el servicio | `INGESTA_HABILITADA=false` en el `.env` y `docker compose up -d ingesta` | El registro dice que el reloj está apagado. `--una-vez` sigue funcionando |
| Ver el estado en el panel | La barra lateral, en cualquier página | "Datos al día" (el último lote llegó hace menos de 2 horas), "Datos atrasados" o "Todavía no hay lotes" (DEC-168) |

**Necesita** `DISCORD_GUILD_ID` en el `.env` de la raíz (el mismo valor de `ingestion/discord/.env`), además de las variables de Discord del bot y `API_KEY_INGESTA`. Sin él, cada corrida registra `Faltan IDs en el .env` y no envía nada.

**No es un segundo bot.** Usa el mismo token, pero solo **lee** Discord por la API REST (GET): nunca escribe en un canal. Puede quedar encendido junto con el bot. Lo que AGENTS.md prohíbe son dos bots que **respondan**.

**Si una corrida falla** (Discord o Java caídos), lo registra, no mueve sus marcadores y espera a la hora siguiente: el servicio no se cae. La primera corrida con el volumen vacío lee **todo el historial** del servidor; después, lo nuevo y los últimos `INGEST_REREAD_DAYS` días. Nada se duplica: Java guarda por `discord_id` y reconoce un lote repetido. Una corrida en la que nada cambió no gasta Gemini: solo se reclasifica un mensaje si cambió su texto.

**Correrla a mano** (README §8.3) sigue funcionando, y no duplica nada: usa los marcadores de `ingestion/discord/data/`, no los del volumen `ingesta-datos`.

⚠️ El volumen `ingesta-datos` guarda mensajes de Discord (datos personales): nunca se copia fuera de Docker. Los lotes de más de 24 horas se borran solos. `docker compose down -v` también lo borra.
