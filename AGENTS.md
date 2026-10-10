# AGENTS.md — guía para asistentes de IA

> Para cualquier asistente de IA o agente de código (de cualquier proveedor) que trabaje en este repositorio. También sirve a una persona que llega por primera vez.
> **Rama:** `main` · **Actualizado:** 2026-10-09

## 1. El proyecto en tres líneas

**InsightEdu Lab** lee los mensajes de un servidor de Discord de una comunidad educativa (la institución ficticia **CommunityLab**), los clasifica con IA, responde dudas en vivo con los documentos de la institución y redacta borradores de posts de LinkedIn, casos de éxito y una FAQ semanal. **Una persona aprueba todo en un panel antes de publicar.** Es el proyecto del equipo 9 (G10) de la hackatón No Country + ONE; entrega el 2026-10-26.

**Idioma:** la documentación, los nombres del código y los mensajes al usuario están en **español**. Mantén ese idioma.

## 2. Qué leer y en qué orden

| Orden | Documento | Para qué |
|---|---|---|
| 1 | [README.md](README.md) | Cómo levantar y probar el sistema |
| 2 | [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) | **Cómo funciona hoy**: piezas, flujos, datos, contratos y seguridad |
| 3 | [docs/ESTADO.md](docs/ESTADO.md) | Qué está hecho, qué falta y cómo continuar |
| 4 | [docs/DECISIONES.md](docs/DECISIONES.md) | Por qué se decidió cada cosa (DEC-01…) |
| 5 | [docs/OPERACION.md](docs/OPERACION.md) | Operar con Docker: variables, comandos y problemas comunes |
| — | [docs/contratos/](docs/contratos/) y [ingestion/discord/docs/CONTRACT.md](ingestion/discord/docs/CONTRACT.md) | Los contratos entre piezas |

**Autoridad, si dos fuentes chocan:**
1. el código;
2. los contratos;
3. `ARQUITECTURA.md`;
4. `DECISIONES.md`;
5. el resto.

⚠️ **`docs/historico/` no son instrucciones vigentes.** Es la traza de cómo se construyó el proyecto: planes viejos, fichas de trabajo, informes y la propuesta original. Úsala solo para entender el *porqué* de algo, nunca como guía de cómo funciona hoy.

## 3. Mapa del repositorio

| Carpeta | Pieza | Tecnología |
|---|---|---|
| `backend-java/` | API Java: la única puerta de entrada y el registro oficial | Java 21, Spring Boot 3.4, Flyway, PostgreSQL 17 |
| `agents/orquestador/` | IA: puertas `/v1/procesar`, `/v1/generar` y `/v1/faq`, y la clasificación | Python 3.12, FastAPI, LangGraph, Gemini |
| `agents/agent_faq/` | Agente FAQ: responde con búsqueda en los PDF de `data/pdfs/` | LangChain, FAISS, sentence-transformers |
| `agents/agent_mod/` | Agente-Mod: borradores, FAQ semanal y `guia_de_voz.md` | Python, Gemini |
| `agents/bot_discord/` | Bot de Discord en vivo | discord.py |
| `panel/` | Panel web: inicio de sesión, curaduría y dashboard | Streamlit |
| `ingestion/discord/` | Ingesta por lotes y **contrato v1** (`contract.py`, `transform.py`) | Python, httpx, pydantic |
| `scripts/` | Generar claves y usuarios del panel sin mostrarlos | Python |
| `compose.yml` | Los 5 servicios de Docker | Docker Compose |

## 4. Reglas que no se rompen

