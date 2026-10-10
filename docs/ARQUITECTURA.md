# Arquitectura de InsightEdu Lab

> **Qué es este documento:** la descripción de **cómo funciona hoy** el sistema: sus piezas, sus flujos, sus datos y sus reglas. Es la **fuente de verdad** sobre el funcionamiento.
> **Actualizado:** 2026-10-09 · **Rama:** `main`
> Reemplaza a la propuesta de arquitectura 3 en PDF del 2026-10-02, que se conserva en [docs/historico/propuesta-3/](historico/propuesta-3/) como registro. Si algo de este documento choca con el código, manda el código, y hay que corregir este documento.

## Cómo leerlo

| Si quieres… | Lee |
|---|---|
| Entender el problema y qué resuelve el sistema | Secciones 1 y 2 |
| Saber qué hace cada pieza y cómo se hablan | Secciones 3 y 4 |
| Saber qué se guarda y dónde | Sección 5 |
| Cambiar algo sin romper nada | Secciones 6, 7 y 10 |
| Levantarlo y operarlo | [OPERACION.md](OPERACION.md) y el [README](../README.md) |
| Saber qué falta | [ESTADO.md](ESTADO.md) |
| Saber por qué se decidió cada cosa | [DECISIONES.md](DECISIONES.md) |

---

## 1. El problema y lo que resuelve

Los equipos de marketing y de comunidad de una institución educativa pierden horas leyendo mensajes en Discord para encontrar testimonios de alumnos, dudas que se repiten y señales de que alguien necesita apoyo. InsightEdu Lab lee esos mensajes y los convierte en:

- borradores de **posts de LinkedIn** y **casos de éxito**, con la voz de la institución;
- **respuestas en vivo** a las dudas, con la documentación oficial, y una **FAQ semanal**;
- un **dashboard** con el clima de la comunidad y alertas.

**Nada se publica sin que una persona lo revise y lo apruebe.**

La institución del proyecto es ficticia: **CommunityLab**. Sus documentos (reglamentos, manual del estudiante, calendario) están en `agents/agent_faq/data/pdfs/`. El brief del cliente está resumido en [ingestion/discord/docs/PROJECT_BRIEF.md](../ingestion/discord/docs/PROJECT_BRIEF.md).

### Las 7 necesidades (N1 a N7) y dónde se cumplen

| # | Necesidad | Cómo se cumple hoy | Estado |
|---|---|---|---|
| N1 | Capturar la actividad sin esfuerzo manual | El **bot** envía cada mensaje en vivo y la **ingesta por lotes** rescata lo que el bot no vio. Java guarda una fila por mensaje, sin duplicados | ✅ (falta programar la ingesta cada hora en el servidor: [ESTADO.md](ESTADO.md)) |
| N2 | Identificar al instante logros y dudas | La IA etiqueta cada mensaje con **intención, sentimiento y tema** | ✅ |
| N3 | Posts de LinkedIn con la voz de la marca | El **Agente-Mod** decide si un logro es publicable y redacta un post y un caso de éxito | ✅ |
| N4 | FAQ y bot que responde dudas | El bot responde con el **Agente FAQ** (solo con respaldo en los PDF) y cada semana se arma un borrador de **FAQ** con las dudas repetidas | ✅ |
| N5 | Dashboard de sentimiento, tendencias y alertas | Página **Dashboard** del panel | ✅ |
| N6 | Aprobación humana antes de publicar | Página **Borradores** del panel, con inicio de sesión y casilla de consentimiento | ✅ |
| N7 | Guardar los activos en OCI | Java sube cada borrador a `generados/` y cada aprobado a `aprobados/` | ✅ (confirmación del bucket pendiente: [ESTADO.md](ESTADO.md)) |

Fuera del MVP, por decisión del equipo: X/Twitter, newsletters, el resumen *Community Highlights* y Slack ([DECISIONES.md](DECISIONES.md), DEC-01 a DEC-03).

