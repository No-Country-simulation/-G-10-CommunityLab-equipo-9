# Catálogo de eventos de la comunidad — InsightEdu Lab

> **Estado:** aprobado v1.0 · **Fecha:** 2026-09-29 · **Rama:** `feature/discord-ingestion`

## 0. Sobre este documento

**Objetivo.** Hacer una lista de las situaciones que ocurren en una comunidad EduTech en Discord. Para cada una se indica qué problema del negocio ataca, cómo se ve en Discord y qué datos hay que registrar. Es la base para definir el contrato de ingesta (O4): si un dato no aparece en este catálogo, el contrato no tiene por qué incluirlo.

**Para quién.** Todo el equipo: backend, data, frontend e IA.

**Cómo leerlo.**
1. La §1 resume qué pide el proyecto.
2. La §2 explica cómo leer el catálogo.
3. La §3 es el catálogo.
4. Las §4 y §5 dicen qué priorizar y qué le falta hoy a la ingesta.

Si nunca trabajaste con Discord, lee antes la sección 2 de la [guía de datos](DISCORD_DATA_GUIDE.md).

---

## 1. Qué nos pide el proyecto

> Una lectura ordenada del brief, sin repeticiones, para que todos partamos de lo mismo.

### 1.1 En una frase
Convertir automáticamente la actividad de una comunidad EduTech en Discord en **activos de marketing, contenido educativo y alertas de retención**, con una persona que revisa y aprueba antes de publicar.

### 1.2 Quién usa el sistema

| Actor | Relación con el sistema |
|---|---|
| Estudiantes | **Generan** los datos en Discord. Solo interactúan con el sistema a través del bot que responde dudas |
| Community Manager (CM) | Monitorea la salud de la comunidad y recibe alertas |
| Marketing | Aprueba y publica los posts de LinkedIn y los testimonios |
| Institución | Define la voz de la marca y aporta la documentación que usa el bot |

### 1.3 Las 5 capacidades

El brief repite las mismas ideas en tres listas: problemas (PR1–PR4), necesidades del cliente (N1–N5) y objetivos del MVP (M1–M6). Están numeradas en el orden en que aparecen, y no hay que confundirlas con los pendientes P1–P7 de [SCOPE.md](SCOPE.md). Ordenadas como un proceso, se reducen a cinco capacidades:

| # | Capacidad | Qué significa | Dónde lo pide el brief |
|---|---|---|---|
| 1 | **Capturar** | Ingerir la actividad de Discord sin trabajo manual | N1 · M1 |
| 2 | **Entender** | Con LLMs: medir el sentimiento, clasificar temas y detectar historias de éxito, dudas frecuentes, tendencias y miembros en riesgo | PR2, PR3, PR4 · N2, N5 · M2 |
| 3 | **Producir** | Generar activos listos para publicar | PR1, PR2, PR3 · N3, N4 · M3 |
| 4 | **Curar y monitorear** | Un panel para aprobar antes de publicar y un dashboard de salud con alertas | PR4 · N5 · M5 |
| 5 | **Orquestar y persistir** | Un flujo automatizado en Python (LangGraph) que guarda los activos en OCI Object Storage | M4 · M6 |

**La ingesta es la capacidad 1.** Las otras cuatro dependen de ella.

### 1.4 Activos del MVP

| Código | Activo | Para quién | Seleccionado |
|---|---|---|---|
| `LI` | Post de LinkedIn | Marketing | ✅ |
| `CE` | Caso de éxito o testimonio con citas | Marketing | ✅ |
| `FAQ` | FAQ, tutorial rápido, tip de la semana o tema de documentación | CM y equipo educativo | ✅ |
| `DB` | Dashboard de salud con alertas | CM | ✅ |
| `BOT` | Bot que responde dudas en vivo con la documentación de la institución | Estudiantes | ✅ (lo agrega el equipo; el brief no lo pide) |
| — | Resumen semanal *Community Highlights* | CM y la comunidad | ❌ Fuera del MVP |

