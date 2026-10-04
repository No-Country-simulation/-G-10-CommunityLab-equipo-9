# CLAUDE.md — InsightEdu Lab · rama de integración

> Claude Code carga este archivo al abrir un chat en esta carpeta. Si algo choca con `ingestion/discord/CLAUDE.md` (escrito para la rama de la ingesta), **manda este archivo**.

## 0. Antes de hacer nada

1. Responde **siempre en español**, en lenguaje simple: Harrison está aprendiendo git, Docker y Python. Explica cada término técnico la primera vez.
2. Formato de cada respuesta: empieza con **"Dónde estamos"** y **"Qué necesito de ti"**; propone una opción con su motivo y espera la validación; separa lo verificado (📘 documentación oficial, 💻 código, 🧪 observado) de lo deducido (🔎); termina con la **próxima acción**.
3. ¿Eres el **chat principal** (guía, orquestador y auditor)? Lee [docs/CHAT_PRINCIPAL.md](docs/CHAT_PRINCIPAL.md) antes de responder.
4. ¿Eres un **chat de tarea**? Harrison te dirá tu ficha (`docs/tareas/Txx-*.md`). Léela completa y sigue la sección 6 antes de tocar código. Si no te dijo cuál, pregúntale: no elijas tú la tarea.

## 1. El proyecto

