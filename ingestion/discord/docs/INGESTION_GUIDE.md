# Guía de la ingesta para el equipo — InsightEdu Lab

> **Estado:** v1.0, para revisar con backend · **Fecha:** 2026-10-02 · **Rama:** `feature/discord-ingestion`

## 0. Cómo leer este documento

> Qué vas a entender aquí: para quién es este documento, qué vas a saber al terminarlo y cómo están marcadas las fuentes.

**Para quién.** Todo el equipo de InsightEdu Lab: backend, IA, frontend y data. **No hace falta** haber usado Discord ni haber trabajado antes con integraciones entre sistemas: todo se explica desde cero.

**Qué vas a entender al terminar:**
1. qué problema del negocio resolvemos y por qué todo empieza en la ingesta;
2. cómo viaja un mensaje desde Discord hasta la IA, por lotes y en vivo;
3. qué es el contrato de ingesta y para qué sirve cada uno de sus campos;
4. cómo se evita guardar dos veces el mismo mensaje;
5. qué encontramos al comparar el contrato con lo que construyó backend, y qué opciones proponemos.

**Cuánto tarda.** La sección 1 se lee en 3 minutos y alcanza para saber lo esencial. El documento completo, unos 40 minutos.

**Qué leer según tu rol:**

| Rol | Secciones |
|---|---|
| Todos | 1, 2 y 6 |
| Backend | Todo, con atención a las secciones 9 a 12 |
| IA | 1, 2, 5, 7 y 8 |
| Frontend y data | 1, 2, 5 y 8 |

**De dónde sale cada afirmación:**
- 📘 **Documentación oficial de Discord** (repositorio `discord/discord-api-docs`).
- 📄 **Brief del cliente:** el enunciado de la hackatón.
- 🤝 **Decisión del equipo,** con su fecha.
- 💻 **Código de backend:** rama `feature/java-core-api`, commit `b5e03e9` del 2026-10-02.
- 🧪 **Observado** en nuestro servidor de pruebas.
- 🔎 **Deducción nuestra:** razonable, pero no verificada.

**Documentos relacionados** (este documento los resume; el detalle está en ellos):
- [PROJECT_BRIEF.md](PROJECT_BRIEF.md): el brief y qué entra en el MVP.
- [DISCORD_DATA_GUIDE.md](DISCORD_DATA_GUIDE.md): cómo son los datos de Discord.
- [EVENT_CATALOG.md](EVENT_CATALOG.md): el catálogo de casos de la comunidad.
- [CONTRACT.md](CONTRACT.md): el contrato de ingesta, campo por campo.
- [SCOPE.md](SCOPE.md): el alcance de la ingesta y los pendientes.

---

## 1. Resumen en una página

> Qué vas a entender aquí: lo esencial de todo el documento, por si solo lees esta sección.

**Qué hicimos (ingesta).**
- Un servidor de Discord de pruebas, con 7 alumnos y 1 mentor simulados.
- Un programa que extrae todos los mensajes de los canales.
- Una guía de cómo son los datos de Discord y un catálogo de las situaciones de la comunidad que le importan al negocio.
- Con todo eso, diseñamos el **contrato de ingesta**: el formato en que cada mensaje de Discord entra al sistema. Tiene **6 campos en el lote** y **23 campos por mensaje**. Sirve igual para el análisis **por lotes** y para el **bot en vivo**.

**Qué encontramos al compararlo con backend.** Backend ya tiene lista la "puerta" que recibe los mensajes, con buenas decisiones (fechas en `Instant`, validaciones, recibo de respuesta). Pero hay cuatro hallazgos:
1. Su formato recibe **9 de los datos** que necesitan los casos del MVP. Faltan, por ejemplo, **a qué mensaje responde cada uno** (sin eso no hay FAQ) y **las reacciones** (sin eso no se mide un logro).
2. El texto es obligatorio: **un mensaje que solo trae una imagen hace rechazar el lote entero**.
3. **No evita duplicados:** si el mismo mensaje llega dos veces, se guarda dos veces.
4. Su clasificación de autores (`HUMANO` o `AI`) mide otra cosa que la nuestra.

**Qué proponemos.** Tres opciones (sección 11). Recomendamos la **opción C, "etiqueta + caja"**:
- backend conserva sus campos tal como están;
- agrega **una sola columna** que guarda el mensaje completo;
- hace cuatro ajustes chicos.

Son unas 25 a 30 líneas de código, sin tablas nuevas.

**Qué les preguntamos.** Qué opción prefieren y cómo resolver juntos los duplicados (sección 12).

**Fechas.** El pull request de la ingesta, alrededor del **2026-10-10**. La entrega final de la hackatón, el **2026-10-26**.

---

## 2. El problema del negocio

> Qué vas a entender aquí: para qué existe InsightEdu Lab y por qué todo depende de la ingesta.

**El problema** 📄. Las comunidades educativas en Discord generan a diario historias inspiradoras, dudas que se repiten y testimonios valiosos. Pero la mayor parte de ese valor **se pierde en el historial de los canales**: revisar los mensajes y producir contenido a mano les cuesta muchas horas a los equipos de Community Management y de Marketing.

**La solución** 📄. Un sistema que **captura** automáticamente la actividad de la comunidad, la **analiza** con IA y la **convierte** en activos listos para publicar. Una persona revisa y aprueba antes de publicar.

**Qué entra en el MVP** 🤝:

| Activo | Para quién | Ejemplo |
|---|---|---|
| Post de LinkedIn | Marketing | Un post a partir del logro de una alumna |
| Caso de éxito con citas | Marketing | "Después de 6 meses y 40 postulaciones, me contrataron" |
| FAQ y contenido educativo | Community Manager y equipo educativo | Un tutorial a partir de una duda que se repite |
| Dashboard de salud con alertas | Community Manager | Una alerta: "Luis lleva 14 días sin escribir" |
| Bot que responde dudas en vivo | Alumnos | El bot contesta "¿cómo instalo Python?" al instante |

**Qué no entra** 🤝 (decidido el 2026-10-01): publicaciones para X (Twitter) y newsletters (solo LinkedIn), y el resumen semanal *Community Highlights*. Además, **solo Discord**: el brief menciona Slack, pero no entra.

**Por qué todo empieza en la ingesta.** La ingesta es la puerta de entrada: saca los mensajes de Discord y se los entrega al resto del sistema. **Si un dato no entra por esa puerta, ni la IA ni el dashboard pueden verlo nunca.** Por eso el contrato tiene que incluir todo lo que necesitan los activos.

El detalle está en [PROJECT_BRIEF.md](PROJECT_BRIEF.md).

---

## 3. Glosario

> Qué vas a entender aquí: cada término técnico y de negocio que aparece en el documento, con un ejemplo del proyecto. Vuelve a esta sección cada vez que una palabra no te resulte clara.

### Negocio

| Término | Qué significa | Ejemplo |
|---|---|---|
| **Brief** | El enunciado del cliente: qué problema tiene y qué espera de la solución | El texto de la hackatón |
| **MVP** | Producto mínimo viable: la primera versión, con lo indispensable | Los 5 activos de la sección 2 |
| **Activo** | Algo que produce el sistema y que el negocio puede usar | Un post de LinkedIn |
| **Community Manager (CM)** | La persona que cuida la comunidad: modera, anima y detecta problemas | Quien recibe la alerta de un alumno en riesgo |
| **Caso de éxito o testimonio** | La historia de un alumno contada con sus propias palabras, útil para marketing | "Me contrataron como QA trainee" |
| **FAQ** | Preguntas frecuentes con su respuesta | "¿Cómo instalo Python en Windows?" |
| **Deserción** | Que un alumno deje de participar o abandone | Un alumno activo que deja de escribir |
| **Aprobación humana** | Una persona revisa lo que generó la IA antes de publicarlo | Marketing edita el post y lo aprueba |

