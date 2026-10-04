# Operación — levantar InsightEdu Lab con Docker

> **Estado:** v0.3 · **Fecha:** 2026-10-04 · **Rama:** `feature/integracion-arquitectura-3`
> Cubre los servicios que ya están en `compose.yml`: base de datos, API Java, IA y bot de Discord (T05). El panel y la ingesta se suman en las fases siguientes del [análisis](ANALISIS_INGENIERIA_PROPUESTA_3.md).

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
| `MOD_MODEL_NAME` | No | T06 · El modelo de Gemini que redacta los posts y casos de éxito (DEC-85). Vacío: el mismo de `GEMINI_MODEL` |
| `GENERACION_HABILITADA` | No | T06 · `true` por defecto. Con `false`, Java no pide borradores al Agente-Mod (cada logro nuevo gasta una llamada a Gemini) |
| `FAQ_SEMANAL_AL_ARRANCAR` | No | T06b · `false` por defecto. Con `true`, Java arma la FAQ semanal una vez al encender, para la demo (ver la sección 9) |
| `FAQ_SEMANAL_DIAS` | No | T06b · Cuántos días hacia atrás se juntan las dudas para la FAQ. `7` por defecto |
| `OCI_PAR_URL` | No | Una URL PAR nueva de OCI. Sin ella, la API arranca igual pero no sube a OCI |
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
| Levantar todo | `docker compose up -d --build` | La primera vez tarda (descarga PyTorch y los modelos de la IA). Termina con los 5 servicios en `Started`. ⚠️ **Enciende el bot**: antes, leer la sección 7 |
| Ver el estado | `docker compose ps` | `postgres`, `api-java`, `ia` y `panel` con `(healthy)` después de uno o dos minutos; `bot` en `Up` (no tiene prueba de salud) |
| Probar la API Java | `Invoke-RestMethod http://127.0.0.1:8008/actuator/health` | `status: UP` |
| Probar la IA | `Invoke-RestMethod http://127.0.0.1:8000/health` | `status: ok` |
| Abrir el panel | `http://127.0.0.1:8501` en el navegador | La pantalla "Iniciar sesión" (sección 10) |
| Ver los registros de un servicio | `docker compose logs -f ia` (o `api-java`, `postgres`, `bot`, `panel`) | Se cortan con `Ctrl+C` |
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

Los puertos escuchan solo en `127.0.0.1`: funcionan desde esta misma máquina y no quedan abiertos a la red. Si uno está ocupado por otro programa, se cambia el número de la izquierda en `compose.yml` (por ejemplo, `127.0.0.1:8009:8080`).

## 5. Base de datos y pruebas del backend

**Las tablas las crea Flyway** cuando arranca `api-java`, con los archivos SQL de `backend-java/src/main/resources/db/migration/` (`V1__…` a `V6__…`). Hibernate solo comprueba que coincidan (`ddl-auto=validate`).

⚠️ **Una migración ya aplicada nunca se edita.** Los cambios van en un archivo nuevo (el siguiente es `V7__…`).

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

⚠️ Para que una semana en `ERROR` se vuelva a intentar: `docker compose exec postgres psql -U insightedu -d insightedu -c "UPDATE faq_semanas SET estado = NULL, intentos = 0, terminada_en = NULL WHERE estado = 'ERROR';"`. El reintento la toma en menos de 30 minutos.

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
| Revisar un borrador | Página **Borradores**: elegir el estado (pendientes, aprobados o rechazados), el tipo y el borrador. A la izquierda, el mensaje original y por qué lo propuso la IA; a la derecha, el texto editable |
| Aprobar un post o un caso de éxito | Marcar la casilla **"El alumno dio su consentimiento…"** (D6). Sin ella, el botón **Aprobar** queda apagado, y Java y la base tampoco lo aceptan |
| Editar | Cambiar el texto y **Aprobar** (la edición viaja con la aprobación), o **Guardar edición** para dejarlo pendiente |
| Rechazar | Abrir **Rechazar este borrador**, escribir el motivo (opcional) y **Rechazar** |
| Reintentar lo que quedó en `ERROR` | Página **Errores**: un botón **Reintentar** por mensaje. La clasificación vuelve a la cola (se procesa en unos 30 s) y la generación también (unos 60 s; gasta una llamada a Gemini) |
| Cerrar sesión | Botón **Cerrar sesión**, en la barra de la izquierda. La sesión también se cierra sola tras 8 horas sin uso |
| Agregar a otra persona | `python scripts/crear_usuario_panel.py --usuario ana` y `docker compose up -d panel` |
| Cambiar una contraseña | `python scripts/crear_usuario_panel.py --usuario harrison --reemplazar` y `docker compose up -d panel` |
| Quitar a una persona | Borrar su parte (`ana:scrypt:…`) de la línea `PANEL_USUARIOS` del `.env`, sin tocar las demás, y `docker compose up -d panel` |
| Apagar el panel | `docker compose stop panel` (el resto sigue funcionando). Para volver: `docker compose start panel` |
| Ver qué pasó | `docker compose logs panel` (inicios de sesión, sin contraseñas ni textos) y `docker compose logs api-java \| Select-String "Borrador"` (quién aprobó o rechazó qué) |

**Reglas que cuida Java:**
- Solo se cambian los borradores `PENDIENTE`. Si otra persona aprobó o rechazó el mismo borrador un momento antes, el panel avisa "otra persona lo revisó" y no cambia nada.
- Al aprobar se guardan quién (`aprobado_por`), cuándo (`aprobado_en`), cuánto tardó la revisión (`tiempo_curaduria_seg`, desde que se abrió el borrador) y el consentimiento (`consentimiento_confirmado`).
- Aprobar **no publica nada**: solo cambia el estado en la base. Subirlo a OCI es la tarea T09, y publicarlo en LinkedIn lo hace Marketing a mano.

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
