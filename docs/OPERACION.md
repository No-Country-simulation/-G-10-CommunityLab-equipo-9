# Operación — levantar InsightEdu Lab con Docker

> **Estado:** v0.2 · **Fecha:** 2026-10-04 · **Rama:** `feature/integracion-arquitectura-3`
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
| `OCI_PAR_URL` | No | Una URL PAR nueva de OCI. Sin ella, la API arranca igual pero no sube a OCI |
| `API_KEY_INGESTA` | Sí, para recibir lotes | **No se escribe a mano.** Desde la raíz, `python scripts/generar_api_key.py` la crea al azar y la escribe aquí y en `ingestion/discord/.env` (`BACKEND_API_KEY`), sin mostrarla. Sin ella, la API Java rechaza todo con 401, salvo `/actuator/health` |
| `API_KEY_IA` | Sí, para clasificar | **No se escribe a mano.** `python scripts/generar_api_key.py --cliente ia` la crea y la escribe aquí, sin mostrarla. La usan los dos servicios: la API Java la envía y la IA la exige en `/v1/procesar`. Sin ella, los mensajes se quedan en `PENDIENTE` |
| `API_KEY_BOT` | Sí, para el bot | **No se escribe a mano.** `python scripts/generar_api_key.py --cliente bot`. El bot la envía y la API Java la exige en `/api/v1/mensajes/en-vivo`, **su única puerta** (DEC-70) |
| `DISCORD_BOT_TOKEN`, `DISCORD_CHANNEL_DUDAS_ID`, `DISCORD_CHANNEL_LOGROS_ID` | Sí, para el bot | **Copiar las líneas de `ingestion/discord/.env`**, con el mismo nombre y valor. Sin el token, el bot no arranca y se reinicia cada tanto (ver la sección 7) |
| `DISCORD_WEBHOOK_DUDAS_URL`, `DISCORD_WEBHOOK_LOGROS_URL`, `DISCORD_MENTOR_ROLE_IDS`, `DISCORD_STAFF_ROLE_IDS`, `SIMULATED_MENTORS` | Sí, para el bot | También se copian de `ingestion/discord/.env`. Con ellas el bot reconoce a los alumnos simulados y a los mentores igual que el lote de la hora (C2) |

El `.env` nunca se sube a git (está en `.gitignore`) ni entra a una imagen de Docker (está en `.dockerignore`).

## 3. Levantar, revisar y detener

| Para… | Comando | Qué debería pasar |
|---|---|---|
| Levantar todo | `docker compose up -d --build` | La primera vez tarda (descarga PyTorch y los modelos de la IA). Termina con los 4 servicios en `Started`. ⚠️ **Enciende el bot**: antes, leer la sección 7 |
| Ver el estado | `docker compose ps` | `postgres`, `api-java` e `ia` con `(healthy)` después de uno o dos minutos; `bot` en `Up` (no tiene prueba de salud) |
| Probar la API Java | `Invoke-RestMethod http://127.0.0.1:8008/actuator/health` | `status: UP` |
| Probar la IA | `Invoke-RestMethod http://127.0.0.1:8000/health` | `status: ok` |
| Ver los registros de un servicio | `docker compose logs -f ia` (o `api-java`, `postgres`, `bot`) | Se cortan con `Ctrl+C` |
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

Los puertos escuchan solo en `127.0.0.1`: funcionan desde esta misma máquina y no quedan abiertos a la red. Si uno está ocupado por otro programa, se cambia el número de la izquierda en `compose.yml` (por ejemplo, `127.0.0.1:8009:8080`).

## 5. Base de datos y pruebas del backend

**Las tablas las crea Flyway** cuando arranca `api-java`, con los archivos SQL de `backend-java/src/main/resources/db/migration/` (`V1__…`, `V2__…`, `V3__…`). Hibernate solo comprueba que coincidan (`ddl-auto=validate`).

⚠️ **Una migración ya aplicada nunca se edita.** Los cambios van en un archivo nuevo (el siguiente es `V4__…`).

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