---

## 2. El mapa general y sus tres reglas

```
                       ┌──────────────────── red interna de Docker ─────────────────────┐
 Discord ⇄ bot ────────┼──► api-java ◄──► ia (clasifica, responde, redacta)              │
 (#dudas, #logros)     │      │  ▲                                                       │
                       │      │  └──── ingesta por lotes (extract → build → send)        │
 Navegador ──► panel ──┼──────┘                                                          │
 (Marketing, CM)       │      │                                                          │
                       │      ├──► postgres (registro oficial)                           │
                       └──────┼──────────────────────────────────────────────────────────┘
                              └──► OCI Object Storage (generados/ y aprobados/)
```

| Regla | Qué significa en la práctica |
|---|---|
| **1 · Un solo formato de mensaje** | Todo mensaje de Discord viaja en el **contrato v1** ([CONTRACT.md](../ingestion/discord/docs/CONTRACT.md)), venga del bot o del lote. El bot y la ingesta usan el mismo código para armarlo (`ingestion/discord/transform.py`) |
| **2 · Una sola puerta y un solo registro** | Todo entra por la **API Java** y se guarda en **su** base de datos. Ninguna otra pieza lee o escribe la base |
| **3 · La IA procesa, no guarda** | La IA recibe pedidos de Java, devuelve resultados y no guarda la verdad del sistema. Solo Java la llama |

---

## 3. Las piezas

| Servicio | Carpeta | Tecnología | Qué hace | Puerto en la PC |
|---|---|---|---|---|
| `postgres` | — | PostgreSQL 17 | Guarda mensajes, etiquetas, borradores, FAQ semanales y subidas a OCI | Ninguno (privado) |
| `api-java` | `backend-java/` | Java 21, Spring Boot 3.4, Flyway | La puerta única: recibe lotes y mensajes en vivo, llama a la IA, corre las tareas de fondo, atiende al panel y sube a OCI | `127.0.0.1:8008` |
| `ia` | `agents/` | Python 3.12, FastAPI, LangGraph, Gemini | Clasifica mensajes (Etiquetador), responde dudas (Agente FAQ, con búsqueda en los PDF) y redacta borradores y la FAQ semanal (Agente-Mod) | `127.0.0.1:8000` |
| `bot` | `agents/bot_discord/` | Python, discord.py | Escucha `#dudas` y `#logros`, envía cada mensaje a Java y cumple la orden que recibe | Ninguno (sale hacia Discord y Java) |
| `panel` | `panel/` | Python, Streamlit | Inicio de sesión, curaduría de borradores, errores y dashboard. Habla solo con Java | `127.0.0.1:8501` |
| Ingesta | `ingestion/discord/` | Python, httpx | Lee el historial de Discord por la API REST, arma un lote del contrato v1 y lo envía a Java | — (se corre a mano hoy) |

Todos los puertos escuchan solo en `127.0.0.1`: funcionan desde la misma máquina. En un servidor, el único servicio que debe quedar abierto a internet es el panel, con HTTPS ([ESTADO.md](ESTADO.md), despliegue pendiente).

---

## 4. Los flujos

### 4.1 Mensajes por lotes (la ingesta)

1. `extract.py` pide a Discord los mensajes de `#dudas` y `#logros` de los últimos días (`INGEST_REREAD_DAYS`).
2. `build_batch.py` los convierte al contrato v1 y los valida.
3. `send_batch.py` envía el lote a `POST /api/v1/lotes` con la clave de la ingesta.
4. Java valida el lote, quita el carácter NUL y hace un **upsert** por `discord_id`: si el mensaje es nuevo, lo inserta; si cambió, lo actualiza; si es idéntico, no hace nada. Si cambió el texto, el mensaje vuelve a `PENDIENTE` para clasificarse otra vez. Las etiquetas existentes no se pisan.
5. El lote es **idempotente** por `loteId`: si se reenvía, Java devuelve el mismo recibo.