### 1.5 Decisiones del equipo
- **El bot en vivo entra en el MVP.** Por eso la ingesta en tiempo real deja de ser "algún día": el bot la necesita.
- **OCI Object Storage es obligatorio para los activos generados.** El brief pide *"persistir todos los paquetes de activos generados en un Bucket Always Free"*. Para la ingesta es opcional (ver [SCOPE.md](SCOPE.md)).
- **Databricks no se usa en el MVP.** El motivo está en [SCOPE.md](SCOPE.md).
- **En el MVP no hay hilos, foros ni datos de los miembros.** Ver §5.

### 1.6 Qué implica para la ingesta
1. **Hay más actividad que dudas y logros:** presentaciones, proyectos, feedback de cursos, debates, anuncios, encuestas y más (ver §3).
2. **No importan solo los mensajes, también las personas.** Las alertas y las historias de superación exigen seguir a cada miembro en el tiempo, mediante su identidad estable y su actividad. En el MVP no se extraen datos del miembro (ni fecha de ingreso ni roles): la deserción se calcula a partir de la actividad.
3. **Publicar testimonios exige consentimiento.** Citar a un alumno con su nombre en LinkedIn es usar públicamente sus datos personales. Se suma al pendiente P3.

---

## 2. Cómo leer el catálogo

> Tres ideas para leer la §3 sin perderse.

**Evento de negocio vs. señal técnica.** "Un alumno consiguió trabajo" no existe para Discord: para Discord es un mensaje normal, quizás con reacciones 🎉. La ingesta captura **la señal técnica** (el mensaje, sus reacciones, sus respuestas) y la IA interpreta **el negocio** (que es una contratación). Por eso cada caso dice cómo se ve en Discord.

**Directo vs. derivado.**
- Un evento **directo** se ve en un solo dato de Discord, por ejemplo un mensaje.
- Un evento **derivado** se calcula a partir de muchos datos, por ejemplo "un miembro dejó de participar". La columna "Cómo se ve en Discord" lo indica con la palabra *Derivado*.

**Columnas y escalas.**
- **Frecuencia:** Alta (a diario), Media (semanal) u Ocasional.
- **Valor para el negocio:** Bajo, Medio, Alto o Muy alto.
- **Activos:** los códigos de la §1.4.
- **⏸ Fuera del MVP:** el caso se conserva en el catálogo, pero por ahora no se cubre (ver §5).

Los eventos ocasionales con valor muy alto (una contratación, una historia de superación) son la razón para registrar el máximo de datos: pasan poco, pero valen mucho.

Las señales técnicas salen de la documentación oficial de Discord. Los eventos en tiempo real (del *Gateway*) se verificarán en detalle al diseñar esa fase.

---

## 3. Catálogo

### A. Dudas y aprendizaje
> Alimentan al bot y al motor de FAQ. Es la actividad más frecuente de la comunidad.

