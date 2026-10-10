# Ingesta de Discord — Alcance

> ⚠️ **Documento histórico:** el alcance de la ingesta antes de la integración. **No es una instrucción vigente.** Cómo funciona hoy: [ARQUITECTURA.md](../../ARQUITECTURA.md) · Qué falta: [ESTADO.md](../../ESTADO.md)

> **Estado:** aprobado v1.3 · **Rama:** `feature/discord-ingestion` · **Fecha:** 2026-10-01

Este documento fija la pauta de cómo entran los mensajes de Discord a InsightEdu Lab. El backend programa contra el contrato que se define aquí.

## 1. Escenario

- InsightEdu Lab convierte la actividad de una comunidad EduTech en Discord en activos de marketing, contenido educativo y alertas de retención, con aprobación humana antes de publicar. Lo que pide el brief y los objetivos de negocio están en [PROJECT_BRIEF.md](../../../ingestion/discord/docs/PROJECT_BRIEF.md).
- Activos del MVP: post de LinkedIn, caso de éxito o testimonio, FAQ o contenido educativo, dashboard de salud con alertas, y un bot que responde dudas en vivo con la documentación de la institución.
- No hay datos reales. El servidor, los canales, los alumnos y el bot se simulan en Discord, que es gratis.
- Canales iniciales: `#dudas` y `#logros`. El catálogo de eventos suma otros (ver [EVENT_CATALOG.md](EVENT_CATALOG.md) §5).
- Flujo completo del sistema:
  `Discord → ingesta → API Java → motor IA (LLM) → API Java → respuesta en Discord`
  Los activos generados se guardan en OCI Object Storage.
  Esta rama cubre solo el primer tramo: **Discord → ingesta → API Java**. La arquitectura propuesta está en [ARCHITECTURE_PROPOSAL.md](ARCHITECTURE_PROPOSAL.md).
- Backend ya tiene una primera versión del endpoint de ingesta en la rama `feature/java-core-api`. Se compara con el contrato después de validarlo (paso 3.6).
- Plazo: la hackatón dura 5 semanas. **Entrega final: 2026-10-26.**

## 2. Objetivos (ETL)

| # | Objetivo | ETL |
|---|---|---|
| O1 | Entorno simulado: servidor de prueba, `#dudas`, `#logros`, bot y alumnos ficticios que publican mensajes | — |
| O2 | Conexión: autenticarse con la API de Discord y extraer todos los mensajes de ambos canales | Extraer |
| O3 | Conocer los datos: guardar muestras crudas y documentar qué campos entrega Discord | Exploración |
| O4 | Contrato de ingesta v1 (JSON Schema) y una transformación estructural mínima | Transformar |
| O5 | Entregar los mensajes a la API Java según el contrato | Cargar |

## 3. Decisiones