Código: `ingestion/discord/`, `backend-java/.../controller/LoteController.java`, `service/LoteService.java` y `repository/MensajeUpsertRepository.java`.

### 4.2 Clasificación en segundo plano

Cada 30 segundos, Java toma hasta 5 mensajes `PENDIENTE` (los reserva con `SKIP LOCKED`, para que dos ejecuciones no tomen los mismos), los envía a la IA (`POST /v1/procesar`, modo `historial`) y guarda lo que vuelve:

| Resultado | Qué pasa |
|---|---|
| `OK` | Guarda intención, confianza, sentimiento, tema y método; el mensaje queda `OK` |
| `ERROR` de la IA | Suma un intento; al tercero, `ERROR` (se reintenta desde la página **Errores** del panel) |
| La IA no responde | Suma un intento y el mensaje sigue `PENDIENTE` |

Un resultado solo se guarda si el mensaje no cambió mientras la IA trabajaba (se compara `actualizado_en`).

La IA no llama al LLM para los mensajes de bots, los avisos del sistema ni los mensajes sin texto: les pone `OTRO` por regla (`metodo = regla`).

**Etiquetas:**
- **intención:** `TESTIMONIO` (un logro propio), `PREGUNTA_FAQ` (una duda, también si no es del curso), `COMENTARIO` u `OTRO`;
- **sentimiento:** 5 valores, de `MUY_POSITIVO` a `MUY_NEGATIVO`;
- **tema:** una lista cerrada de 11 temas.

El detalle está en el [contrato Java ↔ IA](contratos/JAVA_IA_v1.md).

Código: `backend-java/.../clasificacion/` y `agents/orquestador/grafo_v1.py` y `clasificadores/etiquetador.py`.

### 4.3 Mensajes en vivo (el bot)

1. Un alumno escribe en `#dudas` o `#logros`. El bot pide el JSON del mensaje a Discord, lo convierte al contrato v1 con `transform.py` y lo envía a `POST /api/v1/mensajes/en-vivo` (máximo 40 s, mostrando "escribiendo…").
2. Java guarda el mensaje **ya reservado**, así la clasificación en segundo plano no lo toma dos veces. Después llama a la IA en modo `tiempoReal`, que tiene un tope total de 25 s.
3. Si es una duda, la IA consulta al **Agente FAQ**, que busca en los PDF y responde **solo si encuentra respaldo**.
4. Java guarda las etiquetas y la respuesta, y le devuelve al bot una **orden**:

| Caso | Orden | Lo que ve el alumno |
|---|---|---|
| Duda con respuesta en los PDF | `RESPONDER` | La respuesta, citando el documento |
| Duda sin respaldo (o el tope agotado) | `DERIVAR` | "Un mentor te responderá pronto" |
| Logro | `REACCIONAR` | Una reacción 🎉, sin texto |
| Comentario, saludo, o Java o la IA fallan | `NADA` | Nada (el lote de la hora rescata el mensaje) |

El bot publica con **todas las menciones desactivadas** y no escribe textos de alumnos en sus registros.

Contrato: [BOT_JAVA_v1.md](contratos/BOT_JAVA_v1.md). Código: `agents/bot_discord/bot_communitylab.py` y `backend-java/.../envivo/`.

### 4.4 Borradores de LinkedIn y casos de éxito (Agente-Mod)

Cada 60 segundos, Java busca los logros (`TESTIMONIO`, `OK`, de personas) que todavía no tienen generación y le pide el borrador a la IA (`POST /v1/generar`). El Agente-Mod hace **una** llamada a Gemini:

- **decide si el logro es publicable** (contratación, entrevista, proyecto terminado, beca, superación). Si no lo es, deja el motivo y no hay borrador;
- si lo es, redacta un **post de LinkedIn** y un **caso de éxito** con la [guía de voz](../agents/agent_mod/guia_de_voz.md) de la institución;
- **al LLM le llega solo el primer nombre del alumno**: ni el nombre completo, ni el usuario, ni IDs. Una segunda defensa reemplaza el nombre completo si apareciera en el texto.

