# Análisis de ingeniería — Propuesta de arquitectura 3

> **Estado:** v0.3, aprobado por Harrison (decisiones D1 a D7 validadas; objetivos agregados) · **Fecha:** 2026-10-03 · **Rama:** `feature/integracion-arquitectura-3` (commit base `02e6caf`)
> **Preparado por:** Harrison Tutalcha, con asistencia de Claude · **Entrega final del proyecto:** 2026-10-26

## Cómo leer este documento

**Para qué sirve.** El documento [Propuesta de arquitectura 3](#referencias) dice **qué** piezas hay que conectar para cumplir las necesidades N1 a N7. Este análisis dice **cómo** construirlas de forma correcta y segura, a partir del código que existe hoy en esta rama. Señala lo que la propuesta no cubre: seguridad, fallos, datos, pruebas, despliegue y organización del trabajo.

**Etiquetas de origen.** Cada afirmación dice de dónde sale:

| Etiqueta | Significa |
|---|---|
| 📘 | Documentación oficial (con enlace en [Referencias](#referencias)) |
| 💻 | Verificado en el código de esta rama (con archivo y línea) |
| 🧪 | Observado al ejecutar algo |
| 🔎 | Deducción o recomendación nuestra: hay que validarla |
| 👤 | Decisión tomada por Harrison, con su fecha |

**Prioridad de cada tarea.**

| Marca | Significa |
|---|---|
| 🔴 Imprescindible | Sin esto no hay entrega, o hay un riesgo serio |
| 🟡 Recomendable | Mejora la calidad; se hace si hay tiempo |
| ⚪ Fuera de alcance | No se hace; se documenta como limitación conocida |

**Tamaño de cada tarea** (para una persona trabajando con Claude): **S** = menos de medio día · **M** = 1 a 2 días · **L** = 3 días o más.

**Términos que aparecen** (se explican también donde se usan):

| Término | Qué significa |
|---|---|
| Puerto | El "número de puerta" por el que un programa recibe pedidos en una máquina (por ejemplo, 8080) |
| Red interna de Docker | Una red privada entre contenedores: se ven entre ellos, pero nadie de afuera los ve |
| API key | Una clave secreta que un programa manda en cada pedido para demostrar que tiene permiso |
| Upsert | "Actualizar o insertar": si el registro ya existe se actualiza; si no, se crea |
| Migración | Un archivo versionado que crea o cambia las tablas de la base de datos, siempre igual en todas las máquinas |
| Healthcheck | Una revisión automática que pregunta "¿estás vivo?" a un servicio |
| Prueba de contrato | Una prueba que verifica que dos piezas siguen hablando el mismo formato |
| CI (integración continua) | GitHub corre las pruebas solo cada vez que se sube código |
| Id de correlación | Un identificador que acompaña a un mensaje por todas las piezas, para poder seguirlo en los registros |
| Inyección de instrucciones (*prompt injection*) | Un texto que intenta engañar a la IA para que haga algo que no debe ("ignora tus reglas y…") |

---

## Objetivos

👤 Validados por Harrison el 2026-10-03. Ante cualquier duda de "¿esto sirve?", se mira aquí.

### De dónde salen

```
1. Brief del cliente  (resumen: ingestion/discord/docs/PROJECT_BRIEF.md)   QUÉ problema y qué requisitos técnicos
2. Decisiones del equipo sobre el MVP  (PROJECT_BRIEF.md §3)              QUÉ entra y qué no
3. Propuesta de arquitectura 3  (docs/referencias/, PDF)                  CON QUÉ piezas; necesidades N1 a N7
4. Este análisis                                                          CÓMO construirlo y en qué orden
5. Decisiones de Harrison  (D1 a D7 y modo de trabajo, sección 8)         CON QUÉ ritmo y reglas
```

⚠️ **Dos numeraciones "N":** en `PROJECT_BRIEF.md`, N1 a N5 son frases del brief (ahí N4 es *Community Highlights*, que quedó fuera). **En el trabajo se usan las N1 a N7 de la propuesta 3** (ahí N4 es *FAQ y bot*).

### Objetivo principal

> **Entregar el 2026-10-26 un MVP de InsightEdu Lab que funcione de punta a punta y esté desplegado. Debe convertir la actividad de un servidor de Discord en activos de marketing, respuestas a dudas y alertas sobre la comunidad, con una persona que apruebe antes de publicar. Se construye sobre la arquitectura 3, de forma segura y demostrable.**

### Objetivos específicos

Si falta tiempo, lo último que se recorta es OE1, OE3 y OE6.

| # | Objetivo específico | Necesidad | Fase (sección 9) | Estado al 2026-10-03 |
|---|---|---|---|---|
| OE1 | Capturar los mensajes de Discord **en vivo** (bot) y **por lotes** (cada hora), y guardarlos en PostgreSQL a través de la API Java, **sin duplicados** | N1 | 2 | 🟡 La ingesta está lista (34 pruebas). El modelo de datos y el upsert sin duplicados están listos (T01). Falta la puerta de lotes (T03), y el bot todavía no pasa por Java |
| OE2 | Que la IA etiquete cada mensaje con **intención, sentimiento y tema**, sin perder mensajes si falla | N2 | 3 | 🟡 Clasifica la intención (🧪 probado). Faltan el sentimiento y el tema |
| OE3 | Generar, para cada logro, un **borrador de post de LinkedIn** y un **caso de éxito** con la voz de la marca | N3 | 4 | 🔴 El Agente-Mod no existe |
| OE4 | **Responder dudas en vivo** con los PDFs de la institución, y convertir las preguntas repetidas en borradores de FAQ | N4 | 3 · 4 | 🟡 El Agente FAQ responde (🧪 probado). El bot no pasa por Java y la FAQ semanal falta |
| OE5 | Un **dashboard** con sentimiento, temas en tendencia y alertas (deserción, frustración, dudas sin responder) | N5 | 5 | 🔴 No existe |
| OE6 | Un **panel con inicio de sesión** para revisar, editar, aprobar o rechazar, con la casilla de consentimiento | N6 | 5 | 🔴 El panel solo usa datos de ejemplo |
| OE7 | Guardar en **OCI** los activos generados y los aprobados | N7 | 6 | 🟡 Java sube a OCI, pero con el error del JSON (F10) y sin una URL PAR válida |
| OE8 | Que todo **corra con un comando**, sea **seguro** (claves, puertos cerrados) y tenga **pruebas** del flujo completo | Transversal | 1 a 6 | 🟡 3 de 6 servicios en Docker; F6 y F7 resueltos |
| OE9 | **Desplegarlo y ensayar la demo** | Transversal | 6 | ⏸️ La revisión del servidor (O4) quedó pospuesta por Harrison el 2026-10-03; se retoma en la fase 6 |

### Registro de avance

| Fecha | Commit | Qué quedó hecho | Tareas del análisis |
|---|---|---|---|
| 2026-10-03 | `1fb58e2` | La IA atiende pedidos en paralelo y crea el Agente FAQ una sola vez | F6, F7 |
| 2026-10-03 | `220273f` | `docker compose` con base de datos (`postgres:17`, volumen, sin puerto publicado), API Java e IA, con healthchecks; `.env.example` unificado; guía [OPERACION.md](OPERACION.md) | O1 (3 de 6 servicios), O2, O5, S5, M2, parte de O8 |
| 2026-10-03 | `6034d64` | **T01:** modelo de datos nuevo (`lotes_recibidos`, `mensajes`, `borradores`) con Flyway y `validate`; upsert por `discord_id` que no duplica ni pisa las etiquetas; 11 pruebas con PostgreSQL real. Se quitó el modelo viejo y su puerta `/process`, que vuelve en T03 | F1, F2, F3, migraciones e índices de §5 |
| 2026-10-03 | `1e05c5b` | La IA precarga el Agente FAQ al arrancar, carga los embeddings una sola vez y no consulta internet; **se quitó ChromaDB** (solo se escribía, nunca se leía) | Arranque en frío, F12 (parte de ChromaDB) |

---

## 0. Resumen

**En una frase:** las piezas existen y valen, pero hoy **ninguna puerta tiene llave**, **varias fallan en silencio** y **el modelo de datos de backend todavía no sirve** para borradores por logro, aprobación ni dashboard. El PDF de la propuesta no lo muestra porque responde *qué conectar*, no *cómo*.

### Los 6 hallazgos más importantes

| # | Hallazgo | Por qué importa | Sección |
|---|---|---|---|
| 1 | Ninguna pieza pide identificación: API Java, IA y panel aceptan pedidos de cualquiera. Además, una URL de OCI con permiso incluido quedó en el historial público del repositorio | Cualquiera podría cargar mensajes falsos, aprobar borradores o usar el almacenamiento de OCI | [3](#3-seguridad) |
| 2 | Backend guarda **un paquete por lote** con **un solo** campo de post de LinkedIn, sin estados de aprobación | No alcanza para un borrador por cada logro (N3), ni para aprobar o rechazar (N6) | [5](#5-datos) |
| 3 | Si el modelo de IA falla (por ejemplo, se acaba el cupo), **todos** los mensajes quedan como `OTRO` (ruido) sin ningún aviso | Se pierden logros y dudas sin que nadie se entere | [4](#4-fallos-y-duplicados) |
| 4 | Como el Agente-Mod no existe, el bot le responde *"Tu consulta será revisada por un mentor"* a quien comparte un logro | Mala experiencia para el alumno en la demo | [4](#4-fallos-y-duplicados) |
| 5 | La IA atiende **un pedido a la vez** y **vuelve a cargar los modelos del Agente FAQ en cada pregunta** | Respuestas lentas; con varios alumnos a la vez, el bot deja de responder | [4](#4-fallos-y-duplicados) |
| 6 | Solo backend y la base de datos tienen Docker. IA, bot, panel e ingesta no; y la base no guarda sus datos en un volumen con nombre | No se puede desplegar todo con un comando, y hay riesgo de perder los datos | [7](#7-operación-y-despliegue) |

### Decisiones

👤 **Todas validadas por Harrison el 2026-10-03:** se adopta la opción de la columna "Decisión tomada".

| # | Decisión | Opciones | Decisión tomada 👤 | Motivo |
|---|---|---|---|---|
| D1 | ¿Seguimos trayendo los cambios nuevos de las ramas de los equipos? | (a) Base congelada: se parte de lo que hay hoy; (b) traer sus cambios cada tanto | **(a) Base congelada**, trayendo solo algo puntual si sirve | Al cambiar el código de backend e IA aquí, traer sus cambios genera conflictos en cada fusión |
| D2 | ¿Qué se guarda en OCI? | (a) Solo lo aprobado (propuesta 3); (b) todo lo generado (texto literal del brief: *"persistir todos los paquetes de activos generados"*); (c) las dos cosas en carpetas separadas | **(c)** `generados/` y `aprobados/` | Cumple la letra del brief y la intención de la propuesta. Es poco trabajo extra |
| D3 | ¿Las respuestas del bot en Discord necesitan aprobación humana? | (a) Sí, todas; (b) no, salen solas | **(b), con condiciones:** solo responde si el Agente FAQ encontró respaldo en los documentos; si no, deriva a un mentor | N6 protege lo que se publica **fuera** (LinkedIn, FAQ, casos de éxito). Si una respuesta en vivo esperara aprobación, ya no sería en vivo (N4). Hay que dejarlo escrito como excepción |
| D4 | El flujo en vivo (bot → Java → IA → Java → bot), ¿espera la respuesta o la entrega después? | (a) Espera, con tiempos máximos; (b) Java responde "recibido" y el bot consulta más tarde | **(a) Espera**, con tiempos alineados (ver F6) y el aviso "escribiendo…" en Discord | Es mucho más simple de construir y alcanza para el volumen de la demo |
| D5 | ¿Cuántos proveedores de modelos de IA usamos? | Hoy hay uno distinto por agente: Gemini para clasificar y FAQ, OpenAI para el Agente-Mod | **Uno solo** para todo | Una sola clave, una sola cuenta y un solo límite de uso que vigilar |
| D6 | ¿Cómo se registra el consentimiento del alumno antes de publicar su nombre o su cita? (pendiente P3 de la ingesta) | (a) Una casilla en el panel; (b) anonimizar siempre | **(a)** Una casilla obligatoria antes de aprobar un post o caso de éxito con nombre | Es simple y deja constancia de quién confirmó y cuándo |
| D7 | ¿Dónde se despliega? | El servidor del equipo, o una máquina gratuita de OCI | Revisar primero el servidor del equipo (memoria, disco, Docker) | Ya existe y el equipo lo probó |

---

## 1. Mapa real del sistema

Así está hoy el código de esta rama. No es el plan: es lo que existe.

| Pieza | Carpeta | Tecnología | Puerto | ¿Tiene Docker? | Estado real |
|---|---|---|---|---|---|
| API Java | `backend-java/` | Spring Boot 3.4, Java 21 | 8080 adentro; 8008 en la máquina ([compose.yml:19](../compose.yml#L19)) | Sí | Recibe lotes, edita borradores, sube a OCI y lista paquetes 💻 |
| Base de datos | `compose.yml` | PostgreSQL (`postgres:latest`) | 5432, abierto en la máquina ([compose.yml:10](../compose.yml#L10)) | Sí | Sin volumen con nombre 💻 |
| IA · orquestador | `agents/orquestador/` | FastAPI + LangGraph | 8000 ([config_http.py:14](../agents/orquestador/config_http.py#L14)) | No | Puertas `/procesar` y `/health` 💻 |
| IA · Agente FAQ | `agents/agent_faq/` | LangChain, FAISS y modelos de HuggingFace | — (lo usa el orquestador) | No | Funciona; es la pieza más avanzada 💻 |
| IA · Agente-Mod | `agents/agent_mod/` | — | — | — | **No existe**, aunque la configuración lo nombra ([config.py:55-58](../agents/orquestador/config.py#L55-L58)) 💻 |
| Bot de IA | `agents/bot_discord/` | discord.py | — (se conecta él a Discord) | No | Llama directo a la IA, sin pasar por Java ([bot_communitylab.py:23-25](../agents/bot_discord/bot_communitylab.py#L23-L25)) 💻 |
| Ingesta | `ingestion/discord/` | Python + httpx | — | No | Lista; 34 pruebas 🧪 |
| Panel | `panel/` | Streamlit | 8501 (valor por defecto de Streamlit) 🔎 | No | Lee un archivo de ejemplo ([app.py:32](../panel/app.py#L32)); el botón "Aprobar" no llama a backend ([app.py:77-91](../panel/app.py#L77-L91)) 💻 |

### Hoy y objetivo

```
HOY
  Discord ──► Bot de IA ──► IA (/procesar) ──► Bot ──► Discord      (Java no participa)
  Ingesta ──► archivo, o HTTP a Java                                  (sin probar con el Java real)
  API Java ◄── solo Postman
  Panel ──► mock_data.json                                            (sin conexión)
  IA ──► OCI (activos/ y logs/)       API Java ──► OCI (package_<id>.json)

OBJETIVO (propuesta 3)
  Discord ⇄ Bot ──► API Java ⇄ IA (privada)
  Ingesta (cada hora) ──► API Java
  Panel ──► API Java ──► PostgreSQL
  API Java ──► OCI (activos)          IA ──► OCI (solo logs, ver D2)
```

### Detalles del mapa que hay que corregir

| # | Detalle | Fuente | Qué hacer |
|---|---|---|---|
| M1 | El README de backend dice que la API usa el puerto 8000, pero `compose.yml` usa 8008. La IA usa 8000 | 💻 [README.md](../README.md), [compose.yml:19](../compose.yml#L19) | Una tabla única de puertos en el README |
| M2 | Java busca la IA en `http://localhost:8000` por defecto ([application.properties:25](../backend-java/src/main/resources/application.properties#L25)). Dentro de Docker, `localhost` es el propio contenedor de Java, no la IA | 💻 | En Docker, usar el nombre del servicio (por ejemplo, `http://ia:8000`) |
| M3 | Dos nombres para el mismo token: el bot de IA lee `DISCORD_TOKEN` ([bot_communitylab.py:16](../agents/bot_discord/bot_communitylab.py#L16)) y la ingesta `DISCORD_BOT_TOKEN` ([config.py:69](../ingestion/discord/config.py#L69)) | 💻 | Un solo nombre |
| M4 | Java sube a OCI con un enlace PAR; la IA, con el SDK de OCI y un archivo `~/.oci/config`. Son dos credenciales y dos formas de nombrar las rutas | 💻 [CommunityService.java:106](../backend-java/src/main/java/com/insightedulab/backend_java/service/CommunityService.java#L106), [oci_client.py:37](../agents/orquestador/storage/oci_client.py#L37) | Ver D2 y la sección 7 |

---

## 2. Contratos entre piezas

**Contrato** = el formato acordado en que viaja la información entre dos piezas. Si una pieza lo cambia sin avisar, la otra se rompe.

| # | Camino | Formato hoy | Problema | Propuesta 🔎 | Prioridad · tamaño |
|---|---|---|---|---|---|
| C1 | Ingesta → API Java (lotes) | La ingesta envía el contrato v1 (23 campos por mensaje). Java espera 11 campos, con `textoMensaje` obligatorio y sin el tipo de autor `BOT` | Los mensajes sin texto (una captura, por ejemplo) y los de alumnos simulados se rechazarían 💻 [InteractionInputDto.java:32-36](../backend-java/src/main/java/com/insightedulab/backend_java/dto/request/InteractionInputDto.java#L32-L36), [TipoAutor.java](../backend-java/src/main/java/com/insightedulab/backend_java/model/enums/TipoAutor.java) | Aplicar la "opción C" ya aprobada ([INGESTION_GUIDE.md §11](../ingestion/discord/docs/INGESTION_GUIDE.md)) | 🔴 · M |
| C2 | Bot → API Java (en vivo) | **No existe** | El bot va directo a la IA | El bot envía **el mismo contrato v1** con `modo: "tiempoReal"`, un mensaje por pedido. Lo ideal es reutilizar `transform.py` de la ingesta, para tener una sola implementación del contrato (cómo obtener el JSON crudo desde discord.py se verifica al construirlo) | 🔴 · M |
| C3 | API Java → IA | `NlpDataClient` tiene la conexión pero no el método que envía ([NlpDataClient.java:24-28](../backend-java/src/main/java/com/insightedulab/backend_java/client/NlpDataClient.java#L24-L28)). La IA espera el JSON crudo de Discord con 7 campos y **borra las menciones** ([adaptador.py:19](../agents/orquestador/adaptador.py#L19), [adaptador.py:32](../agents/orquestador/adaptador.py#L32)) | Formatos distintos; se pierde a quién se menciona | Agregar a la IA un adaptador que acepte el contrato v1, y que Java envíe las "cajas" (`mensajeContrato`) | 🔴 · M |
| C4 | IA → API Java (respuesta) | Devuelve la respuesta para Discord, el paquete y el log ([contratos.py:123-127](../agents/orquestador/contratos.py#L123-L127)). No devuelve sentimiento ni tema | N2 y N5 necesitan sentimiento y tema por mensaje | Agregar `etiquetas` por mensaje: `{mensajeId, intencion, confianza, sentimiento, tema, estado}` | 🔴 · S |
| C5 | Panel → API Java | Existen `GET /packages`, `PUT /curation/{id}` y la subida a OCI | No hay lista de pendientes, ni aprobar o rechazar, ni consultas del dashboard | Puertas nuevas sobre el modelo de la sección 5 | 🔴 · M |

**Reglas para todos los contratos** 🔎

| Regla | Cómo | Prioridad · tamaño |
|---|---|---|
| Una sola fuente de verdad | El contrato v1 vive en `ingestion/discord/contract.py` y en su JSON Schema ([contract_v1.schema.json](../ingestion/discord/schema/contract_v1.schema.json)). Java y la IA lo copian; no lo reinventan | 🔴 · — |
| Pruebas de contrato | Un mismo juego de mensajes de ejemplo que pasa por la ingesta, por Java y por la IA | 🔴 · S |
| Un formato de error común | `{codigo, mensaje, idCorrelacion}` en Java y en la IA | 🟡 · S |
| Id de correlación | El bot o la ingesta lo crean y viaja en la cabecera `X-Id-Correlacion` por Java y la IA, y queda en sus registros | 🟡 · S |

---

## 3. Seguridad

**Regla base 🔎:** solo una pieza queda abierta a internet (el panel, y protegido). Todo lo demás habla por la red interna de Docker y con una clave.

| # | Riesgo | Situación hoy | Propuesta 🔎 | Prioridad · tamaño |
|---|---|---|---|---|
| S1 | **API Java sin identificación**: cualquiera que llegue a la puerta puede cargar lotes, editar borradores y subir a OCI | 💻 No hay control en [CommunityController.java](../backend-java/src/main/java/com/insightedulab/backend_java/controller/CommunityController.java), y `pom.xml` no incluye Spring Security | Una **API key** por cliente (bot, ingesta, panel) en la cabecera `X-Api-Key`, revisada por un filtro de Java. JWT no hace falta: los clientes son programas, no personas | 🔴 · S |
| S2 | **IA sin identificación** y aceptando conexiones de cualquier dirección | 💻 [config_http.py:13](../agents/orquestador/config_http.py#L13), [api.py:89](../agents/orquestador/api.py#L89) | No publicar su puerto (solo red interna) + API key de Java hacia la IA | 🔴 · S |
| S3 | **Panel sin inicio de sesión**, y es la única pieza abierta a internet ([PDF §8](#referencias)) | 💻 [app.py](../panel/app.py) no pide credenciales | Contraseña para entrar (variable de entorno, nunca en el código). HTTPS si el servidor tiene dominio | 🔴 · S (contraseña) · 🟡 · S (HTTPS) |
| S4 | **URL PAR de OCI en el historial público de git** | 💻 Estuvo en `application.properties` en los commits `eacfe5b` y `bff59f5`; `0f2b407` la quitó del archivo. 🧪 El repositorio es público. 📘 *"Anyone you provide this URL to can access the Object Storage resources"*, *"Deleting a pre-authenticated request revokes user access"* y el vencimiento *"has no limits"* | Backend la elimina en la consola de OCI y crea una nueva: solo para escribir, limitada al bucket y con vencimiento cercano a la entrega. La nueva va solo en `.env`. **Estado 👤 (2026-10-03):** Harrison lo da por cerrado sin esperar a backend; es un **riesgo aceptado**. Mientras nadie la elimine, esa URL sigue funcionando. Esta rama usa siempre una PAR nueva en su `.env`, nunca la expuesta | ⚪ · riesgo aceptado |
| S5 | Base de datos y API abiertas en la máquina | 💻 [compose.yml:9-10](../compose.yml#L9-L10) (5432) y [compose.yml:18-19](../compose.yml#L18-L19) (8008) | En el servidor, la base sin puerto publicado. La API solo en la red interna si el panel corre en el mismo servidor | 🔴 · S |
| S6 | CORS abierto a cualquier sitio y con credenciales | 💻 [CorsConfig.java:18-22](../backend-java/src/main/java/com/insightedulab/backend_java/config/CorsConfig.java#L18-L22) | 🔎 Streamlit llama a Java desde el servidor, no desde el navegador, así que CORS no hace falta: cerrarlo | 🟡 · S |
| S7 | Los errores muestran detalles internos | 💻 La IA responde `"Error interno: {e}"` ([api.py:79](../agents/orquestador/api.py#L79)) | Mensaje genérico para el cliente; el detalle, solo en el registro | 🟡 · S |
| S8 | El bot podría mencionar a todo el servidor | 🔎 Si la IA escribe `@everyone`, el bot lo publica tal cual ([bot_communitylab.py:232](../agents/bot_discord/bot_communitylab.py#L232)) | Responder con las menciones desactivadas | 🔴 · S |
| S9 | Inyección de instrucciones: un alumno intenta engañar a la IA | 🔎 La respuesta del Agente FAQ se publica sin revisión (D3) | Responder solo con respaldo en los PDFs (ya existe un umbral de similitud), límite de largo y reglas en las instrucciones del sistema | 🟡 · S |
| S10 | El bot escucha **todos** los canales | 💻 `BOT_CANAL_PERMITIDO = ""` ([bot_communitylab.py:20](../agents/bot_discord/bot_communitylab.py#L20)) | Solo `#dudas` y `#logros`, con sus IDs en `.env` | 🔴 · S |
| S11 | Datos personales en los registros | 💻 El bot imprime el texto de cada mensaje ([bot_communitylab.py:197](../agents/bot_discord/bot_communitylab.py#L197)) | No registrar textos en el servidor; solo IDs | 🟡 · S |
| S12 | Consentimiento antes de publicar (D6) | 💻 No existe | Casilla obligatoria en el panel | 🔴 · S |
| S13 | Dependencias sin versión fija | 💻 [requirements.txt](../requirements.txt) no fija versiones; `postgres:latest` ([compose.yml:3](../compose.yml#L3)) | Fijar versiones exactas | 🟡 · S |
| S14 | El índice FAISS se carga con `allow_dangerous_deserialization=True` | 💻 [store.py:24](../agents/agent_faq/vectorstore/store.py#L24) | 🔎 Es aceptable porque los archivos son nuestros. Nunca cargar índices de terceros | ⚪ |
| S15 | Secretos | 💻 Todos los `.env` están en `.gitignore` y las plantillas no tienen valores reales (revisado el 2026-10-03) | Mantener una plantilla `.env.example` al día por cada pieza | 🔴 · — |

---

## 4. Fallos y duplicados

**Principio 🔎:** ningún error se traga en silencio. O se reintenta, o queda marcado para que una persona lo vea en el panel.

| # | Problema | Situación hoy | Propuesta 🔎 | Prioridad · tamaño |
|---|---|---|---|---|
| F1 | **Duplicados**: cada lote crea filas y un paquete nuevos | 💻 [CommunityService.java:37-83](../backend-java/src/main/java/com/insightedulab/backend_java/service/CommunityService.java#L37-L83); `discordId` no es único ([Interaction.java:33](../backend-java/src/main/java/com/insightedulab/backend_java/model/Interaction.java#L33)) | Upsert por `discordId`, con la columna única | 🔴 · M |
| F2 | El upsert podría **borrar las etiquetas de la IA** | 🔎 Cuando el lote de la hora vuelve a traer un mensaje (por ejemplo, con reacciones nuevas), no debe pisar la intención, el sentimiento ni el tema | El upsert actualiza solo los campos del mensaje. Si cambió el texto, se marca para volver a clasificar | 🔴 · S |
| F3 | El bot en vivo y el lote de la hora escriben el mismo mensaje a la vez | 🔎 | La columna única más un `INSERT … ON CONFLICT DO UPDATE` de PostgreSQL resuelven la carrera | 🔴 · S |
| F4 | **Errores que se convierten en "ruido"**: si el modelo falla, el mensaje queda como `OTRO` | 💻 [clasificador.py:55-60](../agents/orquestador/nodos/clasificador.py#L55-L60), [generic_adapter.py:96-102](../agents/orquestador/clasificadores/generic_adapter.py#L96-L102) | Un estado `ERROR` distinto de `OTRO`. Java guarda el mensaje como "pendiente de clasificar" y lo reintenta más tarde | 🔴 · S |
| F5 | **El bot responde mal a los logros**: el Agente-Mod no existe, todo TESTIMONIO y COMENTARIO pasa a "requiere humano", y el bot contesta *"Tu consulta fue registrada y será revisada por un mentor"* | 💻 [invocador_mod.py:47-56](../agents/orquestador/nodos/invocador_mod.py#L47-L56), [bot_communitylab.py:238-243](../agents/bot_discord/bot_communitylab.py#L238-L243) | El bot responde con texto **solo** a las dudas. A un logro, como mucho, le pone una reacción 🎉. Los borradores van al panel, no a Discord | 🔴 · S |
| F6 | **La IA atiende de a un pedido** | 💻 `async def procesar` ([api.py:43](../agents/orquestador/api.py#L43)) llama a código que bloquea ([api.py:72](../agents/orquestador/api.py#L72)). 📘 FastAPI ejecuta las funciones `def` en un grupo de hilos aparte, *"as it would block the server"*; las `async def` las llama directo | Cambiar `async def` por `def` (una línea). Mientras un mensaje espera al modelo, los demás pedidos, incluido `/health`, se siguen atendiendo | 🔴 · S |
| F7 | **El Agente FAQ se arma de nuevo en cada pregunta**: carga el modelo de IA, los embeddings, el índice FAISS y el reranker | 💻 [invocador_faq.py:26-27](../agents/orquestador/nodos/invocador_faq.py#L26-L27) → [agente_faq.py:27-62](../agents/agent_faq/agente_faq.py#L27-L62) | Crearlo **una sola vez** al arrancar, como ya se hace con el orquestador ([api.py:21-31](../agents/orquestador/api.py#L21-L31)). Lo mismo para el Agente-Mod | 🔴 · S |
| F8 | **Tiempos de espera desalineados**: bot 60 s, Java → IA 15 s | 💻 [bot_communitylab.py:91](../agents/bot_discord/bot_communitylab.py#L91), [RestClientConfig.java:24](../backend-java/src/main/java/com/insightedulab/backend_java/config/RestClientConfig.java#L24) | En una cadena, el de afuera espera más que el de adentro: modelo 20 s < Java → IA 30 s < bot → Java 40 s. Mientras tanto, el bot muestra "escribiendo…" | 🔴 · S |
| F9 | Si Java o la IA están caídos, el bot pierde la respuesta | 💻 [bot_communitylab.py:206-208](../agents/bot_discord/bot_communitylab.py#L206-L208) solo registra el error | Con la propuesta 3, Java guarda primero; si la IA falla, el mensaje queda "sin responder" y aparece en el panel (indicador "dudas sin responder" de N5). El lote de la hora recupera lo que el bot no vio | 🟡 · S |
| F10 | **El JSON que Java sube a OCI se arma a mano** | 💻 [CommunityService.java:108-119](../backend-java/src/main/java/com/insightedulab/backend_java/service/CommunityService.java#L108-L119) une textos con `String.format`. 🔎 Un post con comillas o saltos de línea (todo post de LinkedIn los tiene) genera un JSON inválido | Armar el JSON con Jackson, la librería que ya trae Spring | 🔴 · S |
| F11 | Se puede subir a OCI algo que no está aprobado | 💻 [CommunityService.java:102-138](../backend-java/src/main/java/com/insightedulab/backend_java/service/CommunityService.java#L102-L138) no revisa la aprobación | Subir a `aprobados/` solo si el estado es `APROBADO` | 🔴 · S |
| F12 | Fallos silenciosos al subir a OCI o a ChromaDB desde la IA | 💻 [consolidacion.py:149-169](../agents/orquestador/nodos/consolidacion.py#L149-L169); ChromaDB falla si llega dos veces el mismo id ([chroma_client.py:57](../agents/orquestador/storage/chroma_client.py#L57)) | Registrar el error con nivel de advertencia y usar upsert en ChromaDB | 🟡 · S |
| F13 | "No encontrado" responde con error 500 | 💻 `RuntimeException` en [CommunityService.java:89](../backend-java/src/main/java/com/insightedulab/backend_java/service/CommunityService.java#L89) | Un manejador global de errores que devuelva 404 | 🟡 · S |
| F14 | La validación de la curación no se aplica | 💻 Falta `@Valid` en [CommunityController.java:61](../backend-java/src/main/java/com/insightedulab/backend_java/controller/CommunityController.java#L61). Si se agrega tal cual, obliga a enviar todos los campos ([CurationRequestDto.java:11-23](../backend-java/src/main/java/com/insightedulab/backend_java/dto/request/CurationRequestDto.java#L11-L23)) | Se rehace junto con el modelo de borradores (sección 5) | 🔴 · — (parte de 5) |
| F15 | Límites de uso de los proveedores de IA: un lote de 39 mensajes son 39 llamadas o más, una tras otra | 🔎 Con un plan gratuito, el proveedor puede rechazar pedidos por exceso, y hoy eso cae en F4 | Reintentar con espera creciente cuando el proveedor responde "demasiados pedidos", y un tope de mensajes por lote | 🟡 · S |

---

## 5. Datos

### Situación hoy 💻

Dos tablas: `paquetes_resultados` (**una por lote**, con un post, una FAQ, tokens y estado de OCI) e `interacciones_originales` (una fila por mensaje). Ver [PackageResult.java](../backend-java/src/main/java/com/insightedulab/backend_java/model/PackageResult.java) e [Interaction.java](../backend-java/src/main/java/com/insightedulab/backend_java/model/Interaction.java).

| Necesidad | Qué exige a los datos | ¿Lo cumple hoy? |
|---|---|---|
| N1 | Un mensaje = una fila, sin duplicados | ❌ Sin columna única (F1) |
| N2 | Intención, sentimiento y tema en cada mensaje | ⚠️ Hay sentimiento; faltan intención y tema |
| N3 | Un borrador **por cada logro** (post y caso de éxito) | ❌ Un solo `postLinkedin` por lote ([PackageResult.java:44](../backend-java/src/main/java/com/insightedulab/backend_java/model/PackageResult.java#L44)) |
| N5 | Autor estable, fecha, a qué mensaje responde y reacciones | ⚠️ Faltan `respondeA` y las reacciones (van en la "caja" de la opción C) |
| N6 | Estado del borrador (pendiente, aprobado o rechazado), quién lo aprobó y cuándo | ❌ Solo existe `fueEditadoPorHumano` |
| N7 | Saber qué se subió a OCI y dónde | ⚠️ `statusOci` por lote, no por activo |

### Modelo propuesto 🔎 (para discutir)

```
lotes_recibidos          mensajes                         borradores
───────────────          ────────────────────────          ─────────────────────────────
lote_id (único)          id                                id
modo                     discord_id (ÚNICO)       ◄────    mensaje_id
version_contrato         canal_id, autor_id                tipo: POST_LINKEDIN | CASO_EXITO
recibido_en              autor_tipo, autor_rol                   | FAQ | RESPUESTA_BOT
total, nuevos,           fecha, responde_a                 texto_ia, texto_final
actualizados             texto                             estado: PENDIENTE | APROBADO
                         contrato (jsonb: la "caja")              | RECHAZADO
                         ── etiquetas de la IA ──          consentimiento_confirmado
                         intencion, confianza              aprobado_por, aprobado_en
                         sentimiento, tema                 tiempo_curaduria_seg
                         estado_clasificacion:             tokens_in, tokens_out
                           PENDIENTE | OK | ERROR          estado_oci, ruta_oci
```

| Decisión de datos | Propuesta 🔎 | Prioridad · tamaño |
|---|---|---|
| Migraciones | Pasar de `ddl-auto=update` ([application.properties:17](../backend-java/src/main/resources/application.properties#L17)) a **Flyway**: un archivo SQL versionado crea las tablas igual en todas las máquinas. `update` no borra ni renombra columnas, y lo que haya en el servidor depende del historial de arranques | 🟡 · S (conviene hacerlo junto con el modelo nuevo) |
| Índices para el dashboard | Únicos en `discord_id`; de búsqueda en `(autor_id, fecha)`, `(fecha)` e `(intencion)` | 🔴 · S |
| Volumen de la base | Un volumen con nombre en `compose.yml`. 🔎 Sin él, al recrear el contenedor los datos quedan en un volumen huérfano | 🔴 · S |
| Versión de PostgreSQL | Fijar la versión mayor (por ejemplo, `postgres:17`). 🔎 Una versión mayor nueva no lee los datos de la anterior sin migrarlos | 🔴 · S |
| Estado dentro de la IA | El historial de preguntas y FAISS viven en archivos de la IA. 🔎 Se aceptan como **copias derivadas** que se pueden reconstruir desde Java, nunca como la única copia (regla 3 de la propuesta). Llevan volumen en Docker. 👤 ChromaDB se quitó el 2026-10-03: solo se escribía y nunca se leía | 🟡 · S |
| Respaldos | Una copia diaria de la base (`pg_dump`) en OCI | 🟡 · S |
| Zonas horarias | Ya está bien: `Instant` en Java y UTC en el contrato 💻 | — |

**Las 5 consultas del dashboard (N5)** 🔎

| Indicador | Consulta, en simple |
|---|---|
| Sentimiento por semana | Contar mensajes por semana y por sentimiento |
| Temas en tendencia | Contar mensajes por semana y por tema |
| Alerta de deserción | Autores cuyo último mensaje tiene más de 14 días |
| Alerta de frustración | Autores con varios mensajes negativos seguidos |
| Dudas sin responder | Mensajes `PREGUNTA_FAQ` sin respuesta de una persona ni del bot después de N horas |

---

## 6. Calidad y pruebas

| Pieza | Pruebas hoy | Fuente |
|---|---|---|
| Ingesta | 34 pruebas automáticas (pytest) | 🧪 |
| IA | Scripts que se corren a mano y llaman a modelos reales; no son pruebas automáticas | 💻 [test_orquestador.py:149](../agents/orquestador/test_orquestador.py#L149), [test_agente.py:200](../agents/agent_faq/test_agente.py#L200) |
| API Java | Una sola prueba, que solo comprueba que la aplicación arranca (y necesita la base de datos) | 💻 [BackendJavaApplicationTests.java:9-10](../backend-java/src/test/java/com/insightedulab/backend_java/BackendJavaApplicationTests.java#L9-L10) |
| Panel | Ninguna | 💻 |

| # | Propuesta 🔎 | Prioridad · tamaño |
|---|---|---|
| Q1 | **Pruebas de contrato**: los mismos mensajes de ejemplo pasan por la ingesta, se leen en Java y los acepta la IA | 🔴 · S |
| Q2 | **Java**: pruebas del upsert (insertar, actualizar, no duplicar, no pisar etiquetas) y de los estados del borrador | 🔴 · M |
| Q3 | **IA sin gastar**: correr las pruebas con el clasificador de palabras clave que ya existe (`CLASIFICADOR_PROVIDER=keyword`, [config.py:19-20](../agents/orquestador/config.py#L19-L20)) y un modelo falso para los agentes | 🟡 · S |
| Q4 | **Prueba de punta a punta** con el caso de Camila ([PDF §7](#referencias)): enviar el lote → fila guardada → etiquetas → borrador → aprobación → OCI | 🔴 · M |
| Q5 | **Calidad de la IA**: los 39 mensajes simulados con su intención esperada, para medir cuántos acierta el clasificador y no empeorar al cambiar instrucciones o modelo | 🟡 · S |
| Q6 | **CI**: GitHub Actions corre pytest y `mvn test` en cada subida a la rama | 🟡 · S |
| Q7 | **Ensayo de la demo**: un guion de 5 minutos, probado en el servidor desplegado | 🔴 · S |

---

## 7. Operación y despliegue

### Situación hoy 💻

- `compose.yml` solo levanta PostgreSQL y la API Java.
- No hay Dockerfile para la IA, el bot, el panel ni la ingesta.
- Las dependencias de la IA ([requirements.txt](../requirements.txt)) incluyen `sentence-transformers`, `transformers`, `unstructured`, `chromadb` y `laya`. 🔎 La imagen de Docker puede pesar varios GB y necesitar bastante memoria; el PDF ya lo advierte.
- Los nombres de modelo por defecto no coinciden: `gemini-3.5-flash-lite` ([config.py:21](../agents/orquestador/config.py#L21)), `gemini-2.0-flash-exp` ([config.py:41](../agents/orquestador/config.py#L41)) y `gemini-3.1-flash-lite` ([agent_faq/config.py:17](../agents/agent_faq/config.py#L17)). 🔎 Hay que verificar cuál existe y usar uno solo (D5).

### Propuesta 🔎

```
SERVIDOR · un solo docker compose
┌───────────────────────────────────────────────────────────────────┐
│  red interna (nadie de afuera la ve)                              │
│                                                                   │
│  postgres ◄── api-java ◄──► ia                                    │
│  (volumen)       ▲    ▲                                           │
│                  │    └──── bot  (se conecta él a Discord)        │
│                  │    └──── ingesta (cada hora, con cron)         │
│                  │                                                │
│               panel ◄──────────── ÚNICO puerto abierto (con clave)│
└───────────────────────────────────────────────────────────────────┘
                 api-java ──► OCI          ia ──► OCI (logs)
```

| # | Tarea | Detalle | Prioridad · tamaño |
|---|---|---|---|
| O1 | Compose completo | Seis servicios: postgres, api-java, ia, bot, panel e ingesta. Solo el panel con puerto publicado | 🔴 · M |
| O2 | Healthchecks | `pg_isready` para la base, una puerta de salud en Java y `/health` en la IA. Cada servicio arranca cuando el anterior está sano | 🔴 · S |
| O3 | Ingesta programada | `cron` del servidor ejecuta `docker compose run --rm ingesta` cada hora | 🔴 · S |
| O4 | Revisar el servidor del equipo | Memoria, CPU, disco, versión de Docker y si tiene dominio (D7). Solo mirar, sin desplegar | 🔴 · S |
| O5 | Configuración | Un `.env` por servidor, con su plantilla `.env.example` al día y nombres unificados (M3) | 🔴 · S |
| O6 | Registros | Cambiar `print` por `logging`, con el id de correlación y sin textos de alumnos (S11). Limitar el tamaño de los registros de Docker | 🟡 · S |
| O7 | Manual de operación | Cómo arrancar, detener, ver registros, actualizar y restaurar un respaldo | 🟡 · S |
| O8 | Imagen de la IA más liviana | Separar lo que solo hace falta para construir el índice; usar la versión de PyTorch solo para CPU | 🟡 · M |
| O9 | Alta disponibilidad, varios servidores, monitoreo con alertas | Más allá del MVP | ⚪ |

---

## 8. Gestión del trabajo

### Modo de trabajo (decidido el 2026-10-03)

Harrison desarrolla el proyecto completo en esta rama, con Claude. **Las ramas de los otros equipos no se ven afectadas:**

| Pregunta | Respuesta |
|---|---|
| ¿Mis commits cambian `feature/java-core-api` o las ramas de IA? | **No.** Cada rama es una línea independiente. Los commits de esta rama solo existen aquí |
| ¿Cuándo afectaría a otros? | Solo si alguien **fusiona** esta rama en otra; por ejemplo, un pull request a `main` que se acepta |
| ¿Sus cambios nuevos llegan aquí solos? | **No.** Solo si se traen a mano con una fusión (ver D1) |

### Riesgos de organización 🔎

| Riesgo | Por qué importa | Mitigación |
|---|---|---|
| Dos versiones del producto | Si los equipos siguen por su lado, el 26 de octubre puede haber dos sistemas distintos | Avisar al equipo ahora y acordar cuál se presenta. Esta rama puede proponerse a `main` con un pull request cerca del final |
| Una sola persona para todo | 23 días para N1 a N7 más el despliegue | Seguir el orden de la sección 9 y recortar los 🟡 si hace falta |
| Cambiar código de otros equipos | Pueden no reconocer su código | Commits pequeños con mensajes claros, por si después quieren tomar algo |

### Cómo se trabaja cada tarea 🔎

1. Se elige la siguiente tarea de la sección 9.
2. Claude escribe el código y las pruebas; Harrison los revisa y los ejecuta.
3. **Terminado** significa: las pruebas pasan, corre con `docker compose`, la documentación está al día y hay un commit con un mensaje claro (`feat(...)`, `fix(...)`, `docs(...)`).

---

## 9. Prioridades y orden

Del 2026-10-03 al 2026-10-26 hay **23 días**. Se reservan los últimos 3 para desplegar, ensayar y corregir.

| Fase | Días | Tareas | Necesidad | Prioridad |
|---|---|---|---|---|
| 0 · Urgente | Hoy | S4: cerrado como riesgo aceptado (ver S4) | — | ⚪ |
| 1 · Base que corre | 1–3 | F6 y F7 (IA atiende varios pedidos y no recarga modelos) · O4 (revisar el servidor) · O1, O2 y O5 (compose completo, sin puertos de más) · S13 (versiones fijas) | — | 🔴 / 🟡 |
| 2 · Datos y captura | 4–7 | Modelo de la sección 5 + Flyway · C1 (opción C) · F1 a F3 (upsert) · S1 (API key) · prueba real de `send_batch.py` · Q1 y Q2 | N1 | 🔴 |
| 3 · Clasificar y responder | 8–11 | C3 y C4 (IA acepta el contrato y devuelve intención, sentimiento y tema) · F4 (`ERROR` ≠ `OTRO`) · C2 (bot → Java) · F5, F8, S8 y S10 (bot correcto) · S2 | N2 · N4 | 🔴 |
| 4 · Generar contenido | 12–15 | Agente-Mod (post de LinkedIn y caso de éxito, con guía de voz) · borradores por mensaje · versión mínima de la FAQ dinámica (borrador semanal con las preguntas repetidas) | N3 · N4 | 🔴 |
| 5 · Panel y dashboard | 16–19 | C5 · S3 (inicio de sesión) · S12 (consentimiento) · aprobar o rechazar · 5 consultas y gráficos | N5 · N6 | 🔴 |
| 6 · OCI y despliegue | 20–23 | F10 y F11 (OCI correcto) · D2 · O3 · Q4 y Q7 (punta a punta y ensayo) | N7 | 🔴 |
| Si hay tiempo | — | Q3, Q5, Q6, O6 a O8, S6, S7, S9, S11, F9, F12, F13, F15 y respaldos | — | 🟡 |
| Fuera | — | JWT y roles, HTTPS sin dominio, hilos y foros, X y newsletters, Community Highlights, alta disponibilidad, anonimización completa | — | ⚪ |

---

## Referencias

| Documento | Dónde |
|---|---|
| Propuesta de arquitectura 3 (PDF, 2026-10-02) | [docs/referencias/Propuesta_3_Arquitectura_InsightEdu.pdf](referencias/Propuesta_3_Arquitectura_InsightEdu.pdf) |
| Operación con Docker | [docs/OPERACION.md](OPERACION.md) |
| Brief y alcance del MVP | [ingestion/discord/docs/PROJECT_BRIEF.md](../ingestion/discord/docs/PROJECT_BRIEF.md), [SCOPE.md](../ingestion/discord/docs/SCOPE.md) |
| Contrato de ingesta v1 | [ingestion/discord/docs/CONTRACT.md](../ingestion/discord/docs/CONTRACT.md) |
| Opción C y comparación con backend | [ingestion/discord/docs/INGESTION_GUIDE.md](../ingestion/discord/docs/INGESTION_GUIDE.md) |
| 📘 OCI · Pre-Authenticated Requests | https://docs.oracle.com/en-us/iaas/Content/Object/Tasks/usingpreauthenticatedrequests.htm |
| 📘 FastAPI · Concurrency and async / await | https://fastapi.tiangolo.com/async/ |
