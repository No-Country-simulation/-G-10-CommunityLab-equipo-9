# Brief del proyecto — InsightEdu Lab

> **Estado:** v1.0 · **Fecha:** 2026-10-01 · **Rama:** `feature/discord-ingestion`

## 0. Sobre este documento

**Qué es.** Lo que sabemos del brief del cliente (el enunciado de la hackatón) y lo que el equipo decidió tomar para el MVP. Es la referencia para cualquier decisión del contrato de ingesta: **si un dato no ayuda a ningún objetivo de este documento, no entra.**

**Para quién.** Todo el equipo: backend, IA, frontend y data.

**Cómo se relaciona con los otros documentos.**
- [EVENT_CATALOG.md](../../../docs/historico/ingesta/EVENT_CATALOG.md) traduce este brief a situaciones concretas de Discord.
- [SCOPE.md](../../../docs/historico/ingesta/SCOPE.md) fija el alcance de la ingesta.
- [CONTRACT.md](CONTRACT.md) define el formato en que entra cada mensaje.

**Fuentes.** Cada afirmación lleva su origen:
- 📄 **Brief:** texto del cliente, citado tal cual.
- 👤 **Decisión del equipo,** con su fecha.
- 🔎 **Interpretación nuestra:** lo que deducimos del brief.

---

## 1. El sector y el problema

> 📄 *"El sector necesita monitorear grandes volúmenes de conversaciones orgánicas, dudas, retroalimentación, entregas de proyectos y testimonios dispersos en canales digitales (Discord) y transformarlos de manera sistemática en activos de marketing, crecimiento y retención."*

> 📄 *"Hoy en día, las comunidades activas generan a diario decenas de historias inspiradoras, dudas recurrentes y testimonios valiosos, pero la mayor parte de ese valor se pierde en el historial de los canales porque la curaduría y la producción manual de contenidos de marketing consumen muchas horas de los equipos de Community Management y Marketing."*

🔎 **En una frase:** el valor ya existe en las conversaciones de la comunidad, pero nadie tiene tiempo de encontrarlo. El sistema lo encuentra y lo convierte en activos, y una persona aprueba antes de publicar.

## 2. Qué pide el brief

### 2.1 La solución

> 📄 *"Desarrollar una solución inteligente y automatizada capaz de ingerir la actividad orgánica de una comunidad digital (mensajes, debates en foros, feedback de cursos, entregas de proyectos de estudiantes, interacciones en chats), analizar estos datos y convertirlos automáticamente en activos de distribución listos para su publicación y toma de decisiones."*

### 2.2 Los cuatro componentes

| Componente | Lo que dice el brief 📄 |
|---|---|
| **Generador de contenido para redes** | *"Creación de publicaciones estructuradas para LinkedIn, X (Twitter) y Newsletters a partir de debates y logros de la comunidad"* |
| **Detector de historias de éxito y testimonios** | *"Identificación de relatos de superación, contrataciones laborales y proyectos destacados con extracción de citas y casos listos para marketing"* |
| **Motor de FAQ y contenido educativo** | *"Transformación de dudas frecuentes de los estudiantes en tutoriales rápidos, tips de la semana y temas de documentación"* |
| **Dashboard de salud y sentimiento** | *"Análisis continuo del sentimiento de los miembros, detección de temas en tendencia y alertas sobre miembros que necesitan apoyo"* |

### 2.3 La necesidad del cliente

> 📄 *"Los equipos de marketing y gestión de comunidades pasan horas navegando por mensajes dispersos en Discord o Slack intentando encontrar testimonios espontáneos de estudiantes o pensando qué publicar en las redes sociales de la institución."*

| # | La solución debe permitir 📄 |
|---|---|
| N1 | *"Capturar automáticamente lo que está sucediendo en la comunidad sin esfuerzo manual"* |
| N2 | *"Identificar a quienes lograron un hito importante o plantearon una duda enriquecedora de forma instantánea"* |
| N3 | *"Generar publicaciones persuasivas y listas para publicar en LinkedIn y Twitter, respetando la voz de la marca"* |
| N4 | *"Crear resúmenes semanales de la comunidad (Community Highlights) en segundos"* |
| N5 | *"Monitorear el sentimiento general, identificando si la comunidad está comprometida, satisfecha o con dificultades"* |

### 2.4 Requisitos técnicos

Estos requisitos vienen del brief, pero aquí no se copian completos. La correspondencia con sus listas (problemas PR1–PR4 y objetivos del MVP M1–M6) está en [EVENT_CATALOG.md](../../../docs/historico/ingesta/EVENT_CATALOG.md) §1.3.
- Un flujo automatizado en Python, orquestado con LangGraph (M4).
- Un panel para que una persona apruebe antes de publicar, y un dashboard (M5).
- Guardar los activos generados en OCI: 📄 *"persistir todos los paquetes de activos generados en un Bucket Always Free"* (M6).

---

## 3. Qué entra en el MVP

> Lo que el equipo decidió tomar del brief, y lo que dejó afuera.