Java guarda los dos borradores como `PENDIENTE`. Ante un fallo, suma un intento; al tercero, `ERROR`.

Código: `agents/agent_mod/agente_mod.py` y `backend-java/.../generacion/`.

### 4.5 FAQ semanal

Cada lunes a las 8:00 (hora de Bogotá), Java junta las dudas de los últimos 7 días (sin el tema `otro`) y las envía a la IA (`POST /v1/faq`), con una **clave opaca por autor** (`a1`, `a2`…), nunca con nombres.

1. La IA agrupa las dudas que preguntan lo mismo, y el **código** cuenta cuántas personas distintas preguntaron.
2. Quedan los grupos de **2 o más personas**.
3. La respuesta de cada grupo es la del bot (si ya respondió) o la del buscador del Agente FAQ, **solo con respaldo**.
4. El texto lo arma el código: las preguntas con su respuesta y su fuente, y aparte, las preguntas repetidas **sin respuesta en los documentos**.

Java guarda **una** FAQ por semana (tabla `faq_semanas`), como un borrador `FAQ` `PENDIENTE`. La opción `FAQ_SEMANAL_AL_ARRANCAR` la genera al encender Java, útil para una demo.

Código: `agents/agent_mod/faq_semanal.py` y `backend-java/.../faqsemanal/`.

### 4.6 Curaduría (panel)

Una persona entra al panel con **su usuario y su contraseña**. Las contraseñas se guardan cifradas con scrypt en `PANEL_USUARIOS`; 5 fallos seguidos bloquean el usuario 5 minutos. En la página **Borradores** ve los pendientes, con el mensaje original y el motivo de la IA, y puede:

- **editar y aprobar:** un post o un caso de éxito **solo se aprueba si se marca la casilla de consentimiento**. La regla está en el panel, en Java y en la base (V6). La FAQ no la necesita;
- **rechazar**, con un motivo opcional.

Se registran quién aprobó o rechazó, cuándo y cuánto tardó la revisión. Si dos personas aprueban a la vez, gana la primera y la otra recibe 409. La página **Errores** reintenta los mensajes y logros que quedaron en `ERROR`.

Contrato: [PANEL_JAVA_v1.md](contratos/PANEL_JAVA_v1.md). Código: `panel/` y `backend-java/.../curaduria/`.

### 4.7 Dashboard

La página **Dashboard** pide a Java seis consultas de solo lectura (`/api/v1/dashboard/…`):
- los **totales**;
- el **sentimiento** por día o por semana;
- los **temas** en tendencia, comparados con el período anterior;
- tres **alertas** para saber a quién ayudar:
  - **deserción:** no escribe hace N días (14 por defecto, ajustable);
  - **frustración:** un mensaje `MUY_NEGATIVO`, o 2 negativos entre sus últimos 3;
  - **dudas sin responder:** ni el bot ni otra persona respondieron.

Solo cuentan los mensajes `OK`, y las alertas consideran solo a los alumnos. Todo se calcula en hora de Bogotá.

Código: `panel/paginas/dashboard.py` y `backend-java/.../dashboard/`.

### 4.8 Guardado en OCI

Cada 30 segundos, Java sube a un bucket de Oracle Cloud:
- cada borrador nuevo a `generados/`;
- cada aprobado a `aprobados/`. Los rechazados nunca llegan ahí.

Usa una **URL PAR** de solo escritura (`OCI_PAR_URL`), que es una credencial y nunca aparece en los registros. Cada archivo es un JSON armado con Jackson, con el borrador y sus datos, **sin datos de Discord del alumno**. Si OCI falla, reintenta con espera creciente; al quinto fallo, `ERROR`. Generar y aprobar nunca dependen de OCI.