| # | Caso | Dolor que ataca | Ejemplo | Cómo se ve en Discord | Datos a registrar | Activos | Frecuencia / valor |
|---|---|---|---|---|---|---|---|
| A1 | Duda nueva | Los mentores responden lo mismo una y otra vez; el alumno espera | "como instalo pyhton en windows??" | Mensaje (`type` 0) en `#dudas`, o una publicación en un canal de foro | ID del mensaje, autor, texto original, fecha, canal, hilo, adjuntos, bloques de código y enlaces | BOT, FAQ, DB | Alta / Alto |
| A2 | Duda partida en varios mensajes | El bot responde a fragmentos sueltos | "hola" / "tengo una duda" / "el pip no funciona" | Varios mensajes seguidos del mismo autor en el mismo canal, con segundos de diferencia | Autor, fecha precisa y canal | BOT, FAQ | Alta / Medio |
| A3 | Duda con captura del error | El texto solo no alcanza para entender el problema | Una imagen y después "me sale esto" | `attachments` de tipo imagen, con `content` vacío o corto | Adjuntos (tipo, nombre, tamaño y medidas) y el mensaje siguiente del mismo autor | BOT, FAQ | Alta / Medio |
| A4 | Duda repetida con otras palabras | La FAQ no se actualiza y se pierde tiempo | "cómo instalo Python", preguntado 3 veces | *Derivado:* textos parecidos en fechas distintas; lo detecta la IA | Texto, fecha, autor y canal | FAQ, DB | Alta / Alto |
| A5 | Duda sin responder | El alumno se frustra y puede abandonar | "alguien? 😅" | *Derivado:* sin respuestas ni mensajes en su hilo después de N horas, o el mismo autor insiste | Fecha, respuestas recibidas (con sus fechas) e hilo | DB (alerta), BOT | Media / Alto |
| A6 | Duda resuelta | No se sabe qué respuesta funcionó, que es la mejor materia prima para la FAQ | "graciasss era eso 🙏", una reacción ✅ o la etiqueta "resuelto" en un foro | Respuesta (`type` 19) de agradecimiento, reacción ✅, etiquetas del hilo (`applied_tags`) o una edición con "RESUELTO" | A qué mensaje responde, reacciones por emoji, etiquetas del hilo y edición | FAQ | Media / Muy alto |
| A7 | Un compañero responde | No se reconoce a los alumnos que ayudan, que son futuros embajadores | "te falta el punto y coma…" | Una respuesta (`type` 19) o un mensaje en el hilo de otro autor | Autor, a qué mensaje responde y fecha | FAQ, CE, DB | Media / Alto |
| A8 | Respuesta oficial de un mentor | Las respuestas oficiales se pierden en el historial | Un mentor responde y fija el mensaje | Autor con el rol de mentor, mensaje fijado (`pinned`) y respuesta | Roles del autor, si está fijado y a qué responde | FAQ | Media / Alto |
| A9 | Debate enriquecedor | Los debates valiosos no se convierten en contenido | "¿conviene aprender Java o Python primero?", con 15 respuestas | Un hilo largo o muchas respuestas, con varios autores distintos y reacciones | Hilo, cantidad de respuestas, cantidad de autores distintos y reacciones | LI, FAQ | Ocasional / Alto |
| A10 | Se califica la respuesta del bot | No se sabe si el bot responde bien | El alumno reacciona 👎 o vuelve a preguntar | Mensaje del propio bot (`author.id` = el bot) y las reacciones o respuestas que recibe | Autor (el bot), a qué responde y reacciones por emoji | BOT, DB | Media / Alto |

### B. Logros e historias de éxito
> La materia prima de los testimonios y de los posts de LinkedIn. Son poco frecuentes, pero son el activo más valioso para marketing.

| # | Caso | Dolor que ataca | Ejemplo | Cómo se ve en Discord | Datos a registrar | Activos | Frecuencia / valor |
|---|---|---|---|---|---|---|---|
| B1 | Empleo: entrevista o contratación | Marketing pierde los testimonios en el historial | "me contrataron!!!!! después de 6 meses…" | Mensaje en `#logros`, con reacciones 🎉 y respuestas de felicitación | Autor (ID estable), texto original, fecha, canal, reacciones por emoji, respuestas recibidas y adjuntos | LI, CE, DB | Ocasional / Muy alto |
| B2 | Curso terminado o certificado | Los hitos académicos no se difunden | "Terminé Lógica de Programación 🎉", con la foto del certificado | Mensaje con un adjunto (imagen o PDF) | Adjuntos, texto y fecha | LI, CE, DB | Media / Alto |
| B3 | Challenge o proyecto aprobado | No se sabe qué alumnos avanzan | "Aprobé el challenge de la biblioteca ✅" | Mensaje en `#logros` | Texto, autor y fecha | CE, LI, DB | Media / Alto |
| B4 | Racha o constancia | Los hábitos positivos no se reconocen | "20 días seguidos estudiando 🔥" | Mensaje en `#logros` | Texto, autor y fecha | CE, DB | Media / Medio |
| B5 | Historia de superación | Las mejores historias se reparten en semanas de mensajes | Luis: "pienso dejar el curso" y, días después, "hoy entendí recursividad" | *Derivado:* el mismo autor, con sentimiento negativo antes y positivo después | Autor (el ID estable es clave), fechas, canal y texto | CE, LI | Ocasional / Muy alto |
| B6 | Agradecimiento espontáneo | Los testimonios espontáneos nunca llegan a marketing | "gracias a todos por la ayuda en el canal" | Mensaje, quizás con menciones a mentores o a roles | Texto, menciones y autor | CE, LI | Ocasional / Muy alto |
| B7 | Felicitaciones de otros | No se mide la validación social de un logro | "Felicidades Camila…" | Respuestas y reacciones sobre el logro; a veces nombres escritos sin mención | A qué responde, menciones y reacciones | DB, LI | Media / Medio |
| B8 | Logro compartido desde otra red | Se pierde la oportunidad de amplificar un post que ya existe | El alumno comparte su post de LinkedIn | Un enlace a linkedin.com en el texto, quizás con vista previa (`embeds`) | Enlaces (con su dominio) y vistas previas | LI, CE | Ocasional / Alto |