| Del brief | Decisión | Origen |
|---|---|---|
| Posts para LinkedIn | ✅ Entra | 👤 |
| Posts para X (Twitter) y newsletters | ❌ No entra: solo LinkedIn | 👤 2026-10-01 |
| N4 · *Community Highlights* | ❌ No entra | 👤 2026-10-01 |
| Detector de historias de éxito y testimonios | ✅ Entra: casos de éxito con citas | 👤 |
| Motor de FAQ y contenido educativo | ✅ Entra | 👤 |
| Dashboard de salud con alertas | ✅ Entra | 👤 |
| Bot que responde dudas en vivo | ✅ Entra. **No lo pide el brief:** lo agrega el equipo, y por eso la ingesta también funciona en tiempo real | 👤 2026-09-29 |
| Discord o Slack | Solo Discord | 👤 2026-10-01 |
| "Debates en foros" | Extraer hilos y foros queda fuera del MVP (P5), pero el contrato ya tiene el campo `hilo` para no cambiar de versión después | 👤 2026-10-01 |
| OCI Object Storage | ✅ Obligatorio para los activos generados | 📄 M6 |
| Databricks | ❌ No se usa: el brief exige OCI ([SCOPE.md](../../../docs/historico/ingesta/SCOPE.md)) | 👤 2026-09-29 |

**Plazo:** la hackatón dura 5 semanas. **Entrega final: 2026-10-26.** 👤

## 4. Objetivos

### 4.1 Objetivos de negocio (MVP)

| # | Objetivo | Viene de | Activo |
|---|---|---|---|
| ON1 | Capturar la actividad de Discord sin trabajo manual | N1 | Todos |
| ON2 | Detectar al instante logros, contrataciones, historias de superación y dudas valiosas | N2 · Detector | Caso de éxito, LinkedIn, bot |
| ON3 | Generar posts de LinkedIn con la voz de la marca, listos para aprobar | N3 · Generador | LinkedIn |
| ON4 | Convertir las dudas frecuentes en FAQ, tutoriales y tips | Motor de FAQ | FAQ |
| ON5 | Medir el sentimiento, los temas en tendencia y los miembros que necesitan apoyo | N5 · Dashboard | Dashboard |
| ON6 | Responder las dudas en vivo con la documentación de la institución | Decisión del equipo | Bot |

### 4.2 Objetivos técnicos de la ingesta (esta rama)

Los objetivos O1–O5 están en [SCOPE.md](../../../docs/historico/ingesta/SCOPE.md) §2. En resumen: un contrato v1 (JSON Schema) que sirve igual por lotes y en vivo, la transformación y validación de todos los mensajes, la entrega a archivo y por HTTP, la especificación del endpoint para backend y un pull request a `main`.

**Criterio de diseño 👤:** el contrato tiene que funcionar con **una institución real**. La simulación es el banco de pruebas, no el objetivo.

---

## 5. Qué le exige el brief al contrato

> 🔎 Cada frase importante del brief, traducida a lo que la ingesta tiene que entregar.

| Frase del brief 📄 | Qué exige al contrato | Campo o decisión |
|---|---|---|
| *"sin esfuerzo manual"* | Extracción automática por lotes y en vivo, con el mismo formato | `modo` |
| *"de forma instantánea"* | El modo en tiempo real | `modo: "tiempoReal"` |
| *"relatos de superación"* | Seguir a la misma persona en el tiempo y entre canales | `autor.id` estable ([CONTRACT.md](CONTRACT.md) §8, decisión 1) |
| *"extracción de citas"* | El texto exacto, sin corregir | `textoOriginal` |
| *"contrataciones laborales"*, *"logros"* | El mensaje y la reacción de la comunidad | `reacciones`, `respondeA` |
| *"proyectos destacados"* | Enlaces, archivos y quién los destacó | `enlaces`, `adjuntos`, `autor.rol` (decisión 2) |
| *"dudas frecuentes"*, *"duda enriquecedora"* | La duda, sus respuestas y la respuesta oficial | `respondeA`, `fijado`, `autor.rol` |
| *"alertas sobre miembros que necesitan apoyo"* | Quién escribe y cuándo, para calcular la deserción | `autor.id`, `fecha` |
| *"temas en tendencia"* | Texto, canal y fecha de cada mensaje | `textoOriginal`, `canal`, `fecha` |
| *"debates en foros"* | Saber si un mensaje está dentro de un hilo | `hilo` (decisión 7, en `null` en el MVP) |
| *"respetando la voz de la marca"* | Nada: la voz la define la institución, no la ingesta | — |

## 6. Riesgos y límites conocidos

| Riesgo | Por qué importa | Dónde se sigue |
|---|---|---|
| Los foros no se extraen en el MVP | Si la institución real usa foros para las dudas, el análisis por lotes no las verá | [SCOPE.md](../../../docs/historico/ingesta/SCOPE.md) P5 |
| Consentimiento para publicar testimonios | Citar a un alumno con su nombre en LinkedIn usa sus datos personales | [SCOPE.md](../../../docs/historico/ingesta/SCOPE.md) P3 |
| No hay datos reales | Todo se prueba con un servidor simulado; los datos reales pueden ser más desordenados | [SCOPE.md](../../../docs/historico/ingesta/SCOPE.md) P1 |
| El rol es el de hoy, no el de entonces | Un alumno que pasó a ser mentor aparece como mentor también en sus mensajes viejos | [CONTRACT.md](CONTRACT.md) §4.1 |
