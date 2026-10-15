# Estado del proyecto y cómo continuar

> **Qué es este documento:** qué está hecho, qué falta y cómo seguir trabajando sin romper lo que existe.
> **Actualizado:** 2026-10-14 · **Rama:** `main` · **Entrega de la hackatón:** 2026-10-26
> Cómo funciona el sistema: [ARQUITECTURA.md](ARQUITECTURA.md). Por qué se decidió cada cosa: [DECISIONES.md](DECISIONES.md).

## 1. En una frase

**El MVP funciona de punta a punta en una computadora local**: los mensajes entran por el bot y por lotes, se clasifican, el bot responde dudas con la documentación oficial, se redactan borradores de LinkedIn, casos de éxito y una FAQ semanal, Marketing los aprueba en un panel con dashboard, todo se guarda en OCI y, si se enciende, los posts aprobados se publican solos en LinkedIn. **Falta desplegarlo en un servidor** y programar la ingesta cada hora.

## 2. Objetivos del proyecto

**Objetivo principal:** entregar el 2026-10-26 un MVP de InsightEdu Lab que funcione de punta a punta y esté desplegado. Debe convertir la actividad de un servidor de Discord en activos de marketing, respuestas a dudas y alertas sobre la comunidad, con una persona que apruebe antes de publicar.

| # | Objetivo específico | Necesidad | Estado |
|---|---|---|---|
| OE1 | Capturar los mensajes **en vivo** (bot) y **por lotes** (cada hora), sin duplicados | N1 | 🟡 Las dos capturas funcionan y no duplican. Falta que la ingesta corra sola cada hora en el servidor |
| OE2 | Etiquetar cada mensaje con intención, sentimiento y tema, sin perder mensajes si la IA falla | N2 | ✅ |
| OE3 | Un borrador de post de LinkedIn y un caso de éxito por cada logro, con la voz de la marca | N3 | ✅ Además, el post aprobado se puede publicar solo en LinkedIn (DEC-149; apagado por defecto) |
| OE4 | Responder dudas en vivo con los PDF y convertir las repetidas en una FAQ | N4 | ✅ |
| OE5 | Dashboard con sentimiento, temas y alertas | N5 | ✅ Desde T12, con una vista por rol (Comunidad y Contenido), la franja "Lo que hizo InsightEdu", la n en cada porcentaje y tema claro y oscuro, con el diseño del prototipo (DEC-153 a DEC-158) |
| OE6 | Panel con inicio de sesión para revisar, editar, aprobar o rechazar, con consentimiento | N6 | ✅ |
| OE7 | Guardar en OCI los activos generados y los aprobados | N7 | ✅ El 2026-10-09 se subieron 31 archivos sin errores, y el 2026-10-12 el dueño del bucket lo confirmó en su consola |
| OE8 | Todo con un comando, seguro y con pruebas | Transversal | 🟡 5 de 6 servicios en Docker, con claves por cliente, inicio de sesión y pruebas automáticas en cada pieza. Falta la ingesta como servicio |
| OE9 | Desplegarlo y ensayar la demo | Transversal | ⏸️ Diseñado, en pausa (sección 3, punto 3) |

Si falta tiempo, lo último que se recorta es OE1, OE3 y OE6.

## 3. Lo que falta, en orden

| # | Qué | Por qué importa | Dónde empezar |
|---|---|---|---|
| 1 | ✅ **Hecho (T11, 2026-10-10):** se borró el código que ya no se usaba en `agents/orquestador/`, sus variables de `config.py` y el `requirements.txt` viejo de la raíz (DEC-145, DEC-146) | Confundía a quien lee el código (personas o asistentes de IA) | [Informe T11](historico/tareas/T11-informe.md): qué se borró, qué se conservó y por qué |
| 2 | ✅ **Hecho (2026-10-12):** el dueño del bucket confirmó que están `generados/` y `aprobados/`, que los archivos no tienen datos de Discord, y que la PAR es de solo escritura y vence después de la entrega (DEC-129) | Cierra OE7 | — |
| 3 | **Desplegar y ensayar la demo**: una VM gratis de Oracle Cloud, Caddy con HTTPS y un subdominio de DuckDNS, la ingesta cada hora con `cron`, respaldos diarios, claves nuevas del servidor y un guion de demo de 10 minutos | Cierra OE1, OE8 y OE9 | La propuesta completa está en [historico/tareas/T10-despliegue-demo.md](historico/tareas/T10-despliegue-demo.md), y las decisiones en DEC-137 a DEC-140 |
| 4 | ✅ **Hecho (2026-10-12):** la PAR de OCI vence después de la entrega. Si la demo se corre más tarde, hay que revisarla de nuevo | Si vence, las subidas pasan a `ERROR` | [OPERACION.md](OPERACION.md) §12 |
| 5 | **Antes de las pruebas finales y de la demo, encender LinkedIn**: acordar la cuenta (perfil o página), conseguir un token vigente, hacer una publicación de prueba y apagarlo al terminar | Viene apagado (DEC-149): sin este paso, aprobar un post no publica nada | [OPERACION.md](OPERACION.md) §13 |
| 6 | **PDF de preguntas frecuentes de CommunityLab**: convertir el manual de servicio al cliente en un PDF corto y probarlo con `scripts/revisar_buscador_faq.py` | El bot podría responder dudas que hoy deriva a un mentor (clases grabadas, estudiar trabajando, preguntas técnicas) | [README de pdfs_en_revision](../agents/agent_faq/data/pdfs_en_revision/README.md) (DEC-152) |

### Mejoras posibles (🟡), si sobra tiempo