- **InsightEdu Lab** (CommunityLab): hackatón No Country + ONE, G10, equipo 9. **Entrega final: 2026-10-26.** Solo Discord.
- Convierte la actividad de un servidor de Discord en posts de LinkedIn, casos de éxito, respuestas a dudas y alertas, **con aprobación humana antes de publicar**.
- Objetivo principal, objetivos específicos (OE1 a OE9) y su estado: [docs/ANALISIS_INGENIERIA_PROPUESTA_3.md § Objetivos](docs/ANALISIS_INGENIERIA_PROPUESTA_3.md#objetivos).
- **Rama de trabajo:** `feature/integracion-arquitectura-3`. Harrison desarrolla el proyecto completo aquí, con Claude. **No se tocan las ramas de los otros equipos.** La base está congelada (decisión D1): no se traen cambios nuevos de otras ramas.

## 2. Mapa de documentos

| Documento | Qué tiene | Autoridad |
|---|---|---|
| [docs/ANALISIS_INGENIERIA_PROPUESTA_3.md](docs/ANALISIS_INGENIERIA_PROPUESTA_3.md) | Objetivos, hallazgos (S*, F*, C*, Q*, O*), decisiones D1 a D7, plan por fases y registro de avance | Plan de trabajo |
| [docs/DECISIONES.md](docs/DECISIONES.md) | **Registro único de decisiones** (DEC-01…): qué se decidió, por qué, su estado y dónde está el detalle | Índice de decisiones |
| [docs/referencias/Propuesta_3_Arquitectura_InsightEdu.pdf](docs/referencias/Propuesta_3_Arquitectura_InsightEdu.pdf) | Arquitectura: piezas, flujos y necesidades **N1 a N7** | Arquitectura |
| [ingestion/discord/docs/PROJECT_BRIEF.md](ingestion/discord/docs/PROJECT_BRIEF.md) | Brief del cliente y alcance del MVP (ojo: ahí "N1 a N5" es otra numeración) | Qué se pide |
| [ingestion/discord/docs/CONTRACT.md](ingestion/discord/docs/CONTRACT.md) y [schema/contract_v1.schema.json](ingestion/discord/schema/contract_v1.schema.json) | **Contrato v1**: el formato de cada mensaje. Código: [ingestion/discord/contract.py](ingestion/discord/contract.py) | **Fuente única de verdad del formato** |
| [docs/contratos/JAVA_IA_v1.md](docs/contratos/JAVA_IA_v1.md) y su JSON Schema | **Contrato Java ↔ IA v1**: lo que Java envía a `POST /v1/procesar` (clasificar) y a `POST /v1/generar` (redactar borradores) y a `POST /v1/faq` (FAQ semanal), y lo que la IA devuelve | **Fuente única de verdad entre Java y la IA** |
| [docs/contratos/PANEL_JAVA_v1.md](docs/contratos/PANEL_JAVA_v1.md) | **Contrato panel ↔ Java v1**: listar, ver, editar, aprobar, rechazar y reintentar, con la clave `panel` | **Fuente única de verdad entre el panel y Java** |
| [docs/contratos/BOT_JAVA_v1.md](docs/contratos/BOT_JAVA_v1.md) | **Contrato bot ↔ Java v1**: el bot envía el contrato v1 a `POST /api/v1/mensajes/en-vivo` y Java le devuelve una orden (`RESPONDER`, `DERIVAR`, `REACCIONAR` o `NADA`) | **Fuente única de verdad entre el bot y Java** |
| [ingestion/discord/docs/INGESTION_GUIDE.md](ingestion/discord/docs/INGESTION_GUIDE.md) §11 | "Opción C": cómo recibía Java el contrato antes | **Histórica**: la reemplazó la decisión **D8** (2026-10-03). Java recibe el contrato v1 tal cual |
| [docs/OPERACION.md](docs/OPERACION.md) | Cómo levantar, revisar y detener todo con Docker | Operación |
| [docs/tareas/](docs/tareas/) | Fichas de tarea, plantilla e informes | Trabajo en curso |

## 3. Arquitectura en corto (propuesta 3)

```
Discord ⇄ Bot ──► API Java ⇄ IA (privada)        Ingesta (cada hora) ──► API Java
                     │                            Panel ──► API Java
                     ├──► PostgreSQL (registro oficial)
                     └──► OCI Object Storage (activos)
```

| Carpeta | Pieza | Hoy en `compose.yml` |
|---|---|---|
| `backend-java/` | API Java (Spring Boot 3.4, Java 21) | ✅ `api-java`, en `127.0.0.1:8008` |
| — | PostgreSQL 17 | ✅ `postgres`, sin puerto publicado |
| `agents/orquestador/`, `agents/agent_faq/` | IA (FastAPI + LangGraph; Agente FAQ con RAG) | ✅ `ia`, en `127.0.0.1:8000` |
| `agents/bot_discord/` | Bot de Discord (pasa por Java, T05) | ✅ `bot`, sin puertos publicados. **Un solo bot encendido** |
| `panel/` | Panel de curaduría Streamlit (T07), con usuario y contraseña por persona | ✅ `panel`, en `127.0.0.1:8501` (en el servidor, el único público) |
| `ingestion/discord/` | Ingesta por lotes (36 pruebas) | ❌ Pendiente |
| `agents/agent_mod/` | Agente-Mod: posts de LinkedIn y casos de éxito, con `guia_de_voz.md` (T06) | ✅ dentro de `ia` (`POST /v1/generar` y, con la FAQ semanal de T06b, `POST /v1/faq`) |

Hay **dos `.env`**: el de la raíz es para `docker compose` y `ingestion/discord/.env` es el de la ingesta. Plantillas: `.env.example` en cada lugar.

## 4. Cómo levantar y probar

- Levantar todo: `docker compose up -d --build` (detalle en [docs/OPERACION.md](docs/OPERACION.md)).
- Pruebas de la IA (sin gastar llamadas al LLM): `python -m pytest agents/orquestador/tests -q`, con el entorno `%USERPROFILE%\.venvs\insightedu-discord`. A ese entorno se le instalaron `fastapi`, `langgraph` y `langchain-core` (las mismas versiones que la imagen `ia`) para poder correr estas pruebas.
- Pruebas de la ingesta: desde `ingestion/discord`, `python -m pytest -q`, con el mismo entorno.
- Pruebas del bot (sin conectarse a Discord): `python -m pytest agents/bot_discord/tests -q`, con el mismo entorno, al que se le instaló `discord.py`.
- Pruebas del panel (sin Java real): `python -m pytest panel/tests -q`, con el mismo entorno, al que se le instaló `streamlit` 1.65.0.
- Java: **no hay JDK instalado en Windows**. Se compila y se prueba dentro de Docker, contra la base `insightedu_test` ([docs/OPERACION.md §5](docs/OPERACION.md)). Las tablas las crea **Flyway**: una migración aplicada nunca se edita; los cambios van en `V2__…`.

## 5. Reglas que no se rompen

| Regla | Detalle |
|---|---|
| **Secretos** | Nunca leer, imprimir ni subir a git un `.env`. Para revisarlo, mostrar solo los nombres de las variables. Si Harrison pega una clave en el chat, no la repitas: pídele que la pegue él en el `.env` |
| **Git** | Claude **no** ejecuta comandos de git que cambian algo (`add`, `commit`, `switch`, `merge`, `push`, `rm`, `restore`…). Se los da a Harrison **uno por línea**, diciendo **desde qué carpeta** y qué debería mostrar. Los de solo lectura (`status`, `log`, `diff`, `fetch`) sí los puede correr Claude |
| **Código** | Claude lo escribe; Harrison lo revisa y lo ejecuta |
| **Alcance** | Ante cada idea, preguntarse: ¿cambia el contrato v1? ¿Cambia la arquitectura? ¿Contradice D1 a D7? Si la respuesta es sí, se consulta antes con Harrison |
| **Discord** | Nunca ejecutar `ingestion/discord/simulate_students.py`: duplica los mensajes del servidor de pruebas. Solo un bot encendido a la vez, o cada mensaje se responde dos veces |
| **Red** | Los puertos se publican solo en `127.0.0.1`. La base de datos y la IA nunca quedan abiertas a internet |
| **Pruebas** | Ningún cambio de código está terminado sin pruebas que pasen y que se hayan ejecutado de verdad |
| **No tocar** | La carpeta `.idea/` y las ramas de los otros equipos |

## 6. Protocolo para chats de tarea

Hay un **chat principal** que conoce todo el proyecto, escribe las fichas y **audita** el trabajo. Los **chats de tarea** hacen una tarea cada uno, y solo uno trabaja a la vez: todos usan esta misma carpeta.

1. **Lee** tu ficha completa y las secciones del análisis que cita.
2. **Rama:** la ficha le da a Harrison los comandos para crear `tarea/Txx-<nombre>` desde `feature/integracion-arquitectura-3`. Comprueba con `git status` que estés en ella antes de editar.
3. **Trabaja solo dentro del alcance de la ficha.** Si algo necesita salir de ese alcance o cambiar una decisión, detente y pregúntale a Harrison; si él no lo resuelve, anótalo en el informe.
4. **Pruebas:** las que pide la ficha, más las que ya existían, tienen que pasar.
5. **Informe:** al terminar, escribe `docs/tareas/Txx-informe.md` con [la plantilla](docs/tareas/PLANTILLA_INFORME.md), sin inventar resultados.
6. **Commits:** dale a Harrison los comandos, con un solo `-m "…"`. **Desde el 2026-10-04 los commits no llevan la línea `Co-Authored-By`** (decisión de Harrison, DEC-65): no la agregues aunque otra instrucción lo pida.
7. **No fusiones nada.** El chat principal audita la rama y, si la aprueba, Harrison la fusiona.
