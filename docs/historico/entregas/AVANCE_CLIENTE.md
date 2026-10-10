# InsightEdu Lab (CommunityLab)

> ⚠️ **Documento histórico:** un informe al cliente del 2026-10-05; el estado actual está en ESTADO.md. **No es una instrucción vigente.** Cómo funciona hoy: [ARQUITECTURA.md](../../ARQUITECTURA.md) · Qué falta: [ESTADO.md](../../ESTADO.md)

**Informe de avance para el cliente**
Equipo 9 · G10 · Hackatón No Country + ONE
Versión 1.0 · 5 de octubre de 2026 · Entrega final: 26 de octubre de 2026

## 1. Resumen

InsightEdu Lab convierte la conversación diaria de una comunidad educativa en Discord en material útil para la institución: posts de LinkedIn, casos de éxito, preguntas frecuentes y alertas sobre los alumnos que necesitan apoyo. El sistema lee los mensajes, los clasifica con inteligencia artificial y prepara borradores, pero nada se publica sin que una persona lo revise y lo apruebe.

Al 5 de octubre, el recorrido principal funciona de punta a punta en nuestro entorno de pruebas: los mensajes entran solos, se clasifican, el bot responde dudas con la documentación oficial, se redactan los borradores y el equipo de marketing los aprueba desde un panel con dashboard. Faltan el guardado de los activos en la nube de Oracle y la puesta en marcha en el servidor.

## 2. El problema

Una comunidad activa genera todos los días historias de superación, dudas que se repiten y comentarios sobre los cursos. Ese contenido tiene mucho valor para marketing y para el seguimiento de los alumnos, pero casi siempre se pierde en el historial de los canales. Encontrarlo exige que alguien lea cientos de mensajes, y los equipos de Community Management y Marketing no tienen ese tiempo.

En pocas palabras: el valor ya está en las conversaciones, pero nadie tiene tiempo de buscarlo. InsightEdu Lab lo encuentra, lo ordena y lo deja listo para que una persona decida qué hacer con él.

Quienes se benefician son tres grupos. Marketing recibe borradores listos para revisar en lugar de una hoja en blanco. Community Management ve de un vistazo el ánimo de la comunidad y sabe a quién acompañar. Y los alumnos obtienen una respuesta inmediata a sus dudas, basada en los reglamentos y manuales oficiales, sin esperar a que un mentor esté conectado.

## 3. Qué se pidió y qué incluye esta entrega

A partir del brief, el equipo definió siete necesidades. Son la vara con la que medimos el producto:

- **N1 · Captura sin esfuerzo manual.** Todo lo que se escribe en Discord entra solo al sistema, tanto el historial como lo que pasa en vivo.
- **N2 · Detectar al instante logros y dudas.** Cada mensaje se reconoce como logro, pregunta, comentario o ruido.
- **N3 · Posts de LinkedIn con la voz de la marca.** Un logro se convierte en un borrador de post y de caso de éxito.
- **N4 · FAQ y bot que responde dudas.** El bot responde en vivo con los documentos de la institución, y las dudas repetidas se convierten en una FAQ semanal.
- **N5 · Dashboard de la comunidad.** Clima general, temas del momento y alertas sobre alumnos que necesitan apoyo.
- **N6 · Aprobación humana.** Nada se publica sin revisión, edición y aprobación de una persona.
- **N7 · Guardado en OCI.** Los activos generados y aprobados se guardan en un bucket de Oracle Cloud.

Para cumplir en cinco semanas, el equipo dejó fuera de esta entrega las publicaciones para X y los newsletters (solo LinkedIn), el resumen semanal *Community Highlights* y la integración con Slack (solo Discord). La arquitectura permite sumarlos más adelante sin rehacer lo construido.

## 4. Objetivos

**Objetivo general.** Entregar el 26 de octubre una primera versión de InsightEdu Lab que funcione de punta a punta y esté desplegada, capaz de transformar la actividad de un servidor de Discord en activos de marketing, respuestas a dudas y alertas, con una persona que aprueba antes de publicar.

**Objetivos específicos.**

1. Capturar los mensajes de Discord en vivo y por lotes, sin duplicados.
2. Etiquetar cada mensaje con su intención, su sentimiento y su tema, sin perder mensajes si la IA falla.
3. Redactar, para cada logro, un borrador de post de LinkedIn y un caso de éxito con la voz de la institución.
4. Responder dudas en vivo solo con respaldo en la documentación oficial, y armar cada semana una FAQ con las preguntas repetidas.
5. Ofrecer un dashboard con el clima de la comunidad, los temas en tendencia y alertas de deserción y frustración.
6. Dar a marketing un panel con usuario y contraseña para editar, aprobar o rechazar, con registro del consentimiento del alumno.
7. Guardar en OCI los activos generados y los aprobados.
8. Que todo funcione con un solo comando, con accesos protegidos y pruebas automáticas.
9. Desplegarlo en un servidor y ensayar la demostración.

## 5. Arquitectura

