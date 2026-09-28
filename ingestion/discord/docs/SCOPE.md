# Ingesta de Discord — Alcance

> **Estado:** aprobado v1.0 · **Rama:** `feature/discord-ingestion` · **Fecha:** 2026-09-28

Este documento fija la pauta de cómo entran los mensajes de Discord a InsightEdu Lab. El backend programa contra el contrato que se define aquí.

## 1. Escenario

- InsightEdu Lab analiza conversaciones de comunidades educativas para responder dudas automáticamente y detectar hitos o logros de los alumnos.
- No hay datos reales. El servidor, los canales, los alumnos y el bot se simulan en Discord, que es gratis.
- Canales iniciales: `#dudas` y `#logros`.
- Flujo completo del sistema:
  `Discord → ingesta → API Java → motor IA (LLM) → API Java → respuesta en Discord`
  Esta rama cubre solo el primer tramo: **Discord → ingesta → API Java**.
- `backend-java` solo tiene el esqueleto de Spring Boot. Todavía no existe un endpoint de ingesta.
- Plazo: la hackatón dura 5 semanas. Al 2026-09-28 ha pasado 1.

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

## 4. Alcance

**Dentro**
- Objetivos O1 a O5.
- Especificación del endpoint de ingesta para que backend lo implemente.

**Fuera, por ahora**
- Limpieza del contenido (ortografía, jerga, sentido). Ver P1 y P2.
- Escucha en tiempo real (Gateway). Es la siguiente fase y la necesitará la respuesta automática.
- Responder en Discord, detectar hitos y la lógica del motor IA.
- Implementar el endpoint en Java. Lo hace backend a partir de nuestra especificación.

## 5. Pendientes

- **P1 · Calidad de los datos.** Investigar (en la web y con experiencia previa) cómo llegan los datos reales y definir reglas de limpieza. Puntos de partida conocidos:
  - Las menciones y los emojis llegan como códigos: `<@123…>`, `<#123…>`, `<:nombre:123…>`.
  - Hay markdown, bloques de código y mensajes sin texto que solo traen un adjunto o un sticker.
  - Hay mensajes editados (`edited_timestamp`) y borrados.
  - Los mensajes de sistema (alguien se unió, se fijó un mensaje) vienen mezclados con los de los alumnos.
  - Las URLs de los adjuntos caducan.
  - Hay errores de ortografía, jerga y mensajes partidos en varios envíos.
- **P2 · ¿Limpia el LLM?** Evaluar si el motor IA tolera o corrige los datos sucios, y qué limpieza deja de hacer falta.
- **P3 · Privacidad.** Decidir si se anonimiza a los alumnos antes de guardar sus datos.
- **P4 · Fechas en Java.** Usar `Instant` u `OffsetDateTime`, no `LocalDateTime`, para no perder la zona horaria.
- **P5 · Hilos.** Decidir si se extraen. Los mensajes dentro de un hilo no aparecen en el historial del canal; hay que recorrer los hilos aparte.
- **P6 · Extracción incremental.** Hoy `extract.py` descarga todo el historial en cada ejecución. En producción conviene pedir solo lo nuevo (parámetro `after` con el último ID guardado) y que la API Java ignore los IDs repetidos.
- **P7 · Mensajes partidos.** Una idea suele llegar en varios mensajes (saludo, contexto y pregunta; o una imagen y después su descripción). Decidir si la agrupación la hace la ingesta o el motor IA. Ver [DISCORD_DATA_GUIDE.md](DISCORD_DATA_GUIDE.md) §14.

## 6. Criterios de terminado

- [x] El servidor de prueba tiene `#dudas` y `#logros` con mensajes de al menos 5 alumnos ficticios.
- [x] Un comando extrae todos los mensajes de ambos canales, incluida la paginación.
- [x] No hay tokens, IDs ni URLs escritos en el código.
- [x] Hay muestras crudas guardadas y un diccionario de datos ([DISCORD_DATA_GUIDE.md](DISCORD_DATA_GUIDE.md)).
- [ ] El contrato v1 existe como JSON Schema y todos los mensajes extraídos lo cumplen.
- [ ] La salida a archivo funciona y la salida HTTP está probada.
- [ ] Backend recibió la especificación del endpoint.