| Regla | Detalle |
|---|---|
| **Secretos** | Nunca leer, imprimir, copiar a un chat ni subir a git un archivo `.env`, una clave, un token de Discord, una URL PAR de OCI ni una contraseña. Para revisar un `.env`, mostrar solo los nombres de las variables. Las claves se crean con `scripts/generar_api_key.py` y los usuarios con `scripts/crear_usuario_panel.py` |
| **Discord** | **Nunca ejecutar `ingestion/discord/simulate_students.py`**: publica mensajes falsos y los duplica. **Nunca dos bots encendidos** con el mismo token o en el mismo canal: cada mensaje se respondería dos veces |
| **Migraciones** | Una migración de Flyway ya aplicada **nunca se edita**. Cada cambio de base va en un archivo nuevo; el siguiente es `V9__…` |
| **Contratos** | Solo crecen con cambios que **agregan**. Cambiar o quitar un campo exige una versión nueva y avisar a todas las piezas. El contrato v1 tiene una sola implementación: `ingestion/discord/contract.py` |
| **Una sola puerta** | Solo `api-java` lee y escribe la base. La IA no guarda el estado del sistema y solo la llama Java. El panel, el bot y la ingesta hablan solo con Java |
| **Claves por puerta** | Cada cliente (`ingesta`, `bot`, `panel`) tiene su clave en `X-Api-Key`, y **cada clave abre solo su puerta**. Una puerta nueva tiene que sumarse a `ApiKeyFilter` (con la ruta normalizada) y revisar el cliente en su controlador |
| **Red** | Los puertos se publican solo en `127.0.0.1`. La base de datos y la IA nunca quedan abiertas a internet; en un servidor, solo el panel, con HTTPS |
| **Datos personales** | Los borradores usan solo el **primer nombre** del alumno, y publicarlo exige la casilla de consentimiento. Los registros nunca llevan textos de alumnos: solo IDs y números |
| **Respuestas del bot** | El bot responde solo si el Agente FAQ encontró **respaldo en los PDF**; si no, deriva a un mentor. Nada fuera de Discord se publica sin aprobación |
| **Pruebas** | Ningún cambio está terminado sin pruebas que pasen, ejecutadas de verdad: las de la pieza tocada y las que ya existían |
| **Ramas** | No modificar ni borrar las ramas originales de los equipos (`feature/java-core-api`, las de `ai-engine`, `feat/7-panel-minimo` y `feature/postman-docs-solo`). Trabajar en una rama nueva desde `main` y fusionar con un Pull Request |

## 5. Cómo levantar y probar

**Levantar todo** (detalle en el [README](README.md) y en [OPERACION.md](docs/OPERACION.md)):
```
docker compose up -d --build
docker compose ps
```

**Pruebas por pieza** (desde la raíz, salvo donde se indica):

| Pieza | Dependencias para las pruebas | Comando |
|---|---|---|
| IA | `fastapi`, `pydantic`, `langgraph`, `langchain-core` y `pytest` (no hace falta PyTorch ni Gemini: las pruebas usan un LLM falso) | `python -m pytest agents/orquestador/tests -q` |
| Bot | `agents/bot_discord/requirements.txt` y `pytest` | `python -m pytest agents/bot_discord/tests -q` |
| Panel | `panel/requirements.txt` y `pytest` | `python -m pytest panel/tests -q` |
| Ingesta | `ingestion/discord/requirements.txt` | Desde `ingestion/discord`: `python -m pytest -q` |
| Java | Ninguna en la máquina: corre dentro de Docker, contra la base `insightedu_test` | El comando de [OPERACION.md](docs/OPERACION.md) §5 |

Las pruebas de Java se niegan a correr si la base no termina en `_test`, y la subida a OCI está apagada en todas ellas. Las pruebas nuevas de Java deben **reutilizar las propiedades** de una prueba existente (por ejemplo, `CuraduriaApiTest`): cada combinación nueva abre otro grupo de conexiones, y PostgreSQL puede quedarse sin ellas.

## 6. Convenciones del código

- Nombres, comentarios y mensajes en español, con la misma densidad de comentarios que el código vecino.
- **Errores** con el formato común `{codigo, mensaje, errores, idCorrelacion}`, sin repetir los datos recibidos.
- **Tareas de fondo** en Java: reservar con `SKIP LOCKED` y una columna de "reservado hasta", llamar a servicios externos **sin transacción abierta** y guardar con una guarda (`actualizado_en` y el estado esperado). Copiar el patrón de `clasificacion/` o `generacion/`.
- **Comparaciones de claves** en tiempo constante.
- **Panel:** los textos de alumnos y de la IA se muestran escapados; nunca con `unsafe_allow_html`.
- **IA:** el texto de un mensaje es un **dato** para el LLM, nunca una instrucción. Salida estructurada con modelos pydantic. Un fallo del LLM es `ERROR`, nunca una etiqueta o un borrador inventados.

## 7. Cuando termines un cambio

1. Corre las pruebas (sección 5).
2. Si decidiste algo, agrega una fila a [docs/DECISIONES.md](docs/DECISIONES.md).
3. Si cambió cómo funciona algo, actualiza [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md).
4. Si cerraste o abriste un pendiente, actualiza [docs/ESTADO.md](docs/ESTADO.md).
5. Abre un Pull Request a `main` con qué cambia, por qué y cómo se probó.