### C. Proyectos y entregas
> Muestran lo que los alumnos son capaces de hacer. Alimentan los casos de éxito.

| # | Caso | Dolor que ataca | Ejemplo | Cómo se ve en Discord | Datos a registrar | Activos | Frecuencia / valor |
|---|---|---|---|---|---|---|---|
| C1 | Entrega o demo de un proyecto | Los proyectos destacados no se muestran | "Acá el repo: https://github.com/…", o un video de la demo | Enlaces (GitHub, deploy o YouTube), adjuntos (video o imagen) en `#proyectos` | Enlaces con su dominio, adjuntos, texto y autor | CE, LI | Media / Alto |
| C2 | Proyecto destacado por un mentor | No se identifica lo que vale la pena mostrar | Un mentor reacciona ⭐ o fija el mensaje | Reacciones de un autor con el rol de mentor; mensaje fijado | Reacciones con **quién** reaccionó (requiere una petición aparte), si está fijado y roles | CE, LI | Ocasional / Muy alto |
| C3 | Pedido de revisión de código | Las revisiones se acumulan sin respuesta | "¿me revisan el PR?" | Bloques de código o un enlace a GitHub | Texto, enlaces y respuestas recibidas | FAQ, DB | Media / Medio |

### D. Feedback sobre los cursos
> Lo que los alumnos opinan del contenido. Alimenta el dashboard y los temas de documentación.

| # | Caso | Dolor que ataca | Ejemplo | Cómo se ve en Discord | Datos a registrar | Activos | Frecuencia / valor |
|---|---|---|---|---|---|---|---|
| D1 | Feedback positivo sobre una clase | Las citas positivas no se aprovechan | "la clase de hoy estuvo buenísima" | Mensaje en `#feedback` o `#general`; el sentimiento lo interpreta la IA | Texto, fecha, canal y reacciones | CE, DB | Media / Alto |
| D2 | Queja o sugerencia | Los problemas del curso se detectan tarde | "no se entiende el módulo de Spring" | Mensaje; la IA interpreta el sentimiento | Texto, fecha, canal y reacciones (por ejemplo, un "+1") | DB (alerta), FAQ | Media / Alto |
| D3 | Error en el material | El contenido desactualizado genera dudas repetidas | "el link del módulo 3 está roto" | Mensaje con un enlace | Texto y enlaces | FAQ, DB | Ocasional / Alto |
| D4 | Encuesta | Sin datos para decidir qué reforzar | "¿qué tema repasamos el jueves?" | Mensaje con una encuesta (`poll`). Al cerrarse, Discord publica un mensaje `type` 46 con el resultado | Pregunta, opciones, votos y resultado | DB, FAQ | Ocasional / Medio |

### E. Salud de la comunidad
> Las señales de riesgo y de clima. Alimentan las alertas del dashboard.