### Discord

| Término | Qué significa | Ejemplo |
|---|---|---|
| **Servidor** | El espacio de una comunidad | `InsightEdu Lab - Pruebas` |
| **Canal** | Una sala de conversación dentro del servidor | `#dudas`, `#logros` |
| **Mensaje** | Lo que alguien publica en un canal: texto, imágenes o ambos | "como instalo pyhton en windows??" |
| **Respuesta** | Un mensaje que cita a otro con la opción "Responder" | "Que necesitas @Ana Pérez?" |
| **Reacción** | Un emoji que se pone **sobre** un mensaje, sin escribir uno nuevo | 🎉 sobre "me contrataron" |
| **Mención** | Llamar a alguien con `@` para que reciba un aviso | `@InsightEdu Ingesta` |
| **Rol** | Una etiqueta que agrupa personas y define sus permisos | El rol `Mentor` |
| **Fijar** | Destacar un mensaje en el canal | Fijar la respuesta oficial de un mentor |
| **Hilo** | Una subconversación que nace de un mensaje | Un hilo "Error con Gson" |
| **Foro** | Un tipo de canal donde cada publicación es un hilo, con etiquetas | Un canal de dudas organizado por temas |
| **Aviso del sistema** | Un mensaje que genera Discord, no una persona | "Ana se unió al servidor" |
| **Bot** | Un programa con cuenta propia en Discord | `InsightEdu Ingesta` |
| **Token** | La contraseña del bot. Nunca se comparte ni se sube al repositorio | — |
| **Webhook** | Una dirección secreta que publica mensajes en un canal con el nombre que uno elija. La usamos para simular alumnos | `Simulador alumnos` |

### Datos e integración

| Término | Qué significa | Ejemplo |
|---|---|---|
| **JSON** | Un formato de texto para intercambiar datos, con pares `"campo": valor` | `{"canal": "dudas"}` |
| **Campo** | Cada dato dentro de un JSON | `fecha` |
| **`null`** | "Sin valor" | `"respondeA": null`: no responde a nadie |
| **Lista** | Varios valores dentro de un campo; puede estar vacía (`[]`) | `"reacciones": [🎉, 👏]` |
| **Objeto** | Un grupo de campos dentro de otro campo | `"autor": {"id": …, "rol": …}` |
| **ID** | Un código único que identifica algo | El ID de un mensaje |
| **Snowflake** | El tipo de ID que usa Discord. 📘 *"Garantizados únicos en todo Discord"*. Crece con el tiempo, así que ordenar por ID es ordenar por fecha | `"1554205178671009863"` |
| **UTC e ISO 8601** | La hora universal y un formato estándar para escribir fechas | `"2026-09-28T18:56:30.331Z"` (la `Z` significa UTC) |
| **API** | Un programa que recibe pedidos de otros programas y les responde | La API de Discord; la API Java de backend |
| **Endpoint** | Una "puerta" específica de una API, donde se entrega un tipo de pedido | La puerta de backend que recibe los mensajes |
| **Ruta** | La dirección de esa puerta | `/api/v1/community/process` |
| **GET y POST** | Dos tipos de pedido: GET es "dame datos"; POST es "te envío datos para que los guardes" | Pedimos los mensajes a Discord con GET y se los enviamos a backend con POST |
| **Petición y respuesta** | Lo que se manda y lo que contestan | Mandamos un lote; backend contesta "exitoso, recibí 38 mensajes" |
| **Error 400** | La respuesta "tu pedido está mal armado". No se guarda nada | Un campo obligatorio vacío |
| **REST** | La forma de hablar con una API mediante pedidos: uno pregunta y la API responde | `extract.py` pide el historial de un canal |
| **Gateway** | La "línea directa" de Discord: un bot conectado recibe un aviso al instante cada vez que pasa algo | El bot en vivo se entera de una duda nueva |
| **WebSocket** | Una conexión que **queda abierta**, como una llamada telefónica que no se corta. El Gateway funciona así | — |
| **Intent** | La lista de avisos que un bot le pide al Gateway | "Avísame de los mensajes nuevos" |

### Backend (Java)

| Término | Qué significa | Ejemplo |
|---|---|---|
| **DTO** | En Java, la clase que define qué forma debe tener el JSON que entra por una puerta. Es la versión de backend de un contrato | `InteractionInputDto` |
| **Entidad y tabla** | Cómo se guardan los datos en la base: cada entidad es una tabla | La entidad `Interaction` es la tabla `interacciones_originales` |
| **PostgreSQL** | La base de datos que usa backend | — |
| **Enum** | Una lista cerrada de valores permitidos | `TipoAutor`: solo `HUMANO` o `AI` |
| **`@NotBlank`, `@NotNull`** | Reglas de Java: "este campo es obligatorio" | `textoMensaje` tiene `@NotBlank` |
| **`Instant`** | Un tipo de fecha de Java que no pierde la zona horaria | `timestampMensaje` |
| **jsonb** | Un tipo de columna de PostgreSQL que guarda un JSON completo tal como llega y permite buscar dentro de él | La "caja" de la opción C |
| **Upsert** | "Actualizar o insertar": si el registro ya existe, se actualiza; si no, se crea | Evitar los duplicados |

### Ingesta

| Término | Qué significa | Ejemplo |
|---|---|---|
| **Ingesta** | La parte del sistema que saca los datos de Discord y se los entrega al resto | Este módulo |
| **Contrato** | El formato acordado en que entra cada mensaje al sistema. Funciona como un formulario: todos lo llenan igual | La sección 8 |
| **Lote** | El "sobre" que lleva uno o muchos mensajes en un envío | Un lote con 38 mensajes |
| **Modo** | Si el lote viene del análisis por lotes (`historial`) o del bot en vivo (`tiempoReal`) | `"modo": "tiempoReal"` |
| **Extracción y transformación** | Sacar los mensajes de Discord, y convertirlos al formato del contrato | `extract.py` y la futura transformación |
| **Marcador** | El ID del último mensaje enviado, para pedir solo los nuevos la próxima vez | "Dame los mensajes posteriores al 1554…" |
| **Simulación** | Mensajes publicados por nosotros para imitar a alumnos | Ana Pérez, Camila Rojas y Luis Gómez |

---

## 4. Discord para quien nunca lo usó

> Qué vas a entender aquí: cómo es nuestro servidor de pruebas, cómo simulamos a los alumnos y qué descubrimos de los datos.

**Nuestro servidor de pruebas** 🧪. Se llama `InsightEdu Lab - Pruebas` y tiene dos canales que importan:
- `#dudas`, donde los alumnos preguntan;
- `#logros`, donde cuentan sus avances.

Un bot propio, `InsightEdu Ingesta`, tiene permiso para leer ambos canales.

**Cómo simulamos a los alumnos.** No hay alumnos reales. Crear cuentas falsas y automatizarlas viola los términos de Discord; un **webhook**, en cambio, permite publicar con un nombre distinto en cada mensaje. Con un webhook por canal publicamos las conversaciones de **7 alumnos y 1 mentor** ficticios. Las escribimos con errores reales a propósito: ortografía ("pyhton"), preguntas partidas en varios mensajes, código y enlaces.

**Las pruebas con una cuenta real.** Hay cosas que un webhook no puede hacer, como responder o reaccionar. Por eso una persona del equipo usó su propia cuenta para:
- responder a una duda;
- reaccionar 🎉 a un logro;
- editar mensajes;
- enviar una captura sin texto;
- mencionar al bot;
- fijar un mensaje.

**Resultado:** 38 mensajes, 32 simulados y 6 reales.

**Cinco descubrimientos que dieron forma al contrato** 🧪:

| Descubrimiento | Por qué importa | Cómo lo resolvió el contrato |
|---|---|---|
| Discord le pone a todos los mensajes de un webhook **el mismo ID de autor** | Todos los alumnos simulados de un canal parecerían una sola persona | El ID del autor se arma con su nombre: `sim-ana-perez` (decisión 1) |
| Hay mensajes **sin texto**: una imagen sola, o un aviso de "X fijó un mensaje" | La IA recibiría texto vacío | Se marcan con `tieneTexto` y `tipo` |
| Al escribir `@InsightEdu Ingesta`, Discord sugiere **el bot y su rol** con el mismo nombre | El bot no se enteraría de que lo llamaron | `mencionaAlBot` cubre las dos formas (decisión 5) |
| 📘 **Las direcciones de las imágenes vencen** (en la prueba, a las 24 horas) | Una imagen guardada hoy, mañana no abre | Se informa cuándo vence (decisión 3) |
| Los **avisos del sistema** vienen mezclados con los mensajes de los alumnos | Se contarían como si los hubiera escrito un alumno | Se marcan como `avisoSistema` (decisión 4) |

El detalle está en [DISCORD_DATA_GUIDE.md](DISCORD_DATA_GUIDE.md).

---

## 5. Los casos de la comunidad

> Qué vas a entender aquí: qué significan los códigos como A3, A4 o B5 que aparecen en el documento.

Antes de diseñar el contrato hicimos un **catálogo** con las situaciones que ocurren en una comunidad educativa y que le importan al negocio. Cada situación tiene un código:
- **la letra** es la familia: A = dudas, B = logros, C = proyectos, D = opiniones sobre los cursos, E = salud de la comunidad, F = ciclo de vida del miembro, G = interacciones, H = la institución, I = ruido;
- **el número** es el caso dentro de la familia.

Estos son **todos los casos que se mencionan en este documento**. En el resto del texto, cada código va acompañado de su nombre.

| Código | Caso | Ejemplo | Para qué activo sirve |
|---|---|---|---|
| **A1** | Duda nueva | "como instalo pyhton en windows??" | Bot, FAQ, dashboard |
| **A3** | Duda con una captura del error | Una imagen y, después, "me sale esto" | Bot, FAQ |
| **A4** | La misma duda, preguntada con otras palabras | "cómo instalo Python", preguntado 3 veces | FAQ, dashboard |
| **A5** | Duda sin responder | "alguien? 😅" | Alerta del dashboard, bot |
| **A6** | Duda resuelta | "graciasss era eso 🙏", o una edición con "RESUELTO" | FAQ (la mejor materia prima) |
| **A7** | Un compañero responde | "te falta el punto y coma…" | FAQ, casos de éxito |
| **A8** | Respuesta oficial de un mentor | Un mentor responde y fija la respuesta | FAQ |
| **A10** | Se califica la respuesta del bot | El alumno reacciona 👎 a lo que dijo el bot | Bot, dashboard |
| **B1** | Empleo: entrevista o contratación | "me contrataron!!!!! después de 6 meses…", con 🎉 | LinkedIn, casos de éxito |
| **B2** | Curso terminado o certificado | "Terminé Lógica de Programación", con la foto del certificado | LinkedIn, casos de éxito |
| **B5** | Historia de superación | Luis: "pienso dejar el curso" y, días después, "hoy entendí recursividad" | Casos de éxito, LinkedIn |
| **B7** | Felicitaciones de otros | "Felicidades Camila…" | Dashboard, LinkedIn |
| **B8** | Logro compartido desde otra red | El alumno comparte su post de LinkedIn | LinkedIn, casos de éxito |
| **C1** | Entrega o demo de un proyecto | "Acá el repo: https://github.com/…" | Casos de éxito, LinkedIn |
| **C3** | Pedido de revisión de código | "¿me revisan el código?", con un bloque de código | FAQ, dashboard |
| **D4** | Encuesta | "¿qué tema repasamos el jueves?" | Dashboard, FAQ |
| **E3** | Un miembro deja de participar | Un alumno activo lleva 14 días sin escribir | Alerta del dashboard |
| **G1** | Reacción a un mensaje | 🎉 ×12 en un logro | Todos |
| **G2** | Mención a un miembro, a un rol o al bot | "@InsightEdu Ingesta ayuda" | Bot, dashboard |
| **G3** | Hilo o publicación en un foro | Un hilo "Error con Gson" con 8 mensajes | FAQ, bot |
| **G4** | Mensaje fijado | El mentor fija una respuesta | FAQ |
| **I1** | Fuera de tema, memes o stickers | Un GIF o un sticker | Dashboard (solo para medir el clima) |
| **I2** | Otros bots o spam | Mensajes automáticos de otra herramienta | Ninguno: se filtra |

El catálogo completo está en [EVENT_CATALOG.md](EVENT_CATALOG.md).

---

## 6. El viaje de un mensaje

> Qué vas a entender aquí: qué piezas tiene el sistema, quién habla con quién y en qué orden.

```
 DISCORD            INGESTA (Python)          BACKEND (API Java)              IA (Python)        PANEL            OCI
 ───────            ────────────────          ──────────────────              ───────────        ─────            ───
 mensajes ───────▶  1. extrae los mensajes
                    2. los transforma
                       al contrato
                    3. los envía (POST) ───▶  4. revisa el lote
                                                 ¿está bien armado?
                                                   no → error 400, no guarda nada
                                                   sí → lo guarda en su base
                       ◀──────── recibo ───   5. "exitoso, recibí 38 mensajes"
                                              6. le pasa los mensajes ────▶  7. analiza y
                                                                                genera
                                              8. recibe los borradores ◀──     borradores
                                              9. los muestra ───────────────────────────▶  10. una persona
                                                                                               aprueba
                                              11. guarda los aprobados ─────────────────────────────────▶  activos
```

| Pieza | Qué hace | Quién la construye |
|---|---|---|
| **Ingesta** | Es lo **único** que habla con Discord: saca los mensajes, los transforma y los envía | Ingesta |
| **Contrato** | El formato común en que viajan los mensajes | Ingesta |
| **API Java + base de datos** | Recibe, guarda y coordina: es el registro oficial | Backend |
| **IA** | Clasifica los mensajes y genera los activos | IA |
| **Panel** | La aprobación humana y el dashboard | Frontend o data |
| **OCI Object Storage** | Guarda los activos aprobados 📄 (obligatorio según el brief) | Por definir |

**Dos ideas clave:**
1. **La API Java nunca le pide nada a Discord.** Espera en su puerta y guarda lo que le llega. Quien va a buscar los mensajes y quien los envía es la ingesta.
2. **La IA solo recibe lo que backend guarda en el paso 4.** Si un dato no entra por la puerta, la IA nunca lo ve.

---

## 7. Dos modos: por lotes y en vivo

> Qué vas a entender aquí: las dos formas en que llegan los mensajes, cómo funciona un bot de Discord y por qué el contrato sirve igual para ambas.

### La diferencia

| | Por lotes | En vivo |
|---|---|---|
| **Para qué** | Analizar semanas de conversación: posts, casos de éxito, FAQ y dashboard | Responder la duda que acaba de llegar |
| **Cómo llegan los mensajes** | **Nosotros vamos a buscarlos** cuando queremos: "dame el historial" (REST) | **Discord nos avisa** en el momento en que alguien escribe (Gateway) |
| **Cada cuánto** | Por ejemplo, cada hora | En segundos |
| **Mensajes por lote** | Muchos | Uno |
| **Estado** | Funciona hoy (`extract.py`) | Se construye en la rama siguiente, después del 10/10 🤝 |