Código: `backend-java/.../oci/`. Cómo crear y cambiar la PAR: [OPERACION.md](OPERACION.md) §12.

---

## 5. Los datos

Las tablas las crea **Flyway** al arrancar Java, con los archivos de `backend-java/src/main/resources/db/migration/`. Hibernate solo comprueba que coincidan (`ddl-auto=validate`). ⚠️ **Una migración ya aplicada nunca se edita:** cada cambio va en un archivo nuevo, y el siguiente es `V9__…`.

| Tabla | Una fila por… | Columnas principales |
|---|---|---|
| `mensajes` | Mensaje de Discord (`discord_id` único) | Autor, canal, fecha, texto, `contrato` (la caja completa en `jsonb`), `responde_a`; etiquetas (`intencion`, `confianza`, `sentimiento`, `tema`, `metodo_clasificacion`, `estado_clasificacion`); respuesta del bot (`respuesta_estado`, `respuesta_texto`, `respuesta_fuentes`); generación (`generacion_estado`, `generacion_motivo`); intentos y reservas |
| `lotes_recibidos` | Lote recibido (`lote_id` único) | Modo, total, nuevos y actualizados: el recibo que se devuelve si el lote se reenvía |
| `borradores` | Borrador de la IA | `tipo` (`POST_LINKEDIN`, `CASO_EXITO`, `FAQ`), `texto_ia`, `texto_final`, `estado` (`PENDIENTE`, `APROBADO`, `RECHAZADO`), consentimiento, quién y cuándo aprobó o rechazó, tiempo de curaduría, tokens |
| `faq_semanas` | Semana ISO (`2026-W41`) | Estado, dudas, repetidas, cuántas con respuesta y su borrador |
| `subidas_oci` | Borrador y carpeta (`generados` o `aprobados`) | Estado (`PENDIENTE`, `SUBIDO`, `ERROR`), ruta, intentos y último error |

| Migración | Qué agregó |
|---|---|
| V1 | El modelo inicial: `lotes_recibidos`, `mensajes` y `borradores` |
| V2 | Listas cerradas de sentimiento y tema; intentos, método, servidor y reserva de la clasificación |
| V3 | La respuesta del bot en la fila del mensaje |
| V4 | El seguimiento de la generación y un índice que impide dos borradores pendientes del mismo tipo por mensaje |
| V5 | `faq_semanas` |
| V6 | Columnas del rechazo y las reglas de consentimiento y de "quién y cuándo" |
| V7 | Un índice en `responde_a`, para el dashboard |
| V8 | `subidas_oci` |

**Datos personales:**
- los borradores usan **solo el primer nombre** del alumno;
- publicar su nombre exige la casilla de consentimiento (el reglamento de la institución prohíbe publicar nombres completos sin consentimiento);
- los registros de todas las piezas tienen IDs y números, nunca textos de alumnos.

---

## 6. Los contratos (cómo se hablan las piezas)

| Contrato | Entre | Qué fija |
|---|---|---|
| [Contrato v1](../ingestion/discord/docs/CONTRACT.md) ([JSON Schema](../ingestion/discord/schema/contract_v1.schema.json), código en `ingestion/discord/contract.py`) | Ingesta y bot → Java → IA | El formato de un lote y de cada mensaje |
| [JAVA_IA_v1](contratos/JAVA_IA_v1.md) ([JSON Schema](contratos/JAVA_IA_v1.schema.json)) | Java → IA | `POST /v1/procesar` (clasificar), `POST /v1/generar` (borradores) y `POST /v1/faq` (FAQ semanal) |
| [BOT_JAVA_v1](contratos/BOT_JAVA_v1.md) | Bot → Java | `POST /api/v1/mensajes/en-vivo` y la orden que Java devuelve |
| [PANEL_JAVA_v1](contratos/PANEL_JAVA_v1.md) | Panel → Java | Borradores, errores y dashboard |