| # | Caso | Dolor que ataca | Ejemplo | Cómo se ve en Discord | Datos a registrar | Activos | Frecuencia / valor |
|---|---|---|---|---|---|---|---|
| E1 | Frustración o intención de abandono | La deserción se detecta cuando ya es tarde | "estoy pensando en dejar el curso 😞" | Mensaje en cualquier canal; lo detecta la IA | Autor (ID estable), texto, fecha y canal | DB (alerta) y CE (si después lo supera) | Ocasional / Muy alto |
| E2 | Urgencia o estrés | Las urgencias reales se pierden entre los demás mensajes | "URGENTE!!! tengo que entregar hoy" | Mensaje con mayúsculas y signos repetidos | Texto, fecha y autor | DB, BOT | Media / Medio |
| E3 | Un miembro deja de participar | Nadie nota que alguien desapareció | Un alumno activo lleva 14 días sin escribir | *Derivado:* sin mensajes desde X días | Autor y fecha de su último mensaje. Con eso se calcula la deserción mensual, que mide a quien dejó de escribir, no a quien abandonó el curso | DB (alerta) | Media / Alto |
| E4 | Tema en tendencia o cambio de actividad | No se sabe de qué habla la comunidad ni si crece | Muchos preguntan por Spring Boot esta semana | *Derivado:* frecuencia de temas y de mensajes por día | Texto, fecha, canal y autor | DB, FAQ, LI | Alta / Alto |
| E5 | Conflicto o mensaje tóxico | El clima se deteriora sin que nadie intervenga | Una discusión agresiva | Mensaje (lo interpreta la IA) y, a veces, un borrado posterior | Texto, autor y fecha | DB (alerta) | Ocasional / Alto |

### F. Ciclo de vida del miembro
> Cómo entra, cambia y sale cada persona. F1, F3 y F4 quedan fuera del MVP porque necesitan datos de los miembros o escucha en tiempo real.

| # | Caso | Dolor que ataca | Ejemplo | Cómo se ve en Discord | Datos a registrar | Activos | Frecuencia / valor |
|---|---|---|---|---|---|---|---|
| F1 | ⏸ Se une un miembro nuevo | No se mide el crecimiento de la comunidad | "Ana se unió al servidor" | Aviso del sistema (`type` 7). En tiempo real, un evento del *Gateway* que exige un permiso privilegiado (*Server Members Intent*) | ID del miembro y fecha de ingreso | DB | Media / Medio |
| F2 | Presentación de un alumno | Se pierde el "antes" de las historias de transformación | "Hola, soy Ana de México, vengo de marketing" | Mensaje en `#presentaciones` | Texto, autor y fecha | CE, DB | Media / Alto |
| F3 | ⏸ Cambio de rol | No se sabe quién egresó o quién pasó a ser mentor | De alumno a egresado | Cambian los roles del miembro; se consulta el miembro o se recibe un evento en tiempo real | Roles y fecha | CE, DB | Ocasional / Alto |
| F4 | ⏸ Un miembro se va | La deserción no se registra | El alumno sale del servidor | Solo un evento en tiempo real, con el mismo permiso privilegiado; por REST no queda rastro | ID del miembro y fecha | DB | Ocasional / Alto |

### G. Interacciones
> Señales que acompañan a todos los casos anteriores y miden su relevancia.

| # | Caso | Dolor que ataca | Ejemplo | Cómo se ve en Discord | Datos a registrar | Activos | Frecuencia / valor |
|---|---|---|---|---|---|---|---|
| G1 | Reacción a un mensaje | No se sabe qué mensajes resuenan | 🎉 ×12 en un logro | `reactions` (conteo por emoji). Saber **quién** reaccionó requiere una petición aparte o el tiempo real | Emoji, conteo y, si hace falta, quién reaccionó | Todos | Alta / Medio |
| G2 | Mención a un miembro, a un rol o al bot | El bot no se entera de que lo llamaron | "@InsightEdu Ingesta ayuda" | `<@id>` en `mentions` o `<@&id>` en `mention_roles` | Menciones de usuarios y de roles | BOT, DB | Alta / Medio |
| G3 | ⏸ Hilo o publicación en un foro | Las conversaciones dentro de hilos no se extraen (P5) | Un hilo "Error con Gson" con 8 mensajes | Un canal de tipo hilo (11 o 12) o de tipo foro (15), con etiquetas (`applied_tags`) | ID, nombre y etiquetas del hilo, y sus mensajes | FAQ, BOT | Media / Alto |
| G4 | Mensaje fijado | No se reconoce el contenido que el equipo consideró importante | El mentor fija una respuesta | `pinned` y un aviso del sistema (`type` 6) | Si está fijado y cuándo | FAQ | Ocasional / Medio |
| G5 | Mensaje editado | La versión guardada queda vieja | Una duda editada con "RESUELTO" | `edited_timestamp` | Si se editó y cuándo | FAQ | Media / Bajo |
| G6 | Mensaje borrado | Se usa un texto que su autor retiró, por ejemplo un testimonio | El alumno borra su mensaje | Por REST, simplemente desaparece. En tiempo real llega un aviso con los IDs | ID del mensaje y fecha del borrado | DB | Ocasional / Medio |