```
FLUJO A · POR LOTES (hoy)
 Discord ──"dame el historial"──▶ extract.py ──▶ transformar ──▶ lote con 38 mensajes ──POST──┐
           (REST, cada hora)                     al contrato     modo: "historial"            │
                                                                                              ▼
                                                                         puerta de backend /process
                                                                                              ▲
FLUJO B · EN VIVO (rama siguiente)                                                            │
 Discord ──"llegó un mensaje"──▶ bot ──▶ transformar ──▶ lote con 1 mensaje ──POST────────────┘
           (Gateway, al instante) │      (la MISMA       modo: "tiempoReal"
                                  │       función)
                                  └──▶ pide una respuesta a la IA ──▶ responde en Discord
                                       (propuesta: cómo se conecta con la IA está por definir)
```

### Cómo funciona un bot en vivo 📘

Hoy, nuestro bot `InsightEdu Ingesta` solo presta su identidad (el token) para que `extract.py` pida el historial: no está conectado. En vivo, un programa nuestro abre una conexión permanente con Discord:

| Paso | Qué pasa |
|---|---|
| 1. Conectarse | El programa abre un WebSocket con Discord, una conexión que **queda abierta** |
| 2. Latido | Cada pocos segundos le avisa a Discord "sigo aquí" (*heartbeat*). Si deja de hacerlo, Discord corta la conexión |
| 3. Identificarse | Envía el token y los *intents*. Para los mensajes necesita `GUILD_MESSAGES` y `MESSAGE_CONTENT`; este último ya está activado en nuestro bot |
| 4. Recibir | Cada vez que alguien escribe, Discord le envía un aviso `MESSAGE_CREATE` con el mensaje. **Cada mensaje llega una sola vez**, en el momento en que se escribe |

**Qué pasa si el bot se desconecta:**
- 📘 Si la desconexión es corta, el bot puede **retomar** la sesión y Discord le reenvía en orden los avisos que se perdió.
- 📘 Si tarda demasiado, Discord responde "sesión inválida": el bot empieza de cero y **los avisos de ese rato se pierden**.
- 🔎 Si el bot está apagado, por ejemplo porque se reinició el servidor donde corre, los mensajes de ese tiempo nunca le llegan.

**Por eso los lotes siguen haciendo falta aunque exista el bot:** rescatan lo que el bot se perdió (sección 9).

### El contrato es el mismo en los dos modos

```
POR LOTES                                     EN VIVO
{                                             {
  "versionContrato": "1.0",    ← igual          "versionContrato": "1.0",
  "loteId": "3f2b…",                            "loteId": "9a1c…",
  "modo": "historial",         ← cambia →       "modo": "tiempoReal",
  "fuente": "discord",                          "fuente": "discord",
  "mensajes": [ 38 mensajes ]  ← cambia →       "mensajes": [ 1 mensaje ]
}                                             }
```

- **`versionContrato` no cambia con el modo.** Es la edición del formulario, no la forma de llenarlo. Solo cambia si cambiamos el formato, por ejemplo al agregar un campo.
- Cada mensaje de adentro tiene **los mismos 23 campos** en los dos modos.

### Qué cambia de un modo al otro, pieza por pieza

| Pieza | Por lotes | En vivo | ¿Cambia? |
|---|---|---|---|
| Cómo llega el mensaje | `extract.py` lo pide | El bot lo recibe | **Sí:** el bot es un programa nuevo |
| Transformación al contrato | Una función | La misma función | No |
| Formato y `versionContrato` | `"1.0"` | `"1.0"` | No |
| Roles del autor | 📘 Una petición a Discord por cada autor | 📘 Vienen dentro del mensaje | Solo cómo se obtienen |
| Dirección de las imágenes | 📘 Válida al extraer | 📘 Válida al llegar | No |
| Puerta de backend | `POST /process` | La misma | No |
| Duplicados | Lotes que se superponen | El mismo mensaje llega en vivo y después en un lote | Sección 9 |
| Responder en Discord | No aplica | El bot contesta | **Sí:** nuevo |
| Dónde corre | En una PC, cuando se ejecuta | 🔎 Encendido las 24 horas en un servidor | **Sí:** hay que decidir dónde alojarlo |

**Para backend, el modo en vivo significa tres cosas:**
1. Recibirán lotes de 1 mensaje, más seguido, por la misma puerta y con el mismo formato.
2. Necesitan evitar los duplicados (sección 9).
3. Si cada lote crea un paquete de resultados, habrá un paquete por mensaje (pregunta 4 de la sección 12).

---

## 8. El contrato v1 explicado

> Qué vas a entender aquí: qué es el contrato, sus reglas, para qué sirve cada campo y por qué tomamos cada decisión.

### Qué es un contrato

Es un **formulario** que todos llenan igual: la ingesta lo completa con cada mensaje de Discord y los demás equipos lo leen sabiendo exactamente qué van a encontrar. Así, cada equipo trabaja sin depender de cómo están hechas las otras piezas por dentro.

**Cómo lo diseñamos:** a partir del catálogo de casos (sección 5). **Cada campo existe porque algún caso del MVP lo necesita;** si ningún caso lo pide, no entra. Lo diseñamos sin mirar el código de backend ni el de la IA, para no copiar decisiones ajenas, y recién después lo comparamos (sección 10).

### Sus reglas

1. **1 mensaje de Discord = 1 registro.** No se agrupan mensajes.
2. **El texto original no se modifica.** Se envía tal cual, con sus errores; la limpieza queda para después.
3. **Siempre van todos los campos.** Si Discord no manda un dato, el campo va igual con un valor explícito: `[]`, `null` o `false`. Así nadie tiene que adivinar si un campo "falta".
4. **Los IDs van como texto.** Son números tan grandes que algunos lenguajes, como JavaScript, los redondean.
5. **Las fechas van en UTC**, con el formato `2026-09-28T18:56:30.331Z`.
6. **Los nombres de campo van en `camelCase`:** `textoOriginal`, `respondeA`.
7. **Solo entra lo que algún caso del MVP necesita.** Lo demás queda guardado en los datos originales de Discord.
8. **El contrato tiene número de versión.** Si cambia el formato, cambia la versión.

### El lote: 6 campos

| Campo | Qué es | Para qué sirve | Ejemplo |
|---|---|---|---|
| `versionContrato` | La versión del formato | Saber qué formulario se llenó | `"1.0"` |
| `loteId` | El ID del envío | Rastrear cada envío y detectar los reenvíos | `"3f2b8c1e-…"` |
| `fuente` | La plataforma de origen | Sumar otras plataformas en el futuro sin cambiar el formato | `"discord"` |
| `modo` | Por lotes o en vivo | Distinguir lo que llegó del bot | `"historial"` |
| `servidorId` | El servidor de Discord | Saber de qué comunidad viene | `"1554157903701741700"` |
| `generadoEn` | Cuándo se armó el lote | Auditoría | `"2026-09-29T15:00:00.000Z"` |

Además, `mensajes` es la lista de mensajes del lote.

### Cada mensaje: 23 campos