El sistema se apoya en tres reglas simples. Hay un solo formato para describir un mensaje, desde que sale de Discord hasta que se guarda. Hay una sola puerta de entrada, la API central, que además es el registro oficial. Y la inteligencia artificial solo procesa: recibe mensajes, devuelve resultados y no guarda datos propios.

```
                         SERVIDOR
 +----------+     +-------------------------------------------------+
 |          |     |                                                 |
 | Discord  |<--->|  Bot en vivo ----+                              |
 |          |     |                  |                              |
 |          |---->|  Ingesta ------->+---> API central ----> IA      |
 +----------+     |  (cada hora)          (Java)      <----         |
                  |                         |                       |
                  |                         +--> Base de datos      |
                  |                         |    (PostgreSQL)       |
                  |  Panel y dashboard <----+                       |
                  |  (marketing y CM)       |                       |
                  +-------------------------|-----------------------+
                                            v
                                     OCI Object Storage
                                     (activos generados
                                      y aprobados)
```

Qué hace cada pieza:

- **Bot en vivo.** Escucha los canales de dudas y de logros, avisa a la API y responde en Discord cuando corresponde.
- **Ingesta.** Cada hora revisa el historial, recupera lo que el bot no vio y actualiza reacciones y ediciones.
- **API central.** Recibe todo, valida, evita duplicados, coordina a la IA y guarda el resultado.
- **Base de datos.** Guarda cada mensaje, sus etiquetas, los borradores y quién los aprobó.
- **IA.** Clasifica los mensajes, responde dudas con los documentos de la institución, redacta borradores y arma la FAQ.
- **Panel.** Permite revisar, editar, aprobar o rechazar borradores, y muestra el dashboard.
- **OCI.** Guarda como archivos los activos generados y los aprobados.

Solo el panel queda abierto a internet, con usuario y contraseña. La base de datos y la IA quedan en una red privada.

## 6. Un mensaje de punta a punta

Tomemos un caso real del servidor de pruebas. Una alumna escribe en el canal de logros: "¡Me contrataron! Después de seis meses de bootcamp empiezo el lunes como QA trainee".

```
 1. Captura       El bot recibe el mensaje y la API lo guarda.
       |
 2. Clasificación La IA lo etiqueta: logro, muy positivo, tema "empleo".
       |
 3. Borradores    La IA redacta un post de LinkedIn y un caso de éxito
       |          con el tono de la institución.
       |
 4. Una hora      La ingesta trae el mismo mensaje con más reacciones.
    después       La API lo actualiza: no se duplica.
       |
 5. Dashboard     Suma un mensaje positivo y un logro de empleo en la semana.
       |
 6. Revisión      Marketing abre el panel, corrige una frase, confirma
       |          el consentimiento de la alumna y aprueba.
       |
 7. Guardado      El activo aprobado se guarda en OCI. (En construcción)
```

Si en cambio el mensaje es una duda, el bot busca la respuesta en los reglamentos y manuales de la institución. Si la encuentra, responde citando el documento; si no, avisa que un mentor la va a responder.

## 7. Cuidado de los datos y control humano

- **Nada se publica solo.** Los posts, los casos de éxito y la FAQ quedan como borradores hasta que una persona los aprueba.
- **Consentimiento.** Antes de aprobar un contenido que nombra a un alumno, el panel exige confirmar que el alumno dio su permiso.
- **Respuestas con respaldo.** El bot responde solo cuando encuentra la información en los documentos oficiales; nunca inventa.
- **Accesos protegidos.** Cada pieza usa su propia clave y cada persona del panel tiene su usuario. Los datos de Discord no se suben al repositorio de código.

## 8. Estado al 5 de octubre de 2026

- **N1 Captura: Listo.** Lotes y bot en vivo; probado con 39 mensajes reales del servidor de pruebas, sin duplicados.
- **N2 Detección: Listo.** Intención, sentimiento y tema en cada mensaje.
- **N3 Posts de LinkedIn: Listo.** Borradores de post y de caso de éxito con guía de voz.
- **N4 FAQ y bot: Listo.** Respuestas en vivo y FAQ semanal cada lunes.
- **N5 Dashboard: Listo.** Clima, temas y alertas de deserción, frustración y dudas sin responder.
- **N6 Aprobación: Listo.** Panel con inicio de sesión, edición, aprobación y consentimiento.
- **N7 Guardado en OCI: En curso.** Diseño cerrado; empieza la construcción.
- **Despliegue: Pendiente.** Puesta en marcha en el servidor y ensayo de la demo.

Todo lo marcado como "listo" funciona en el entorno de pruebas del equipo y está cubierto por pruebas automáticas.

## 9. Próximos pasos

- **Del 6 al 12 de octubre:** guardado de los activos en OCI.
- **Del 13 al 19 de octubre:** despliegue en el servidor, revisión de seguridad y ajustes de calidad.
- **Del 20 al 25 de octubre:** ensayo de la demostración y correcciones finales.
- **26 de octubre:** entrega final.

Ante cualquier consulta sobre este informe, el Equipo 9 queda a disposición.