**Regla de cambio:** un contrato solo crece con cambios que **agregan** (un campo o una puerta nueva). Cambiar o quitar algo existente exige una versión nueva y avisar a todas las piezas que lo usan.

Todas las piezas usan el mismo formato de error: `{codigo, mensaje, errores, idCorrelacion}`, sin repetir los datos recibidos.

---

## 7. Seguridad

| Tema | Cómo está resuelto |
|---|---|
| **Claves por cliente** | Cada pieza tiene su clave en la cabecera `X-Api-Key` (`API_KEY_INGESTA`, `API_KEY_BOT`, `API_KEY_PANEL`, `API_KEY_IA`), comparada en tiempo constante. **Cada clave abre solo su puerta:** la del bot, solo `/api/v1/mensajes/en-vivo`; la de la ingesta, solo `/api/v1/lotes`; la del panel, solo sus puertas. La ruta se compara normalizada y cada controlador vuelve a revisar el cliente |
| **La IA es privada** | Solo Java la llama, con `API_KEY_IA`. No tiene puerto público |
| **Inicio de sesión del panel** | Usuario y contraseña por persona (scrypt con sal), pausa por fallo, bloqueo tras 5 fallos y vencimiento a las 8 h sin uso. Los textos se muestran escapados (sin HTML) |
| **Secretos** | Viven en `.env`, que nunca va a git ni a las imágenes de Docker. Las claves internas se generan con `scripts/generar_api_key.py` y los usuarios con `scripts/crear_usuario_panel.py`, sin mostrarlas |
| **Puertos** | Solo en `127.0.0.1`. La base de datos y la IA nunca se publican |
| **CORS** | Cerrado: el panel llama a Java desde el servidor, no desde el navegador |
| **El bot** | Solo `#dudas` y `#logros`, sin menciones y **un solo bot encendido** (dos bots responderían dos veces) |

---

## 8. La IA por dentro

| Tema | Detalle |
|---|---|
| Proveedor | **Un solo proveedor: Google Gemini.** Modelo por defecto: `gemini-3.5-flash-lite` (`GEMINI_MODEL`). El Agente-Mod puede usar otro con `MOD_MODEL_NAME`. Este modelo ignora `temperature` |
| Tiempos (de adentro hacia afuera) | Cada llamada al LLM: 20 s · tope en vivo: 25 s · Java → IA: 30 s · bot → Java: 40 s. El Agente-Mod tiene 25 s; la FAQ semanal tiene un tope de 120 s y Java la espera 150 s |
| Búsqueda en los PDF (Agente FAQ) | Embeddings `intfloat/multilingual-e5-small` y reordenador `cross-encoder/ms-marco-MiniLM-L-6-v2`, descargados al construir la imagen (la IA arranca sin internet). Una respuesta con fidelidad media cuenta como **no encontrada** |
| El índice de los PDF | Está construido y guardado en `agents/agent_faq/data/vectorstore/faiss_pdfs/`. Si se agregan o cambian PDF en `data/pdfs/`, hay que reconstruirlo: 🔎 borrar `faiss_pdfs/` y volver a construir la imagen `ia`; al arrancar, la IA lo arma de nuevo (sin probar) |
| Lo que la IA nunca hace | Guardar el estado del sistema, publicar nada o hablar con la base de datos |

---

## 9. Las tareas de fondo de Java

| Tarea | Cada cuánto | Qué toma |
|---|---|---|
| Clasificación | 30 s, de a 5 | Mensajes `PENDIENTE` |
| Generación de borradores | 60 s, de a 3 | Logros sin generación |
| FAQ semanal | Lunes 8:00 (Bogotá); reintento cada 30 min | Las dudas de los últimos 7 días |
| Subida a OCI | 30 s, de a 10 | Borradores sin subir |

Las cuatro corren en paralelo (4 hilos), cada una con su propia reserva en la base. Todo se configura en `backend-java/src/main/resources/application.properties` y en variables del `.env` ([OPERACION.md](OPERACION.md) §2).