| Campo | Qué es | Para qué sirve (caso) | Ejemplo |
|---|---|---|---|
| `id` | El ID del mensaje en Discord | Identificar el mensaje y evitar duplicados | `"1554205178671009863"` |
| `canal` | El canal (ID y nombre) | Saber si es una duda o un logro (A1, B1) | `{"id": "…", "nombre": "dudas"}` |
| `hilo` | El hilo, si lo hay | Foros (G3). **En el MVP siempre es `null`** | `null` |
| `fecha` | Cuándo se escribió | Deserción (E3) y tendencias | `"2026-09-28T18:56:30.331Z"` |
| `tipo` | Mensaje, respuesta o aviso del sistema | Separar a las personas de los avisos (G4, I1) | `"respuesta"` |
| `tipoDiscord` | El número original de Discord | Trazabilidad | `19` |
| `esSimulado` | Si lo publicó nuestra simulación | Separar los datos de prueba de los reales | `true` |
| `autor` | Quién lo escribió (6 datos, ver abajo) | Seguir a cada persona en el tiempo (B5) | — |
| `textoOriginal` | El texto, sin cambios | Citas para LinkedIn, dudas para la FAQ (A1, B1) | `"como instalo pyhton…"` |
| `tieneTexto` | Si trae texto | Reconocer una captura sin texto (A3) | `false` |
| `tieneBloqueCodigo` | Si trae código | Dudas de código (A1, C3) | `true` |
| `enlaces` | Los links, con su dominio | Proyectos en GitHub (C1), posts de LinkedIn (B8) | `[{"url": "…", "dominio": "github.com"}]` |
| `menciones` | A quién menciona | Felicitaciones (B7) | `{"usuarios": […], "roles": […], "todos": false}` |
| `mencionaAlBot` | Si llamaron al bot | Que el bot responda (G2) | `true` |
| `respondeA` | A qué mensaje responde | Duda resuelta (A6), duda sin responder (A5), compañero que ayuda (A7) | `"1554205273621667853"` |
| `adjuntos` | Los archivos | Captura del error (A3), certificado (B2) | `[{"nombre": "captura.jpg", …}]` |
| `reacciones` | Los emojis y su cantidad | Medir un logro (B1, G1), calificar al bot (A10) | `[{"emoji": "🎉", "cantidad": 1}]` |
| `fijado` | Si está fijado | Respuesta oficial (A8, G4) | `true` |
| `editado` | Si se editó | Duda editada con "RESUELTO" (A6) | `true` |
| `editadoEn` | Cuándo se editó | Ídem | `"2026-09-28T21:25:19.495Z"` |
| `stickers` | Los stickers | Ruido (I1) | `["wave"]` |
| `vistasPrevias` | La vista previa de un link | Post de LinkedIn compartido (B8) | título del post |
| `encuesta` | Una encuesta | Encuestas (D4) | `null` |

**El autor (`autor`) tiene 6 datos:**
- `id`: la identidad estable. Si es una persona real, su ID de Discord; si es simulada, `sim-` más su nombre.
- `idDiscord`: el ID original.
- `nombreUsuario` y `nombreVisible`.
- `tipo`: `persona`, `botPropio` (nuestro bot) u `otroBot`.
- `rol`: `miembro`, `mentor` o `staff`.

### Las 7 decisiones 🤝 (aprobadas el 2026-10-01)

**El criterio:** el contrato tiene que funcionar con **una institución real**, no solo con nuestra simulación.

| # | Pregunta | Qué decidimos | Por qué |
|---|---|---|---|
| 1 | ¿Cómo identificamos a un alumno simulado? | Con su nombre: `sim-ana-perez` | Discord le pone a todos los mensajes de un webhook el mismo ID. Con ese ID, todos los alumnos de un canal serían una sola persona |
| 2 | ¿Cómo sabemos quién es mentor? | Con **sus roles reales de Discord**. Una configuración dice qué rol significa "mentor" y cuál "staff". Para los simulados, que no tienen roles, hay una lista de respaldo | La institución ya administra los roles: si llega un mentor nuevo, no hay que tocar el sistema |
| 3 | ¿Enviamos la dirección de las imágenes? | Sí, junto con la fecha en que vence | 📘 Llega válida tanto en vivo como por lotes; lo que vence es la copia guardada. Con el ID del mensaje se puede pedir una dirección nueva |
| 4 | ¿Filtramos los avisos del sistema? | No: los enviamos marcados como `avisoSistema` | La ingesta no decide qué le sirve a cada equipo; descartarlos es fácil para quien no los quiera |
| 5 | ¿Cuándo "llaman" al bot? | Cuando mencionan al bot **o a su rol** | Lo descubrimos en la prueba real: Discord sugiere los dos con el mismo nombre |
| 6 | ¿Qué hacemos con las encuestas y las vistas previas, que todavía no probamos? | Se definen según la documentación oficial | Quitarlas y agregarlas después cambiaría la versión del contrato |
| 7 | ¿Qué hacemos con los hilos y foros? | El campo `hilo` existe desde la v1, pero va en `null` en el MVP | 📄 El brief pide "debates en foros". Agregarlo después cambiaría la versión que backend ya programó |

El detalle de cada campo está en [CONTRACT.md](CONTRACT.md).

---

## 9. Los duplicados

> Qué vas a entender aquí: por qué un mismo mensaje puede llegar más de una vez y cómo evitamos guardarlo dos veces.

### Por qué un mensaje puede llegar dos veces

| Situación | Ejemplo |
|---|---|
| **1. Lotes que se superponen** | Hoy `extract.py` descarga **todo** el historial cada vez. El lote de las 12 trae otra vez los mensajes de las 11 |
| **2. En vivo y después en un lote** | El bot envía un mensaje a las 10:05 y el lote de las 11 lo vuelve a traer. **Pasa a propósito:** el lote existe para rescatar lo que el bot se perdió |
| **3. Un reenvío** | Enviamos un lote, backend lo guarda, pero se corta internet antes de que llegue el recibo. Como no sabemos si llegó, lo reenviamos |
| **4. El mismo mensaje con datos nuevos** | El logro de Camila llega con 0 reacciones y, una hora después, con 🎉 ×5. Es el mismo mensaje, pero más actualizado |

### `loteId` y el ID del mensaje: dos números para dos cosas distintas

| | `loteId` | `id` del mensaje (`discordId` en backend) |
|---|---|---|
| **Qué identifica** | Un **envío** | Un **mensaje** |
| **Comparación** | El número de guía de una encomienda | El documento de identidad del mensaje |
| **Quién lo crea** | La ingesta, uno nuevo en cada envío | Discord, cuando se escribe el mensaje |
| **¿Puede repetirse?** | Solo si se reenvía **el mismo** envío (situación 3) | 📘 Es único en todo Discord: el mismo mensaje tiene siempre el mismo ID, sin importar en cuántos lotes viaje |
| **Qué detecta** | El reenvío de un envío completo | El mismo mensaje en lotes distintos (situaciones 1, 2 y 4) |

**Por qué el `loteId` no alcanza.** El lote de las 11 (`loteId` A) trae los mensajes 1, 2 y 3; el de las 12 (`loteId` B) trae el 3 y el 4. El mensaje 3 llegó dos veces, aunque A y B son números distintos. Solo el ID del mensaje lo detecta.

### Dos protecciones, una de cada lado

**Protección 1 · La ingesta no envía de más: el marcador.** 📘 Discord permite pedir "dame los mensajes **posteriores** a este ID" (parámetro `after`). Después de cada envío, la ingesta guarda el ID del último mensaje enviado de cada canal:
```
11:00  "dame todo"                     → mensajes 1, 2, 3   → marcador = 3
12:00  "dame los posteriores al 3"     → mensajes 4, 5      → marcador = 5
13:00  "dame los posteriores al 5"     → (nada nuevo)
```
🔎 Para captar las reacciones que llegan después (situación 4), conviene que cada lote **vuelva a leer los últimos días** y no solo lo posterior al marcador. Cuántos días es una decisión interna de la ingesta (pendiente P6 en [SCOPE.md](SCOPE.md)).

**Protección 2 · Backend no guarda dos veces: el *upsert*.** Si llega un mensaje cuyo ID ya existe, **se actualiza con la versión nueva**; si no existe, se crea. No conviene simplemente ignorar el repetido, porque a veces trae datos nuevos.

