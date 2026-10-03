# Operación — levantar InsightEdu Lab con Docker

> **Estado:** v0.1 · **Fecha:** 2026-10-03 · **Rama:** `feature/integracion-arquitectura-3`
> Cubre los servicios que ya están en `compose.yml`: base de datos, API Java e IA. El bot, el panel y la ingesta se suman en las fases siguientes del [análisis](ANALISIS_INGENIERIA_PROPUESTA_3.md).

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

El `.env` nunca se sube a git (está en `.gitignore`) ni entra a una imagen de Docker (está en `.dockerignore`).

## 3. Levantar, revisar y detener

| Para… | Comando | Qué debería pasar |
|---|---|---|
| Levantar todo | `docker compose up -d --build` | La primera vez tarda (descarga PyTorch y los modelos de la IA). Termina con los 3 servicios en `Started` |
| Ver el estado | `docker compose ps` | Los 3 servicios con `(healthy)` después de uno o dos minutos |
| Probar la API Java | `Invoke-RestMethod http://127.0.0.1:8008/actuator/health` | `status: UP` |
| Probar la IA | `Invoke-RestMethod http://127.0.0.1:8000/health` | `status: ok` |
| Ver los registros de un servicio | `docker compose logs -f ia` (o `api-java`, `postgres`) | Se cortan con `Ctrl+C` |
| Entrar a la base de datos | `docker compose exec postgres psql -U insightedu -d insightedu` | Se sale con `\q` |
| Detener todo | `docker compose down` | Los datos se conservan en los volúmenes |
| ⚠️ Detener y **borrar los datos** | `docker compose down -v` | Borra la base de datos y el estado de la IA. No tiene vuelta atrás |

## 4. Servicios y puertos

| Servicio | Puerto en esta máquina | Desde otros contenedores | Volumen |
|---|---|---|---|
| `postgres` | ninguno (privado) | `postgres:5432` | `postgres-datos` |
| `api-java` | `127.0.0.1:8008` | `api-java:8080` | — |
| `ia` | `127.0.0.1:8000` | `ia:8000` | `ia-preguntas`, `ia-chroma` |

Los puertos escuchan solo en `127.0.0.1`: funcionan desde esta misma máquina y no quedan abiertos a la red. Si uno está ocupado por otro programa, se cambia el número de la izquierda en `compose.yml` (por ejemplo, `127.0.0.1:8009:8080`).

## 5. Problemas comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| `postgres` no pasa a `healthy` | Falta `POSTGRES_PASSWORD` en `.env` | Completarla, y luego `docker compose down -v` y `docker compose up -d` (la base se crea con la primera contraseña) |
| `api-java` se reinicia una y otra vez | No conecta con la base | Revisar `docker compose logs api-java` |
| `port is already allocated` | Otro programa usa ese puerto | Cambiar el puerto, como en la sección 4 |
| La IA responde a todo como derivado a un mentor | Falta `GEMINI_API_KEY` | Completarla y `docker compose up -d` |
