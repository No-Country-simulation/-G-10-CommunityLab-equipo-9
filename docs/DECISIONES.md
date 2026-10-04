# Registro de decisiones — InsightEdu Lab

> **Qué es:** el índice único de todo lo que se decidió en el proyecto. Cada fila resume la decisión en una línea y enlaza al documento con el detalle. Si algo choca, manda el documento enlazado.
> **Quién lo mantiene:** el chat principal. Cada decisión nueva suma una fila aquí, y su detalle va en su documento.
> **Actualizado:** 2026-10-04 · **Rama:** `feature/integracion-arquitectura-3`

## 0. Cómo leer

| Estado | Significa |
|---|---|
| ✅ | Vigente |
| 🔁 | Reemplazada: la fila dice por cuál |
| ⚠️ | Riesgo aceptado: se sabe y se decidió convivir con él |
| ⏸️ | Pospuesta: se retoma más adelante |
| ❓ | Pendiente de decidir |

Las decisiones grandes del análisis se llaman **D1 a D8**; las de este registro se numeran **DEC-01, DEC-02…** Los códigos S*, F*, C*, O* y OE* son hallazgos y objetivos del [análisis](ANALISIS_INGENIERIA_PROPUESTA_3.md).

## A · Proyecto y alcance

| # | Fecha | Decisión | Por qué | Estado | Detalle en |
|---|---|---|---|---|---|
| DEC-01 | 2026-10-01 | Solo posts de **LinkedIn**: sin X ni newsletters | Acotar el MVP a 5 semanas | ✅ | [PROJECT_BRIEF.md §3](../ingestion/discord/docs/PROJECT_BRIEF.md) |
| DEC-02 | 2026-10-01 | Sin el resumen semanal *Community Highlights* | Igual que DEC-01 | ✅ | PROJECT_BRIEF.md §3 |
| DEC-03 | 2026-10-01 | Solo **Discord** (no Slack) | Igual que DEC-01 | ✅ | PROJECT_BRIEF.md §3 |
| DEC-04 | 2026-09-29 | Un **bot que responde dudas en vivo** (no lo pide el brief) | Valor para el alumno; obliga a que la ingesta funcione en tiempo real | ✅ | PROJECT_BRIEF.md §3 |
| DEC-05 | 2026-09-29 | No usar Databricks | El brief exige OCI; nadie lo conoce y no hace falta para este volumen | ✅ | [SCOPE.md §3](../ingestion/discord/docs/SCOPE.md) |
| DEC-06 | 2026-10-02 | Arquitectura: **propuesta 3** (un solo formato, Java como única puerta y registro oficial, IA privada, sin n8n ni ngrok) | Reutiliza lo construido y lo conecta. El equipo no la confirmó: la adopta Harrison | ✅ | [PDF de la propuesta 3](referencias/Propuesta_3_Arquitectura_InsightEdu.pdf) |
| DEC-07 | 2026-10-02 | Rama de integración `feature/integracion-arquitectura-3` = `main` + backend + ingesta | Probar la propuesta 3 de punta a punta | ✅ | [Análisis §8](ANALISIS_INGENIERIA_PROPUESTA_3.md#8-gestión-del-trabajo) |
| DEC-08 | 2026-10-03 | Harrison desarrolla **todo el proyecto en esa rama**, con Claude. Las ramas de los otros equipos no se tocan | Avanzar sin depender de la coordinación entre equipos | ✅ | Análisis §8 |
| DEC-09 | 2026-10-03 | **D1 · Base congelada:** no se traen cambios nuevos de otras ramas | Evitar conflictos en cada fusión | ✅ | Análisis §0 |
| DEC-10 | 2026-10-03 | **Plan de 2 días** para fijar la base: modelo de datos, formato Java ↔ IA y puerta de lotes | Que los demás no hagan cambios fuertes en paralelo | ✅ Cumplido el 2026-10-04 | Análisis, registro de avance |
| DEC-11 | 2026-10-03 | Objetivo principal y OE1 a OE9. Si falta tiempo, lo último que se recorta es OE1, OE3 y OE6 | Un solo lugar para decidir "¿esto sirve?" | ✅ | Análisis § Objetivos |
| DEC-12 | 2026-10-03 | **Trabajo en varios chats:** un chat principal (guía, orquestador y auditor) y chats de tarea; una rama por tarea; un chat a la vez; auditoría antes de fusionar | Cuidar el contexto sin perder el conocimiento | ✅ | [CLAUDE.md §6](../CLAUDE.md), [CHAT_PRINCIPAL.md](CHAT_PRINCIPAL.md) |
| DEC-83 | 2026-10-04 | La **FAQ semanal** va en una ficha aparte (**T06b**), después de T06, y se arma con los datos de Java, no con el historial que el Agente FAQ guarda dentro de la IA | Que T06 se concentre en OE3, que es crítico. Regla 3 de la propuesta: la IA no guarda la verdad del sistema | ✅ | [T06 §1.1](tareas/T06-agente-mod.md) |
| DEC-13 | 2026-10-03 | Al repositorio, que es público, solo sube la propuesta 3. **No** suben el brief oficial, el discovery, las notas de reunión ni el traspaso del chat anterior | Documentos de terceros o con datos de personas; el traspaso "crearía sesgo" | ✅ | Este registro |
| DEC-14 | 2026-10-03 | Modelos de Claude: **Opus 5.5** para el chat principal y las tareas que definen una base; **Sonnet 5.5** para las acotadas | Equilibrio entre calidad y límite de uso | ✅ | CHAT_PRINCIPAL.md §4 |
| DEC-65 | 2026-10-04 | Los mensajes de commit **ya no llevan** la línea `Co-Authored-By: Claude…` | Decisión de Harrison | ✅ | [CLAUDE.md §6](../CLAUDE.md) |

## B · Arquitectura y contratos

| # | Fecha | Decisión | Por qué | Estado | Detalle en |
|---|---|---|---|---|---|
| DEC-15 | 2026-10-01 | **Contrato v1** de la ingesta (lote y mensaje), con sus 7 decisiones | Un formato acordado para todo el sistema | ✅ | [CONTRACT.md §8](../ingestion/discord/docs/CONTRACT.md) |
| DEC-16 | 2026-10-02 | Opción C, "etiqueta + caja": la ingesta convertía al formato viejo de backend | Puente para no esperar al equipo de backend | 🔁 Reemplazada por DEC-17 | [INGESTION_GUIDE.md §11](../ingestion/discord/docs/INGESTION_GUIDE.md) |
| DEC-17 | 2026-10-03 | **D8:** Java recibe el **contrato v1 tal cual** en `POST /api/v1/lotes` | Un solo formato en todo el sistema (regla 1 de la propuesta 3) | ✅ | Análisis §0 y [T03](tareas/T03-puerta-lotes.md) |
| DEC-18 | 2026-10-02 | Flujo en vivo: Discord → bot → Java → IA → Java → bot | Que todo quede registrado y que la IA sea privada | ✅ Hecho en T05 | PDF de la propuesta 3, análisis C2 |
| DEC-19 | 2026-10-03 | **D3:** el bot responde **sin aprobación humana**, pero solo si encontró respaldo en los PDFs; si no, deriva a un mentor | N6 protege lo que se publica fuera de Discord; en vivo no se puede esperar una aprobación | ✅ | Análisis §0 |
| DEC-20 | 2026-10-03 | **D4:** el flujo en vivo **espera** la respuesta, con tiempos máximos de 20 s (LLM) < 30 s (Java → IA) < 40 s (bot → Java), y muestra "escribiendo…" | Simple de construir y suficiente para la demo | ✅ | Análisis §0 y F8 |
| DEC-21 | 2026-10-03 | **D2:** en OCI se guardan los activos `generados/` y los `aprobados/` | Cumple la letra del brief y la intención de la propuesta 3 | ✅ Se implementa en T09 | Análisis §0 |
| DEC-22 | 2026-10-03 | **Contrato Java ↔ IA v1:** `POST /v1/procesar`, camelCase, un resultado por mensaje | Que Java implemente sin adivinar | ✅ Con el agregado de T04 (DEC-58) | [JAVA_IA_v1.md](contratos/JAVA_IA_v1.md) |
| DEC-23 | 2026-10-03 | La IA **importa** `contract.py`: no lo copia | Una sola definición del contrato | ✅ | [T02-informe §3](tareas/T02-informe.md) |
| DEC-24 | 2026-10-03 | **`ERROR` ≠ `OTRO`** (F4). Sin LLM configurado, el resultado es `ERROR`; las palabras clave se usan solo si se eligen | Un fallo no se disfraza de ruido | ✅ | T02-informe §5 |
| DEC-25 | 2026-10-03 | Los mensajes de bots, los avisos del sistema y los que no tienen texto salen como `OTRO` por regla, sin LLM, con sentimiento y tema vacíos y el campo `metodo` | No gastar el LLM y no ensuciar el dashboard | ✅ | T02-informe §5 |
| DEC-26 | 2026-10-03 | La IA genera la respuesta del FAQ **solo en `tiempoReal`**, nunca en `historial` | No gastar respondiendo dudas viejas | ✅ | [T02](tareas/T02-formato-java-ia.md) |
| DEC-27 | 2026-10-03 | Java clasifica **en segundo plano y en tandas chicas**; un fallo de la IA no cambia estados y se reintenta hasta un máximo | Un lote de historial no entra en 30 s (observación de T02) | ✅ Hecho en T04: cada 30 s, tandas de 5, máximo 3 intentos (configurable) | [T04-informe](tareas/T04-informe.md) |
| DEC-28 | 2026-10-03 | Formato común de error en Java y en la IA: `{codigo, mensaje, errores, idCorrelacion}`, sin repetir los datos recibidos | Errores claros y sin fugas (S7) | ✅ | Análisis §2, T02 y T03 |
| DEC-58 | 2026-10-04 | El cambio de T04 al contrato Java ↔ IA queda **aprobado sin cambiar de versión**: `X-Api-Key` obligatoria en `/v1/procesar` y un código más, `NO_AUTORIZADO` (401) | Solo agrega: nada de lo que existía cambia, y lo pedía S2. Validado por Harrison en T04 y revisado en la auditoría | ✅ | JAVA_IA_v1.md §1 y §7, [T04-informe §5](tareas/T04-informe.md) |
| DEC-59 | 2026-10-04 | La tanda se **reserva** con `SKIP LOCKED` y `reservado_hasta` (2 min), y la IA se llama **sin transacción abierta**. Un resultado se guarda solo si el mensaje no cambió (`actualizado_en`) | Una transacción abierta 30 s bloquearía la ingesta; la reserva vence sola si Java se cae | ✅ | T04-informe §5 |
| DEC-60 | 2026-10-04 | Un **422** de la IA suma un intento solo a los mensajes que señala `errores[].campo`; si no señala ninguno, a todos | No castigar a toda la tanda por un mensaje, y no reintentar sin fin | ✅ | T04-informe §5 |
| DEC-67 | 2026-10-04 | Si Java o la IA fallan en el flujo en vivo, **el bot no responde nada** (solo lo registra, sin el texto). El lote de la hora rescata el mensaje | El bot no sabe si era una duda o un "gracias"; la duda aparece como "sin responder" en el dashboard (F9) | ✅ Hecho en T05 | [T05 §1.1](tareas/T05-bot-en-vivo.md) |
| DEC-68 | 2026-10-04 | **Java decide qué hace el bot** y le devuelve una orden (`RESPONDER`, `DERIVAR`, `REACCIONAR` o `NADA`). Contrato nuevo: `docs/contratos/BOT_JAVA_v1.md`. El bot envía el contrato v1 tal cual | Las reglas (D3, F5) quedan en un solo lugar, con pruebas; el bot queda simple | ✅ Hecho en T05 | T05 §1.1 |
| DEC-75 | 2026-10-04 | El bot pide el JSON crudo del mensaje con `GET /channels/{canal}/messages/{id}` y lo convierte con `transform.py` de la ingesta | Una sola implementación del contrato (C2). 🧪 El mensaje en vivo y el del lote de la hora salen idénticos | ✅ | [T05-informe §5](tareas/T05-informe.md) |
| DEC-77 | 2026-10-04 | En `RESPONDER`, Java publica el texto del Agente FAQ **tal cual**, sin agregar un pie de fuentes. `respuesta_fuentes` se guarda igual | El texto ya cita el documento que usó; el pie lo repetía y a veces nombraba otro documento | ✅ | T05-informe §5, [BOT_JAVA_v1.md](contratos/BOT_JAVA_v1.md) |
| DEC-79 | 2026-10-04 | `RESPONDIDA` se guarda cuando Java decide, **antes** de que el bot publique | Confirmar la publicación obligaría a cambiar el contrato bot ↔ Java por un caso raro (Discord rechaza la respuesta). Decisión del chat principal | ⚠️ Riesgo aceptado | T05-informe §6 |
| DEC-80 | 2026-10-04 | Los borradores de los logros se generan **solos**: una tarea programada en Java busca los `TESTIMONIO` sin generación y se los pide a la IA | Marketing encuentra los borradores listos; mismo patrón que la clasificación de T04 | ✅ Se implementa en T06 | T06 §1.1 |
| DEC-82 | 2026-10-04 | Java pide los borradores en una **puerta nueva de la IA, `POST /v1/generar`**, separada de `/v1/procesar`. Solo agrega al contrato Java ↔ IA | Etiquetar y redactar son trabajos distintos; redactar es más lento y se puede repetir | ✅ Se implementa en T06 | T06 §1.1 |
| DEC-61 | 2026-10-04 | Si falla **toda** la llamada (401, 500, tiempo agotado o IA caída), los mensajes suman un intento y siguen `PENDIENTE` | Un fallo pasajero no pierde ni marca mal ningún mensaje | ✅ | T04-informe §5 |

## C · Datos

| # | Fecha | Decisión | Por qué | Estado | Detalle en |
|---|---|---|---|---|---|
| DEC-29 | 2026-10-03 | Modelo nuevo de 3 tablas (`lotes_recibidos`, `mensajes`, `borradores`); se elimina el modelo viejo de "un paquete por lote" | El viejo no servía para N3, N5 ni N6 | ✅ | Análisis §5, [T01](tareas/T01-modelo-datos.md) |
| DEC-30 | 2026-10-03 | **Flyway** con `ddl-auto=validate`. Una migración aplicada nunca se edita: los cambios van en `V2__…` | La misma base en todas las máquinas | ✅ | [OPERACION.md §5](OPERACION.md) |
| DEC-31 | 2026-10-03 | Upsert por `discord_id` con `ON CONFLICT`: no duplica, **no pisa las etiquetas de la IA**, vuelve a `PENDIENTE` si cambió el texto y da `SIN_CAMBIOS` si llega idéntico | F1, F2 y F3 | ✅ | [T01-informe §5](tareas/T01-informe.md) |
| DEC-32 | 2026-10-03 | Los valores cerrados se guardan **tal cual los define el contrato** (`persona`, `botPropio`, `historial`…) | Fidelidad al contrato | ✅ | T01-informe §5 |
| DEC-33 | 2026-10-03 | `borradores.mensaje_id` es obligatorio salvo en el tipo `FAQ` | La FAQ semanal junta varias preguntas | ✅ | T01-informe §5 |
| DEC-34 | 2026-10-03 | Listas cerradas: **sentimiento** (5 valores) y **tema** (11 temas, incluidos `calendario_clases` y `herramientas_entorno`) | Que el dashboard pueda contar | ✅ `CHECK` en la V2 (T04) | JAVA_IA_v1.md §4.3 |
| DEC-35 | 2026-10-03 | Los lotes son **idempotentes** por `loteId`: un reenvío recibe el mismo recibo | La ingesta reintenta si se corta la red | ✅ | [T03-informe §5](tareas/T03-informe.md) |
| DEC-36 | 2026-10-04 | El carácter invisible **NUL** se **quita al recibir**, en lugar de rechazar el lote | PostgreSQL no lo acepta (📘) y un solo mensaje trabaría toda la ingesta | ✅ Hecho en T04: se quita de todos los textos del lote, también de la caja | T04-informe §5 |
| DEC-37 | 2026-10-04 | Las URL de los adjuntos que cambian e inflan los "actualizados" **se dejan así** | Solo afectan un contador; no reinician la clasificación | ✅ | T03-informe §6 |
| DEC-38 | 2026-10-03 | Las pruebas de Java usan la base `insightedu_test`, con un freno que impide correrlas sobre otra base | No borrar la base principal por error | ✅ | OPERACION.md §5 |
| DEC-62 | 2026-10-04 | `mensajes.servidor_id` (V2) admite vacío: los mensajes anteriores a la V2 no se clasifican hasta que la ingesta los reenvía, y un envío sin servidor no borra el que ya estaba | Ni recrear la base ni inventar un servidor | ✅ | T04-informe §5 |
| DEC-63 | 2026-10-04 | Si cambia el texto de un mensaje, sus intentos de clasificación vuelven a 0 | Un texto nuevo merece todas sus oportunidades | ✅ | T04-informe §5 |
| DEC-66 | 2026-10-04 | Lo que respondió el bot se guarda **en la fila del mensaje** (migración `V3`): `respuesta_estado` (`RESPONDIDA` / `DERIVADA`), texto, fuentes y hora. No se usa `borradores` | Es un dato del mensaje, como sus etiquetas; `borradores` es la bandeja de aprobación (N6) y las respuestas del bot no se aprueban (D3) | ✅ Hecho en T05 | T05 §1.1 |
| DEC-81 | 2026-10-04 | Los borradores nombran al alumno **solo por su primer nombre**, y al LLM le llega solo ese dato (ni el nombre completo, ni el usuario, ni los IDs) | El `Reglamento de Comunicaciones` de CommunityLab prohíbe publicar nombres completos sin consentimiento; el panel pedirá el consentimiento (D6) | ✅ Se implementa en T06 | T06 §1.1 |
| DEC-72 | 2026-10-04 | La primera respuesta del bot, que mostraba la ruta de la PC de un compañero, **se deja** publicada en el servidor de pruebas y guardada en la base (fila 165) | Decisión de Harrison: es el servidor de pruebas | ⚠️ Riesgo aceptado | T05-informe §4.5 |

## D · Seguridad

| # | Fecha | Decisión | Por qué | Estado | Detalle en |
|---|---|---|---|---|---|
| DEC-39 | 2026-10-03 | **API key por cliente** en la cabecera `X-Api-Key`, comparada en tiempo constante; `/actuator/health` queda libre. Sin clave configurada, Java rechaza todo con 401 | S1 | ✅ | T03-informe §5 |
| DEC-40 | 2026-10-03 | Las claves se generan con un script **que no las muestra** (`scripts/generar_api_key.py`; desde T04, `--cliente ia` para la de la IA) | Que nunca pasen por la pantalla ni por el chat | ✅ | T03 |
| DEC-64 | 2026-10-04 | **S2:** la IA exige `X-Api-Key` (`API_KEY_IA`) en toda ruta `/v1/…`, revisada antes que el cuerpo y en tiempo constante. `/health` queda libre y `/procesar` (el del bot) sin clave hasta C2 | Que solo Java pueda pedirle trabajo a la IA | ✅ | T04-informe §5 |
| DEC-70 | 2026-10-04 | **Cada clave abre solo su puerta:** `POST /api/v1/mensajes/en-vivo` solo para el cliente `bot`, y `POST /api/v1/lotes` solo para `ingesta` (403 para los demás). Desde la auditoría de T05, el filtro compara la ruta normalizada y cada controlador vuelve a revisar el cliente | Si se filtra una clave, el daño queda limitado a su puerta | ✅ Hecho en T05 | T05 §3 |
| DEC-71 | 2026-10-04 | Las claves que se pegaron en el chat de T05 (token del bot, 2 webhooks y clave de la ingesta) **no se cambian** | 🧪 No son públicas: no están en git; solo quedaron en la conversación guardada en la PC y en Anthropic. Decisión de Harrison | ⚠️ Riesgo aceptado (al desplegar, claves nuevas: T10) | T05-informe §6 |
| DEC-74 | 2026-10-04 | El `.env` de la raíz lleva también las variables de Discord que necesita el bot para reconocer simulados y mentores (webhooks, roles de mentor y de staff, mentores simulados), con los nombres de la ingesta | Sin ellas, el contrato del bot sale distinto del lote (rompe C2). Las URL de los webhooks quedan también en el contenedor `bot` | ✅ | T05-informe §5 |
| DEC-41 | 2026-10-03 | La URL PAR de OCI que quedó en el historial público **no se persigue**. Esta rama usa siempre una PAR nueva | Decisión de Harrison | ⚠️ Riesgo aceptado | Análisis S4 |
| DEC-42 | 2026-10-03 | Puertos solo en `127.0.0.1`, la base sin puerto publicado y el panel como único servicio público (con clave) | S5 | ✅ | [compose.yml](../compose.yml), análisis §3 |
| DEC-43 | 2026-10-03 | Nunca leer ni mostrar un `.env`: solo los nombres de sus variables | Proteger el token del bot, los webhooks y las claves | ✅ | CLAUDE.md §5 |
| DEC-44 | 2026-10-03 | **D6:** una casilla de consentimiento obligatoria en el panel antes de aprobar un post con el nombre de un alumno | Usa datos personales | ✅ Se implementa en T07 | Análisis §0 |

## E · IA

| # | Fecha | Decisión | Por qué | Estado | Detalle en |
|---|---|---|---|---|---|
| DEC-45 | 2026-10-03 | **D5:** un solo proveedor, **Google Gemini**, con el modelo `gemini-3.5-flash-lite` (📘 estable). Este modelo ignora `temperature` | Una clave, una cuenta y un solo límite de uso | ✅ | Análisis §0, [compose.yml](../compose.yml) |
| DEC-46 | 2026-10-03 | La IA atiende pedidos en paralelo (F6), crea el Agente FAQ una sola vez (F7), lo precarga al arrancar, carga los embeddings una sola vez y no usa internet para los modelos | 🧪 La primera pregunta bajó de 36,6 s a 3,97 s | ✅ | Análisis, registro de avance |
| DEC-47 | 2026-10-03 | Se quitó **ChromaDB** | Solo se escribía y nunca se leía; costaba 14,6 s y 79 MB | ✅ | Análisis §5 |
| DEC-48 | 2026-10-03 | Tope de **20 s** por llamada al LLM, con 1 reintento | D4, F8 | ✅ | T02-informe §5 |
| DEC-49 | 2026-10-03 | Una respuesta del FAQ con fidelidad media cuenta como **no encontrada** | Aplicar D3 con prudencia | ✅ | T02-informe §5 |
| DEC-54 | 2026-10-04 | **Tope total de 25 s** por pedido en `tiempoReal` (`TIEMPO_REAL_TOPE_S`). Si se agota, la IA devuelve las etiquetas con `respuesta.encontrada = false`, y el bot deriva al mentor | Una duda encadena hasta 3 llamadas al LLM de 20 s; así la respuesta llega antes de los 30 s de Java (observación de T02). Solo agrega al contrato Java ↔ IA | ✅ Hecho en T05 | T05 §1.1 |
| DEC-69 | 2026-10-04 | T05 quita solo la puerta vieja `/procesar` de la IA. El resto del código viejo (`orquestador.py`, `nodos/`, `aristas/`…) se borra más adelante | El Agente FAQ todavía usa `contratos.py`, y T05 ya es grande | ✅ (la limpieza queda como mejora 🟡) | T05 §3 |
| DEC-73 | 2026-10-04 | Una pregunta que **no es del curso** se clasifica como `PREGUNTA_FAQ` con tema `otro`, y el bot la **deriva al mentor** | Decisión de Harrison: ningún alumno que pregunta se queda sin respuesta. A cambio, los mentores y el dashboard ven también esas preguntas | ✅ Hecho en T05 (auditoría) | T05-informe §8.2 |
| DEC-76 | 2026-10-04 | Las fuentes llevan **solo el nombre del PDF y la página**, nunca la ruta de una PC | 🧪 En la prueba real apareció la ruta de la PC de un compañero. Se corrigió en el origen (`reranker.py`) y en `grafo_v1.py` | ✅ | T05-informe §5 |
| DEC-78 | 2026-10-04 | El tope de 25 s también corta la **clasificación**. Si la agota, el resultado es `ERROR` y el bot no responde | Con un reintento del LLM, el pedido podía pasar de los 30 s de Java | ✅ | T05-informe §5 |
| DEC-53 | 2026-10-04 | Antes de redactar, **la IA decide si un logro es publicable** y deja escrito el motivo; si no lo es, no hay borrador (por ejemplo, "por fin entendí recursividad") | El problema del cliente es el tiempo que pierde Marketing (brief §2.3) | ✅ Se implementa en T06 | T06 §1.1 |
| DEC-84 | 2026-10-04 | La **guía de voz de CommunityLab** la redacta el chat de T06 y la aprueba Harrison. Vive en un archivo del Agente-Mod que la IA lee al arrancar | No existe una guía; una institución real solo tendría que cambiar el archivo | ✅ Se implementa en T06 | T06 §3 |
| DEC-85 | 2026-10-04 | El modelo de Gemini del Agente-Mod se configura con `MOD_MODEL_NAME` (por defecto, el mismo que clasifica) | Redactar posts puede necesitar un modelo más potente; sigue siendo un solo proveedor (D5) | ✅ Se implementa en T06 | T06 §3 |

## F · Operación

| # | Fecha | Decisión | Por qué | Estado | Detalle en |
|---|---|---|---|---|---|
| DEC-50 | 2026-10-03 | Todo se levanta con **Docker Compose**: un `.env` en la raíz para Docker y otro en `ingestion/discord/` para la ingesta; `postgres:17` con volumen; PyTorch solo para CPU | Un solo comando, sin instalar Java ni librerías en Windows | ✅ | OPERACION.md |
| DEC-51 | 2026-10-03 | La revisión del servidor (O4) se pospone a la fase de despliegue | Harrison no la ve prioritaria ahora | ⏸️ Se retoma en T10 | Análisis § Objetivos (OE9) |
| DEC-52 | 2026-10-03 | **D7:** desplegar primero en el servidor del equipo | Ya existe y el equipo lo probó | ⏸️ Depende de DEC-51 | Análisis §0 |

## G · Pendientes de decidir

| # | Pregunta | Cuándo | Origen |
|---|---|---|---|
| DEC-55 | ¿Hace falta vincular lotes y mensajes (una tabla intermedia)? | T07, solo si el panel lo necesita | Observación de T01 |
| DEC-56 | Red interna o HTTPS para que las claves no viajen en texto plano; ¿hay dominio para el HTTPS del panel? | T10 | Observación de T03, S3 |
| DEC-57 | ¿Qué versión se entrega el 26 de octubre? ¿Se avisa al equipo? | Antes de T10 | Análisis §8 (riesgo "dos versiones") |

Ya resueltas: DEC-58 (el cambio de T04 al contrato Java ↔ IA), en la auditoría de T04; DEC-54 (el tope en vivo), en la ficha T05, y DEC-53 (los logros de aprendizaje), en la ficha T06. Ahora están en las secciones B y E.