| Área | Mejora |
|---|---|
| Clasificación | Guardar en la base la razón de un `ERROR` (hoy solo queda en el registro); medir la calidad del clasificador con un conjunto de mensajes etiquetados a mano |
| Bot y Agente FAQ | Guardar la fuente que citó la IA (hoy se guarda el primer fragmento encontrado); no mostrar "escribiendo…" en `#logros`; liberar el hilo del Agente FAQ cuando se agota el tope |
| Agente-Mod | Exigir el largo que pide la guía de voz (los textos salen cortos); no mencionar reacciones que todavía no existen; probar otro modelo con `MOD_MODEL_NAME`; un botón "volver a generar" en el panel |
| FAQ semanal | Tutoriales y tips; un botón para reintentar una FAQ en `ERROR` |
| Panel | Mantener la sesión al recargar la página; avisar si dos personas editan el mismo borrador. (Las dos mejoras del dashboard, mostrar el tiempo de revisión y que la frustración ignore los mensajes viejos, se hicieron en T12) |
| Operación | Registros de la IA en nivel INFO; sus registros en OCI; integración continua (pruebas automáticas en cada PR) |

Los **riesgos aceptados** (⚠️) están en [DECISIONES.md](DECISIONES.md): por ejemplo, una URL PAR vieja en el historial público de git (DEC-41) y la regla de "respondida" del bot (DEC-79).

## 4. Cómo continuar el trabajo

1. **Entender antes de cambiar:** leer el [README](../README.md) (cómo levantarlo), [ARQUITECTURA.md](ARQUITECTURA.md) y las reglas de [AGENTS.md](../AGENTS.md).
2. **Una rama por cambio**, desde `main`, con un nombre que diga qué hace (por ejemplo, `mejora/razon-error-clasificacion`). Nunca un commit directo en `main`, y nunca cambiar la rama de otra persona (DEC-148).
3. **Respetar las reglas que no se rompen** ([AGENTS.md](../AGENTS.md)): los contratos solo crecen agregando, una migración aplicada nunca se edita, los secretos nunca van a git, las claves solo abren su puerta y nunca hay dos bots encendidos.
4. **Probar de verdad:** las pruebas de la pieza que se tocó, más las que ya existían. Ningún cambio está terminado sin pruebas que pasen.
5. **Documentar:** si el cambio decide algo, una fila en [DECISIONES.md](DECISIONES.md); si cambia cómo funciona, actualizar [ARQUITECTURA.md](ARQUITECTURA.md); si cierra un pendiente, actualizar este documento.
6. **Pull Request a `main`**, con qué cambia, por qué y cómo se probó.

## 5. Ramas de trabajo retiradas

La integración se hizo con una rama por tarea. Al terminar, todas se fusionaron en `main` y se borraron el 2026-10-10 para dejar el repositorio ordenado (DEC-144): **su contenido completo está en `main`**. Las ramas originales de cada equipo (`feature/java-core-api`, las de `ai-engine`, `feat/7-panel-minimo` y `feature/postman-docs-solo`) **se conservan sin cambios**. `feature/automatizacion-linkedin`, de otros integrantes, tampoco se toca: con el permiso de sus autores, su trabajo entró a `main` a través de `integracion/linkedin` (DEC-149), y la rama original se conserva sin cambios (DEC-148).

Para recrear una rama retirada: `git branch <nombre> <commit>`.

| Rama | Último commit | Qué contenía |
|---|---|---|
| `tarea/T01-modelo-datos` | `6034d64460644d905a0ab6e586bc02253616b047` | Modelo de datos con Flyway |
| `tarea/T02-formato-java-ia` | `5b7c63e9ee6e96308bb75e8e4b648600c770b7ad` | Contrato Java ↔ IA y clasificación con sentimiento y tema |
| `tarea/T03-puerta-lotes` | `c895af3720449248b4e496957c2218d81e6f032e` | Puerta de lotes con el contrato v1 y claves |
| `tarea/T04-clasificacion-java-ia` | `3ea907bb7d49d0a0dfd991cff8784a6a4116bde2` | Clasificación en segundo plano |
| `tarea/T05-bot-en-vivo` | `c815546f6da476a839852bb3d10b0ffb56f14cfc` | El bot pasa por Java |
| `tarea/T06-agente-mod` | `158ff7f5abb2818f0d4ad336f7f249a02fb1229f` | Agente-Mod |
| `tarea/T06b-faq-semanal` | `b8607897368f9e085991e263be3639508474fff1` | FAQ semanal |
| `tarea/T07-panel` | `d4a9f712cd8cc69b380ffef47d0e2093bc47605b` | Panel de curaduría |
| `tarea/T08-dashboard` | `b955cc95751afb5a7a8f0fd62d350446b7f142c9` | Dashboard |
| `tarea/T09-oci` | `c0f8f0d91ead7302128effaba72765fe21f96558` | Subida a OCI |
| `feature/discord-ingestion` | `b193554f73157b4e67fd351d383471562637cddd` | Ingesta de Discord y contrato v1 (antes de la integración) |
| `tarea/T11-limpieza-codigo` | Fusionada en la integración antes del Pull Request | Limpieza del código que ya no se usaba |
| `feature/integracion-arquitectura-3` | Fusionada en `main` por Pull Request | La integración completa |
| `integracion/linkedin` | `58c87c8` (fusionada en `main` por el PR #13 y borrada el 2026-10-14) | La publicación en LinkedIn de `feature/automatizacion-linkedin`, apagada por defecto, y el manual de servicio al cliente en revisión (DEC-149 a DEC-152) |
| `docs/cierre-oe7-dec144` | `092415e` (fusionada en `main` por el PR #11 y borrada el 2026-10-12) | El cierre de OE7, DEC-144 aplicada y la regla de ramas (DEC-148) |

La traza de cada tarea (qué se pidió, qué se hizo, cómo se probó y qué se decidió) está en [docs/historico/tareas/](historico/tareas/).