---

## 10. Dónde está cada cosa en el código

| Busco… | Carpeta |
|---|---|
| Las puertas HTTP de Java | `backend-java/src/main/java/com/insightedulab/backend_java/controller/` |
| Las claves y los permisos | `…/seguridad/` |
| Cada flujo de Java | `…/clasificacion/`, `…/envivo/`, `…/generacion/`, `…/faqsemanal/`, `…/curaduria/`, `…/dashboard/` y `…/oci/` |
| Las migraciones | `backend-java/src/main/resources/db/migration/` |
| Las puertas de la IA | `agents/orquestador/api.py` (`/v1/procesar`, `/v1/generar`, `/v1/faq` y `/health`) |
| La clasificación | `agents/orquestador/grafo_v1.py` y `clasificadores/etiquetador.py` |
| El Agente FAQ y los PDF | `agents/agent_faq/` |
| El Agente-Mod, la FAQ semanal y la guía de voz | `agents/agent_mod/` |
| El bot | `agents/bot_discord/` |
| El panel | `panel/` (`app.py`, `paginas/`, `auth.py` y `cliente_java.py`) |
| La ingesta y el contrato v1 | `ingestion/discord/` |
| Los scripts de claves y usuarios | `scripts/` |

⚠️ En `agents/orquestador/` todavía queda código de un diseño anterior que ya no se usa (`orquestador.py`, `nodos/`, `aristas/`, `adaptador.py`). Su limpieza está pendiente ([ESTADO.md](ESTADO.md)).

Las pruebas viven junto a cada pieza: `backend-java/src/test/`, `agents/orquestador/tests/`, `agents/bot_discord/tests/`, `panel/tests/` e `ingestion/discord/tests/`. Cómo correrlas: [AGENTS.md](../AGENTS.md).

---

## 11. Origen de cada pieza y créditos

InsightEdu Lab se construyó **sobre piezas que el equipo ya había desarrollado** en ramas separadas. Después, esas piezas se **integraron y adaptaron** a esta arquitectura: un solo formato, Java como única puerta y la IA privada.

| Pieza | Rama de origen | Autores (según el historial de git) | Qué se adaptó en la integración |
|---|---|---|---|
| Backend Java | `feature/java-core-api` | cris959, cevallosgabriel, MaxxyGuti3rr3z | Modelo de datos nuevo con Flyway, la puerta del contrato v1, las tareas de fondo, la curaduría, el dashboard, las claves por cliente y la subida a OCI |
| IA: orquestador, Agente FAQ y bot | Ramas `ai-engine` | Gonzalo Costela, Juan Sebastian Rodriguez | La IA acepta el contrato v1, clasifica con sentimiento y tema, queda privada detrás de Java; el bot pasa por Java |
| Panel | `feat/7-panel-minimo` | Jhon Patrick | Se conservó su diseño y se conectó a Java, con inicio de sesión, curaduría y dashboard |
| Ingesta y contrato v1 | `feature/discord-ingestion` | Harrison Tutalcha | Se reutilizó su conversión al contrato v1 también en el bot |
| Integración en esta arquitectura | `feature/integracion-arquitectura-3` | El equipo, con asistencia de IA | Agente-Mod, FAQ semanal y la conexión de todas las piezas |

La traza detallada de cómo se integró cada pieza (fichas de trabajo, informes y decisiones con su contexto) está en [docs/historico/](historico/).

---

## 12. Límites conocidos

- La ingesta todavía se corre a mano, y el despliegue en un servidor con HTTPS está diseñado pero no hecho ([ESTADO.md](ESTADO.md)).
- No hay roles ni permisos distintos por usuario en el panel; todos los usuarios pueden aprobar.
- No se leen hilos ni foros de Discord, y la IA no sube sus registros a OCI.
- El dashboard muestra "dudas sin responder" contando solo las respuestas del bot y las hechas con "Responder" de Discord.