### H. La institución
> La actividad del equipo de la institución. Da contexto a todo lo demás.

| # | Caso | Dolor que ataca | Ejemplo | Cómo se ve en Discord | Datos a registrar | Activos | Frecuencia / valor |
|---|---|---|---|---|---|---|---|
| H1 | Anuncio oficial | Se mezcla con las conversaciones de los alumnos | "recuerden la mentoría del jueves" | Mensaje de un autor con el rol de *staff*, en `#anuncios` | Roles del autor, texto y fecha | DB | Media / Bajo |
| H2 | Clase en vivo o evento programado | No se mide la participación | "Clase en vivo: Spring Boot" | Un evento programado de Discord, que se consulta con su propia petición | Evento, fecha y cantidad de interesados | DB, LI | Ocasional / Medio |
| H3 | Oferta de empleo compartida | No se conecta con las contrataciones posteriores | Un enlace a una vacante en `#empleos` | Mensaje con un enlace | Enlaces, texto y fecha | DB, CE | Ocasional / Medio |

### I. Ruido
> Lo que hay que reconocer para poder filtrarlo.

| # | Caso | Dolor que ataca | Ejemplo | Cómo se ve en Discord | Datos a registrar | Activos | Frecuencia / valor |
|---|---|---|---|---|---|---|---|
| I1 | Fuera de tema, memes o stickers | Ensucia el análisis | Un GIF o un sticker | `sticker_items` y vistas previas de GIF | Stickers y vistas previas | DB (solo para medir el clima) | Alta / Bajo |
| I2 | Otros bots o spam | Se confunde con la actividad de los alumnos | Mensajes automáticos, enlaces sospechosos | `author.bot` o `application_id` | Si el autor es un bot, y enlaces | Ninguno (se filtra) | Media / Bajo |

---

## 4. Priorización para el MVP

> Qué eventos necesita cada activo seleccionado. Los que aparecen en varias filas son los de mayor prioridad para la ingesta.

| Activo | Eventos clave |
|---|---|
| `BOT` | A1, A2, A3, A5, A10, G2 |
| `FAQ` | A1, A4, A6, A8, A9, D2, D3 |
| `LI` y `CE` | B1 a B8, C1, C2, D1, F2 |
| `DB` | A5, D1, D2, E1 a E5, G1 |

## 5. Qué le falta hoy a la ingesta

> La diferencia entre lo que ya hacemos y lo que pide el catálogo, con la decisión tomada para el MVP.

| Tema | Decisión para el MVP |
|---|---|
| Más canales (`#presentaciones`, `#proyectos`, `#feedback`, `#anuncios`, `#empleos`) | Pospuesto: se agregan cuando se amplíe la simulación |
| Datos de los miembros (fecha de ingreso, roles) | No se extraen. La deserción se calcula con la actividad (E3). Cómo reconocer a un mentor o al *staff* (A8, C2, H1) se resuelve al definir el contrato |
| Hilos y foros (P5) | Descartados: `#dudas` es un canal normal. Es una limitación conocida si la institución real usa foros |
| Quién reaccionó (C2, G1) | Opcional: es una petición aparte por cada emoji |
| Tiempo real (Gateway) | Lo necesita el bot. Se construye en otra rama, con el mismo contrato |
| Simulación ampliada (eventos ocasionales de alto valor) | Pospuesta hasta cerrar el contrato |

## 6. Próximo paso: consolidar los datos

Juntar la columna "Datos a registrar" de todos los casos en **una sola lista de campos**, sin repeticiones. Para cada campo se indicará de dónde sale en Discord, su tipo, si viene siempre y qué casos lo usan. Esa lista es la propuesta del **contrato v1 (O4)**, que validaremos antes de programarlo.