### Un día con todas las situaciones
(Los IDs están acortados para que se lean fácil.)
```
10:05  Camila escribe "me contrataron!!!" (mensaje 222)
         EN VIVO → el bot lo recibe → lote L1 [222, sin reacciones]
         backend: 222 no existe → lo CREA
10:40  cinco compañeros reaccionan 🎉
11:00  LOTE DE LA HORA → vuelve a leer los últimos días → lote L2 [222 con 🎉×5, …]
         backend: 222 ya existe → lo ACTUALIZA (ahora con 🎉×5), no crea otra fila
11:20  se apaga el servidor donde corre el bot
11:30  Luis escribe una duda (mensaje 333) → el bot está apagado → no llega en vivo
12:00  LOTE DE LA HORA → trae el 333
         backend: 333 no existe → lo CREA ✅ (el lote rescató lo que el bot perdió)
12:00  se corta internet justo cuando backend respondía → no sabemos si llegó
         → reenviamos el mismo lote L3
         backend: L3 ya recibido y 333 ya existe → no duplica nada
```

**¿Cambia el contrato?** No. Ya tiene el ID de cada mensaje y el `loteId` de cada envío. Lo que hace falta es que **la ingesta use el marcador** y que **backend haga el *upsert***.

---

## 10. Comparación con backend

> Qué vas a entender aquí: qué construyó backend para recibir los mensajes, en qué coincide con el contrato y qué le falta, y cuánto cuesta cada diferencia.

### Lo que construyó backend 💻

Backend avanzó mucho y con buenas decisiones:
- **La puerta ya existe:** `POST /api/v1/community/process`.
- **Valida lo que entra** y responde con un **recibo** claro: `status`, `mensaje`, `loteId`, `totalMensajesRecibidos` y `recibidoEn`.
- **Usa `Instant` para las fechas,** que no pierde la zona horaria. Eso resuelve un pendiente nuestro (P4).
- **Tiene base de datos** (PostgreSQL con Docker), la subida de reportes a OCI y métodos de búsqueda ya preparados.
- **Está empezando la conexión con la IA** (`NlpDataClient`). Hoy está vacía, con el comentario *"A la espera de confirmación para continuar"*. Por eso **es el mejor momento para acordar qué datos le llegan a la IA**.

### Qué recibe hoy su puerta 💻

El lote (`CommunityProcessRequestDto`) trae tres campos obligatorios:
- `loteId`;
- `tipoServidor`;
- `interacciones`, que no puede venir vacía.

Cada mensaje (`InteractionInputDto`, resumido):
```java
public class InteractionInputDto {
    @NotBlank private String discordId;        // obligatorio
    private String channelId;
    @NotBlank private String authorId;         // obligatorio
    private String authorUsername;
    private String autorNombre;
    private String autorRol;
    @NotBlank private String textoMensaje;     // obligatorio  ← hallazgo 1
    @NotNull  private TipoAutor tipoAutor;     // obligatorio: HUMANO o AI  ← hallazgo 4
    private ClasificacionSentimiento clasificacionSentimiento;   // ← hallazgo 5
    private Instant timestampMensaje;
}
```

### La comparación campo por campo

Cómo leer las dos columnas de estado:
- **Su DTO:** ✅ existe (aunque con otro nombre), ⚠️ existe pero distinto, ❌ no existe.
- **Esfuerzo:** 🟢 barato, unas 5 líneas; 🔴 caro, hace falta una tabla nueva; "—" no hay que cambiar nada.

**El lote**

| Contrato | Su DTO | Significado | Caso afectado | Por qué afecta | Ejemplo | Esfuerzo |
|---|---|---|---|---|---|---|
| `versionContrato` | ❌ | La versión del formato | Todos | Si el formato cambia, backend no sabe qué versión recibió | `"1.0"` | 🟢 |
| `loteId` | ✅ `loteId` | El ID del envío | Reenvíos | — | `"3f2b…"` | — |
| `fuente` | ⚠️ `tipoServidor` | La plataforma de origen | — | Su ejemplo mezcla la plataforma con el nombre del servidor | `"discord"` vs `"Discord_ONE_G10"` | — (acordar el valor) |
| `modo` | ❌ | Por lotes o en vivo | Calificar al bot (A10) | No se distingue lo que llegó del bot | `"tiempoReal"` | 🟢 |
| `servidorId` | ❌ | El servidor de Discord | — | Poco: en el MVP hay un solo servidor | `"1554157903…"` | 🟢 |
| `generadoEn` | ❌ | Cuándo se armó el lote | Auditoría | Poco | una fecha | 🟢 |
| `mensajes` | ✅ `interacciones` | La lista de mensajes | — | Solo cambia el nombre | — | — |

**Cada mensaje**

| Contrato | Su DTO | Significado | Caso afectado | Por qué afecta | Ejemplo | Esfuerzo |
|---|---|---|---|---|---|---|
| `id` | ✅ `discordId` | El ID del mensaje | Todos | — | `"1554205178…"` | — |
| `canal` | ⚠️ `channelId` | El canal | Dudas y logros (A1, B1) | Solo guardan el número: el dashboard mostraría `1554158212…` en lugar de "dudas" | `"dudas"` | 🟢 |
| `hilo` | ❌ | El hilo | Foros (G3) | Nada en el MVP: va en `null` | `null` | 🔴 |
| `fecha` | ✅ `timestampMensaje` | Cuándo se escribió | Deserción (E3) | — | `"2026-09-28T18:56Z"` | — |
| `tipo` | ❌ | Mensaje, respuesta o aviso | Fijados (G4), ruido (I1) | "Ana se unió al servidor" se analizaría como si lo hubiera escrito un alumno | `"avisoSistema"` | 🟢 |
| `tipoDiscord` | ❌ | El número original | Trazabilidad | Poco | `19` | 🟢 |
| `esSimulado` | ❌ | Si es de la simulación | Dashboard | Los datos de prueba se mezclan con los reales | `true` | 🟢 |
| `autor.id` | ✅ `authorId` | La identidad estable | Historia de superación (B5) | — | `"sim-ana-perez"` | — |
| `autor.idDiscord` | ❌ | El ID original | Trazabilidad | Poco | `"1554160711…"` | 🟢 |
| `autor.nombreUsuario` | ✅ `authorUsername` | El usuario | — | — | `"Ana Pérez"` | — |
| `autor.nombreVisible` | ✅ `autorNombre` | El nombre que se ve | — | — | `"Ana Pérez"` | — |
| `autor.tipo` | ⚠️ `tipoAutor` | Persona, nuestro bot u otro bot | Calificar al bot (A10), spam (I2) | Su lista solo admite `HUMANO` o `AI` (hallazgo 4) | `"otroBot"` | 🟢 |
| `autor.rol` | ⚠️ `autorRol` | `miembro`, `mentor` o `staff` | Respuesta de un mentor (A8) | Aceptan cualquier texto: "Mentor", "mentor" y "Tutor" contarían como roles distintos | `"mentor"` | — (acordar los valores) |
| `textoOriginal` | ⚠️ `textoMensaje` | El texto | Duda con captura (A3) | **Es obligatorio: un mensaje sin texto hace rechazar el lote entero** (hallazgo 1) | la `captura.jpg` sin texto | 🟢 (borrar 1 línea) |
| `tieneTexto` | ❌ | Si trae texto | A3 | — | `false` | 🟢 |
| `tieneBloqueCodigo` | ❌ | Si trae código | Dudas de código (A1, C3) | La FAQ no distingue las dudas de código | `true` | 🟢 |
| `respondeA` | ❌ | A qué mensaje responde | Duda resuelta (A6), sin responder (A5) | **No se sabe qué duda se resolvió ni cuáles quedaron sin respuesta: es la base de la FAQ y de las alertas** | "graciasss era eso 🙏" responde a Ana | 🟢 |
| `mencionaAlBot` | ❌ | Si llamaron al bot | Mención al bot (G2) | El bot no se entera de que lo llamaron | `true` | 🟢 |
| `fijado` | ❌ | Si está fijado | Respuesta oficial (A8) | — | `true` | 🟢 |
| `editado`, `editadoEn` | ❌ | Si se editó y cuándo | Duda resuelta (A6) | — | `true` | 🟢 |
| `enlaces` | ❌ | Los links | Proyecto en GitHub (C1), post de LinkedIn (B8) | No se detectan proyectos ni posts compartidos | `github.com` | 🔴 |
| `menciones` | ❌ | A quién menciona | Felicitaciones (B7) | — | `@Camila` | 🔴 |
| `adjuntos` | ❌ | Los archivos | Captura (A3), certificado (B2) | La IA no ve la captura ni el certificado | `captura.jpg` | 🔴 |
| `reacciones` | ❌ | Los emojis | Contratación (B1), reacciones (G1) | No se mide que el logro tuvo 🎉 ×12 | `🎉 ×1` | 🔴 |
| `vistasPrevias` | ❌ | La vista previa de un link | Post compartido (B8) | — | el título del post | 🔴 |
| `stickers` | ❌ | Los stickers | Ruido (I1) | Poco | `["wave"]` | 🔴 |
| `encuesta` | ❌ | Una encuesta | Encuestas (D4) | — | — | 🔴 |
| — | `clasificacionSentimiento` | Si el mensaje es positivo o negativo | Dashboard | La calcula la IA, no la ingesta: la ingesta la envía vacía (hallazgo 5) | `null` | — |