| Tema | Decisión propuesta | Motivo |
|---|---|---|
| Lenguaje y librerías del conector | Python 3.12 con `httpx` para extraer y enviar por REST. `discord.py` solo para la fase de tiempo real (Gateway) | `httpx` entrega el JSON crudo de Discord, que O3 necesita y que permite conservar el original. Además trae tiempo máximo de espera por defecto y es la base de los SDK que usa el motor IA. `discord.py` convierte los mensajes en objetos y el JSON original se pierde. Python 3.12 es la versión segura para las librerías del motor IA. |
| Forma de extraer | Peticiones REST al historial (`GET /channels/{id}/messages`, 100 mensajes por página) | Es lo que pide el objetivo: extraer bajo demanda, sin un proceso encendido todo el día. |
| Destino | Configurable: archivo JSON local o `POST` a la API Java | Backend todavía no tiene endpoint. Mientras tanto recibe JSON reales generados desde Discord, no archivos escritos a mano. |
| Formato del contrato | Modelo `pydantic` que genera el JSON Schema, con número de versión (`version_contrato`) | Backend programa contra la especificación, no contra un archivo fijo, y así se evita el hardcodeo. El motor IA ya usa `pydantic` (`contratos.py`), así que una sola definición valida los datos y produce el esquema. |
| Texto del mensaje | Se guarda el original sin modificar y los campos normalizados van aparte | Permite agregar la limpieza después (con reglas o con el LLM) sin volver a extraer. |
| Identificadores | Los IDs de Discord se guardan como texto. Se incluyen servidor, canal, mensaje, hilo y mensaje al que responde | Los IDs superan el entero seguro de JavaScript. El motor IA los necesita para responder en el lugar correcto. |
| Fechas | ISO 8601 en UTC, tal como las entrega Discord | Una sola zona horaria en todo el sistema. Se convierte solo al mostrarlas. |
| Secretos | El token del bot y las URLs de webhook van en `.env`, que Git ignora | Nunca se escriben en el código ni se suben al repo. |
| Simulación de alumnos | Webhooks de Discord, con un nombre distinto en cada mensaje | Automatizar cuentas de usuario (self-bots) viola los términos de Discord; los webhooks no. |
| Mensajes de webhook | Se conservan y se marcan como simulados | Llegan con `webhook_id` y no son de personas. Si se filtraran como si fueran de bots, se perdería toda la simulación. |
| Almacenamiento en la nube | OCI Object Storage es obligatorio para los **activos generados**. Para la ingesta es opcional: sirve de respaldo de los datos crudos, escritos por lotes | El brief pide *"persistir todos los paquetes de activos generados en un Bucket Always Free"*. El plan Always Free incluye 20 GB y 50.000 peticiones al mes: guardar un archivo por cada mensaje agotaría el cupo, por eso se escribe por lotes. |
| Databricks | No se usa en el MVP | El brief exige OCI, así que Databricks sería una segunda plataforma y no un reemplazo. Nadie del equipo la conoce y está pensada para volúmenes de datos que no tenemos. La organización por capas (crudo → contrato → activos) se logra con carpetas dentro del bucket de OCI. |
| Contenido del contrato | Todo campo que necesite algún caso de [EVENT_CATALOG.md](EVENT_CATALOG.md). Los datos crudos se conservan completos | Los eventos ocasionales pueden valer mucho, como una contratación. Si un dato no está en el contrato, sigue disponible en la capa cruda y se puede volver a procesar. |
| Datos de los miembros | No se extraen en el MVP: ni fecha de ingreso ni lista de roles. **Excepción (2026-10-01):** los roles del autor se consultan solo para calcular `autor.rol` (mentor o *staff*) | La deserción mensual se calcula con la actividad (autor y fecha de sus mensajes). Mide a quien dejó de escribir, no a quien abandonó el curso. Los roles sí hacen falta para reconocer a los mentores en una comunidad real (A8, C2, H1): en vivo llegan con el mensaje y por lotes cuestan una petición por autor. Ver [CONTRACT.md](../../../ingestion/discord/docs/CONTRACT.md) §8, decisión 2. |

## 4. Alcance

**Esta rama termina con el contrato v1, su entrega (O4 y O5) y un pull request a `main`.** Regla para no desviarse: ante cada idea nueva, preguntar **¿cambia el contrato?** Si no lo cambia, va a pendientes.

**Dentro**
- Objetivos O1 a O5.
- Especificación del endpoint de ingesta para que backend lo implemente.

**Fuera de esta rama.** Algunos puntos sí son parte del MVP, pero se construyen en otras ramas usando el mismo contrato.
- La escucha en tiempo real y el bot que responde dudas. Son parte del MVP y corresponden a la siguiente fase de la ingesta.
- La limpieza del contenido (ortografía, jerga, sentido). Ver P1 y P2.
- La lógica del motor IA, la detección de logros, el dashboard y el guardado de los activos en OCI.
- La implementación del endpoint en Java. La hace backend a partir de nuestra especificación.
- La extracción de hilos y foros (P5). El contrato ya tiene el campo `hilo`, que en el MVP va en `null`.
- Los datos de los miembros, salvo los roles que hacen falta para `autor.rol`.
- Ampliar la simulación para cubrir todos los eventos del catálogo.