### Gravedad y esfuerzo no son lo mismo

Hay que separar:
- **la gravedad:** cuánto pierde el negocio si falta el dato;
- **el esfuerzo:** cuánto le cuesta a backend agregarlo.

**Un campo simple es barato.** Agregar, por ejemplo, `esSimulado` toca 5 archivos, con una línea en cada uno:
```
InteractionInputDto.java     + private Boolean esSimulado;          ← lo que entra por la puerta
Interaction.java             + private Boolean esSimulado;          ← la columna (se crea sola)
CommunityService.java        + .esSimulado(dto.getEsSimulado())     ← copiar de la entrada a la base
InteractionResponseDto.java  + private Boolean esSimulado;          ← lo que devuelven
CommunityController.java     + .esSimulado(i.getEsSimulado())       ← copiar de la base a la respuesta
```

**Una lista es cara.** Una columna guarda **un solo valor**, y un mensaje puede tener 0, 1 o 10 reacciones. Hace falta una tabla nueva enlazada al mensaje, una clase Java nueva, un repositorio nuevo y el código de entrada y de salida: decenas de líneas **por cada lista**, y faltan 8.

**Ejemplos:**

| Dato | Gravedad | Esfuerzo |
|---|---|---|
| `textoMensaje` obligatorio | Alta: se pierde el lote entero | Borrar 1 línea |
| `respondeA` | Alta: sin él no hay FAQ | Bajo |
| `adjuntos`, `reacciones` | Alta | **Alto** ← el problema que resuelve la opción C |

### Los hallazgos

| # | Hallazgo 💻 | Efecto en el negocio | Gravedad |
|---|---|---|---|
| 1 | `textoMensaje` es obligatorio | 🔎 Una captura sin texto (A3) hace que se rechace el lote entero con un error 400. Lo deducimos del código; no lo ejecutamos | Alta |
| 2 | Faltan 12 campos simples y 8 listas u objetos | La FAQ no sabe qué duda se resolvió (A6), los casos de éxito no tienen reacciones (B1), el bot no sabe cuándo lo llaman (G2) | Alta |
| 3 | **No evita duplicados** | Ver abajo | Alta |
| 4 | `TipoAutor` solo admite `HUMANO` o `AI` | Mide otra cosa: si un activo lo escribió la IA o una persona. Un bot de spam (I2) no es ninguna de las dos | Media |
| 5 | `clasificacionSentimiento` viene en la entrada | La ingesta no puede calcularlo. Como es opcional, no hace falta cambiar nada: lo llena la IA después | Baja |
| 6 | Cada lote crea un "paquete de resultados" | En vivo, los lotes son de 1 mensaje: habría un paquete por mensaje | Para conversar |

**Detalle del hallazgo 3: los duplicados.**

| Protección | ¿La tienen? | Detalle 💻 |
|---|---|---|
| Revisar si el mensaje ya existe antes de guardarlo | ❌ | Tienen preparado `findByDiscordId`, pero no se usa |
| Una regla en la base que impida repetir el `discordId` | ❌ | La columna no está marcada como única |
| Revisar si un lote ya llegó | ❌ | Tienen `findByLoteId`, pero no se usa |
| *Upsert* | ❌ | — |

Lo que hace hoy su código al recibir un lote (resumido, de `CommunityService.java`):
```java
for (cada mensaje del lote) {
    Interaction interaction = Interaction.builder()...build();  ← siempre crea una fila nueva
}
PackageResult pkg = PackageResult.builder()...build();          ← siempre crea un paquete nuevo
packageResultRepository.save(pkg);                              ← guarda todo, sin preguntar
```

**El efecto:** si se envían los 38 mensajes a las 11 y otra vez a las 12, quedan **76 filas y 2 paquetes**.
- El dashboard cuenta doble: parece que Ana hizo 2 dudas.
- La FAQ ve una falsa "duda repetida" (A4).
- La IA genera activos duplicados y gasta el doble de tokens, un costo que backend mismo registra (`tokensIn`, `tokensOut`).

**La buena noticia:** tienen las piezas. Los métodos de búsqueda ya existen y solo falta usarlos: unas 10 líneas.

---

## 11. Opciones A, B y C

> Qué vas a entender aquí: tres formas de resolver las diferencias, cuánto le cuesta cada una a cada equipo y cuál recomendamos.

### Opción A · La ingesta se adapta al DTO actual

```
 Ingesta ──▶ solo los 9 campos que backend ya recibe ──▶ backend sin cambios
             (lo demás se pierde)
```
- **Backend:** no cambia nada.
- **Ingesta:** traduce al formato de backend.
- **Problema:** se pierde todo lo marcado con ❌ en la sección 10. La FAQ no tiene `respondeA`, los casos de éxito no tienen reacciones, el bot no sabe cuándo lo llaman, y un mensaje sin texto sigue rechazando el lote.
- **Nuestra opinión:** no la recomendamos, porque deja casos del MVP sin datos.

### Opción B · Backend agrega una columna por cada campo

```
 Ingesta ──▶ contrato completo ──▶ backend con ~30 columnas y 8 tablas nuevas
```
- **Backend:** 12 campos simples (unas 60 líneas) más 8 tablas nuevas (decenas de líneas cada una).
- **Ingesta:** envía el contrato tal cual.
- **Ventaja:** cada dato queda en su propia columna y es fácil de consultar.
- **Problema:** es mucho trabajo, con riesgo para la fecha de entrega.

### Opción C · "Etiqueta + caja" (nuestra recomendación)

Funciona como una encomienda:
- **La etiqueta** de afuera tiene los pocos datos que sirven para buscar rápido: quién, cuándo y en qué canal. Son **los campos de siempre de backend, con sus nombres**: no se renombra nada.
- **La caja** lleva el mensaje completo, con los 23 campos del contrato. Backend la guarda **en una sola columna nueva de tipo jsonb**.

**Lo que enviaría la ingesta:**
```
{
  "loteId": "3f2b…",                          ← ya existe en su DTO
  "tipoServidor": "discord",                  ← ya existe
  "versionContrato": "1.0",                   ← nuevo (cambio 5)
  "modo": "historial",                        ← nuevo (cambio 5)
  "interacciones": [
    {
      "discordId": "1554205178671009863",     ┐
      "channelId": "1554158212742127821",     │
      "authorId": "sim-ana-perez",            │  LA ETIQUETA:
      "authorUsername": "Ana Pérez",          │  sus campos,
      "autorNombre": "Ana Pérez",             │  con SUS nombres
      "autorRol": "miembro",                  │
      "textoMensaje": "como instalo pyhton…", │
      "tipoAutor": "HUMANO",                  │
      "timestampMensaje": "2026-09-28T…Z",    ┘
      "mensajeContrato": { … los 23 campos del contrato … }   ← LA CAJA (cambio 1)
    }
  ]
}
```

**Cómo quedaría su tabla:**
```
tabla interacciones_originales
┌─────────────┬───────────────┬────────────────┬─────┬──────────────────────────────┐
│ discord_id  │ author_id     │ texto_mensaje  │ ... │ mensaje_contrato (jsonb)     │ ← columna nueva
├─────────────┼───────────────┼────────────────┼─────┼──────────────────────────────┤
│ 1554205178… │ sim-ana-perez │ como instalo…  │ ... │ {"respondeA": null,          │
│             │               │                │     │  "reacciones": [], …}        │
└─────────────┴───────────────┴────────────────┴─────┴──────────────────────────────┘
```

**Cómo se llena la etiqueta a partir del contrato:**

| Su campo | Sale de | Nota |
|---|---|---|
| `discordId` | `id` | |
| `channelId` | `canal.id` | |
| `authorId` | `autor.id` | `sim-ana-perez` en los simulados |
| `authorUsername` | `autor.nombreUsuario` | |
| `autorNombre` | `autor.nombreVisible` | |
| `autorRol` | `autor.rol` | `miembro`, `mentor` o `staff` |
| `textoMensaje` | `textoOriginal` | Puede venir vacío (cambio 2) |
| `tipoAutor` | `autor.tipo` | `persona` → `HUMANO`; `botPropio` → `AI` (las respuestas del bot salen de la IA); `otroBot` → `BOT` (cambio 3) |
| `timestampMensaje` | `fecha` | |
| `clasificacionSentimiento` | — | Va vacío: lo llena la IA |

**Lo que cambia backend** (en total, unas 25 a 30 líneas, sin tablas nuevas):

| # | Cambio | Esfuerzo | Por qué |
|---|---|---|---|
| 1 | Agregar `mensajeContrato` (la caja) como columna jsonb | Unas 5 líneas. 🔎 Spring Boot 3 trae Hibernate 6, que soporta columnas JSON; a confirmar por backend | Para que nada se pierda y la IA reciba el mensaje completo |
| 2 | Quitar la obligación de texto en `textoMensaje` | Borrar 1 línea | Hoy un mensaje con solo una captura hace rechazar el lote entero |
| 3 | Agregar `BOT` a `TipoAutor` | 1 línea | Para los bots que no son ni personas ni nuestra IA |
| 4 | *Upsert* por `discordId`: si existe, actualizarlo; si no, crearlo. Y marcar la columna como única | Unas 10 líneas | Evitar los duplicados (sección 9) |
| 5 | Agregar `versionContrato` y `modo` al lote | Unas 10 líneas | Saber qué versión del formato llegó y si vino del bot o del análisis |

**Lo que cambia la ingesta:**
- El sobre y la etiqueta usan los nombres de backend. La transformación todavía no está programada, así que no hay que rehacer nada.
- `servidorId` y `generadoEn` se siguen enviando. 🔎 Si backend no los usa, Spring los ignora sin error.
- Lee el recibo de backend para saber si el envío llegó.
- **El contrato no cambia:** la etiqueta y el sobre son solo la forma de entregárselo a backend. Esto ya está programado en `send_batch.py`.

### Las tres opciones, lado a lado

| | A · Nos adaptamos | B · Una columna por campo | C · Etiqueta + caja |
|---|---|---|---|
| Esfuerzo de backend | Ninguno | Alto (unas 30 columnas y 8 tablas) | Bajo (25 a 30 líneas) |
| Esfuerzo de la ingesta | Bajo | Bajo | Bajo |
| ¿Se pierden datos? | **Sí** | No | No |
| ¿La IA recibe todo? | No | Sí | Sí |
| Consultar un dato de la caja | — | Fácil | Un poco más difícil (dentro del JSON) |
| Si el contrato suma un campo | Se pierde | Una columna nueva | **Nada cambia en backend** |
| Riesgo para la fecha | Bajo, pero el MVP queda incompleto | Alto | Bajo |

**Nuestra recomendación es la opción C:** no se pierde ningún dato, el cambio para backend es chico y su conexión con la IA (`NlpDataClient`) puede enviar la caja completa. Pero queremos su opinión: **ustedes conocen su código mejor que nosotros**, y puede haber una opción D que no vimos.

---

## 12. Preguntas para backend

> Qué vas a entender aquí: lo que necesitamos decidir juntos. Cada pregunta remite a la sección donde está explicado.

| # | Pregunta | Sección |
|---|---|---|
| 1 | ¿Qué opción prefieren: A, B, C u otra? ¿Por qué? | 11 |
| 2 | Si eligen la C, ¿les sirve guardar la caja en una columna jsonb? ¿Ven algún problema con JPA? | 11 |
| 3 | ¿Pueden hacer el *upsert* por `discordId`? Si un mensaje que llegó en el lote L1 se actualiza con el lote L2, ¿a qué paquete de resultados pertenece? | 9 y 10 |
| 4 | En vivo, cada lote trae 1 mensaje. ¿Quieren un paquete de resultados por mensaje, o prefieren separar "recibir mensajes" de "generar paquetes"? | 7 y 10 |
| 5 | ¿Qué datos va a enviar `NlpDataClient` a la IA? ¿Puede enviar la caja completa? | 6 y 10 |
| 6 | ¿Qué valores esperan en `autorRol` y `tipoServidor`? Proponemos `miembro`, `mentor` o `staff`, y `"discord"` | 10 |
| 7 | ¿Para qué fecha podrían tener los cambios? La ingesta apunta al pull request del 10/10 | 13 |

---

## 13. Qué hicimos y qué sigue

> Qué vas a entender aquí: cómo llegamos hasta aquí y qué viene después.

### Lo que hicimos

| Fecha | Qué se hizo | Resultado |
|---|---|---|
| 2026-09-28 | Definimos el alcance de la ingesta | [SCOPE.md](SCOPE.md) |
| 2026-09-28 | Creamos el servidor de pruebas, el bot y los webhooks, y verificamos la conexión | `verify_connection.py` |
| 2026-09-28 | Simulamos 7 alumnos y 1 mentor, y extrajimos los 38 mensajes | `simulate_students.py`, `extract.py` |
| 2026-09-28 | Documentamos cómo son los datos de Discord | [DISCORD_DATA_GUIDE.md](DISCORD_DATA_GUIDE.md) |
| 2026-09-29 | Interpretamos el brief, armamos el catálogo de casos y propusimos una arquitectura | [EVENT_CATALOG.md](EVENT_CATALOG.md) |
| 2026-09-29 | Diseñamos el borrador del contrato y lo probamos con los 38 mensajes, sin errores | [CONTRACT.md](CONTRACT.md) v0.1 |
| 2026-10-01 | Documentamos el brief y lo que entra en el MVP | [PROJECT_BRIEF.md](PROJECT_BRIEF.md) |
| 2026-10-01 | Validamos el contrato con criterio de casos reales: 7 decisiones aprobadas | [CONTRACT.md](CONTRACT.md) v0.2 |
| 2026-10-01 y 02 | Comparamos el contrato con el código de backend | Este documento |

### Lo que sigue

| Cuándo | Qué | Quién |
|---|---|---|
| Ahora | Conversar este documento y elegir una opción | Ingesta y backend |
| En paralelo | Programar el contrato en código, la transformación y la validación de todos los mensajes | Ingesta |
| Después del acuerdo | Ajustar el contrato a la opción elegida (v0.3) y probar el envío a la puerta de backend | Ingesta y backend |
| **2026-10-10** | Pull request de la ingesta a `main` | Ingesta |
| Después del 10/10 | El bot en vivo, en una rama nueva, con el mismo contrato | Ingesta |
| **2026-10-26** | Entrega final de la hackatón | Todo el equipo |