## 5. Pendientes

- **P1 · Calidad de los datos.** Investigar (en la web y con experiencia previa) cómo llegan los datos reales y definir reglas de limpieza. Puntos de partida conocidos:
  - Las menciones y los emojis llegan como códigos: `<@123…>`, `<#123…>`, `<:nombre:123…>`.
  - Hay markdown, bloques de código y mensajes sin texto que solo traen un adjunto o un sticker.
  - Hay mensajes editados (`edited_timestamp`) y borrados.
  - Los mensajes de sistema (alguien se unió, se fijó un mensaje) vienen mezclados con los de los alumnos.
  - Las URLs de los adjuntos caducan.
  - Hay errores de ortografía, jerga y mensajes partidos en varios envíos.
- **P2 · ¿Limpia el LLM?** Evaluar si el motor IA tolera o corrige los datos sucios, y qué limpieza deja de hacer falta.
- **P3 · Privacidad y consentimiento.** Decidir si se anonimiza a los alumnos antes de guardar sus datos. Además, publicar un testimonio con nombre y cita en LinkedIn requiere el consentimiento del alumno.
- **P4 · Fechas en Java.** Usar `Instant` u `OffsetDateTime`, no `LocalDateTime`, para no perder la zona horaria.
- **P5 · Hilos y foros: descartados para el MVP.** Los mensajes dentro de un hilo o de un foro no aparecen en el historial del canal, y extraerlos exige recorrer los hilos aparte. Como el servidor de prueba lo diseñamos nosotros, `#dudas` es un canal normal y no se extraen hilos. **Limitación conocida:** si la institución real usa foros para las dudas, habrá que agregarlo. El brief pide "debates en foros", por eso el contrato v1 ya incluye el campo `hilo` (en `null`): agregar la extracción después no cambiará la versión del contrato.
- **P6 · Extracción incremental. Resuelto (2026-10-02).** `extract.py` pide solo lo posterior al marcador (parámetro `after`) y relee los últimos `INGEST_REREAD_DAYS` días (7 por defecto) para captar reacciones y ediciones. `send_batch.py` guarda el marcador cuando backend confirma la recepción. Falta del lado de backend: actualizar en lugar de duplicar (*upsert*), según [INGESTION_GUIDE.md](INGESTION_GUIDE.md) §9.
- **P7 · Mensajes partidos.** Una idea suele llegar en varios mensajes (saludo, contexto y pregunta; o una imagen y después su descripción). Decidir si la agrupación la hace la ingesta o el motor IA. Ver [DISCORD_DATA_GUIDE.md](../../../ingestion/discord/docs/DISCORD_DATA_GUIDE.md) §14.
## 6. Criterios de terminado

- [x] El servidor de prueba tiene `#dudas` y `#logros` con mensajes de al menos 5 alumnos ficticios.
- [x] Un comando extrae todos los mensajes de ambos canales, incluida la paginación.
- [x] No hay tokens, IDs ni URLs escritos en el código.
- [x] Hay muestras crudas guardadas y un diccionario de datos ([DISCORD_DATA_GUIDE.md](../../../ingestion/discord/docs/DISCORD_DATA_GUIDE.md)).
- [x] El contrato v1 existe como JSON Schema ([schema/contract_v1.schema.json](../../../ingestion/discord/schema/contract_v1.schema.json)) y los 38 mensajes extraídos lo cumplen (2026-10-02).
- [ ] La salida a archivo funciona y la salida HTTP está probada. La salida a archivo funciona. El envío HTTP (opción C, histórica: reemplazada por D8 el 2026-10-03) está probado contra un backend simulado; falta probarlo contra el backend real.
- [ ] Backend recibió la especificación del endpoint.
- [ ] Hay un pull request abierto hacia `main`.
