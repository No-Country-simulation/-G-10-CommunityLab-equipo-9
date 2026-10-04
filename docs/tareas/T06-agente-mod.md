# T06 · Agente-Mod: borradores de LinkedIn y casos de éxito con la voz de CommunityLab

| Dato | Valor |
|---|---|
| Fase del plan | 4 · Generar contenido ([análisis §9](../ANALISIS_INGENIERIA_PROPUESTA_3.md#9-prioridades-y-orden)) |
| Objetivos | **OE3** (un borrador de post de LinkedIn y un caso de éxito por cada logro, con la voz de la marca). Es "el corazón del negocio de Marketing" (PDF de la propuesta 3, §8) |
| Hallazgos y decisiones que resuelve | N3 del PDF, DEC-53 y la observación de T02 sobre los logros de aprendizaje |
| Tamaño | L (un agente nuevo en la IA, una puerta nueva, una tarea programada en Java y una migración) |
| Modelo de Claude recomendado | **Opus 5.5**: crea una pieza nueva, amplía un contrato y tiene concurrencia en Java |
| Depende de | T04 ✅ (el patrón de la clasificación en segundo plano: reserva con `SKIP LOCKED`, guardas por `actualizado_en` y reintentos) y T05 ✅ (la API key de la IA en `/v1/…`). **Reutilizarlos** |
| Rama | `tarea/T06-agente-mod` |
| Decisiones previas 👤 | Las de la sección 1.1, validadas por Harrison el 2026-10-04 |

## 1. Objetivo

Que cada logro que comparte un alumno (`intencion = TESTIMONIO`) se convierta, sin que nadie lo pida, en **dos borradores listos para revisar**: un **post de LinkedIn** y un **caso de éxito**, escritos con la voz de CommunityLab y guardados en `borradores` como `PENDIENTE`.

Antes de redactar, la IA decide si el logro **vale la pena publicarse** y deja escrito el motivo. Así, Marketing no pierde tiempo con logros menores.

Nada se publica: Marketing revisa, edita y aprueba en el panel (T07, N6).

### 1.1 Decisiones previas 👤 (2026-10-04)

| # | Pregunta | Decisión | Descartada |
|---|---|---|---|
| 1 | ¿Cuándo se escribe el borrador? (DEC-80) | **Automático:** una tarea programada en Java busca los logros sin borrador y se los pide a la IA, igual que la clasificación de T04 | A pedido desde el panel: el panel todavía no existe |
| 2 | ¿Todos los logros generan borrador? (DEC-53) | **La IA decide** si es publicable (contratación, entrevista, proyecto terminado, beca, graduación, superación de una dificultad) y deja escrito el motivo. Si no lo es, no hay borrador | Generar para todos y que Marketing descarte |
| 3 | ¿Cómo se nombra al alumno? (DEC-81) | **Solo el primer nombre** ("Camila"). El `Reglamento de Comunicaciones` de CommunityLab prohíbe publicar nombres completos sin consentimiento, y el panel lo pedirá antes de aprobar (D6) | El nombre completo; el anonimato |
| 4 | ¿Cómo le pide Java el borrador a la IA? (DEC-82) | **Una puerta nueva, `POST /v1/generar`**, separada de la que clasifica. **Solo agrega** al contrato Java ↔ IA | Redactar dentro de `/v1/procesar`: mezcla dos trabajos y hace más lenta la clasificación |

Decisiones del chat principal (Harrison no se opuso):
- **DEC-83:** la FAQ semanal va en otra ficha (T06b).
- **DEC-84:** la guía de voz la redacta este chat, la aprueba Harrison y queda en un archivo que la IA lee.
- **DEC-85:** el modelo de Gemini que redacta se puede configurar.

## 2. Contexto que hay que leer

| Qué | Dónde |
|---|---|
| N3: qué lee el Agente-Mod (texto para las citas, reacciones y respuestas) y dónde guarda el borrador | [PDF de la propuesta 3](../referencias/Propuesta_3_Arquitectura_InsightEdu.pdf), §6 (N3) y §7 (el caso de Camila) |
| Lo que pide el brief: posts *"persuasivos y listos para publicar… respetando la voz de la marca"* y la *"extracción de citas"* (`textoOriginal`, sin corregir) | [PROJECT_BRIEF.md](../../ingestion/discord/docs/PROJECT_BRIEF.md) §2.3 y §5 |
| La institución y sus reglas de comunicación (prohíbe publicar nombres completos sin consentimiento) | `agents/agent_faq/data/pdfs/10_Reglamento_de_Comunicaciones.pdf` y `06_Manual_del_Estudiante_V3.pdf` |
| La tabla `borradores` (tipos `POST_LINKEDIN` y `CASO_EXITO`, `texto_ia`, `estado`, `tokens_in`, `tokens_out`) | `backend-java/src/main/resources/db/migration/V1__modelo_inicial.sql`, `model/Borrador.java` |
| El patrón que hay que copiar: reserva, guardas, reintentos y registros sin textos | `backend-java/.../clasificacion/` ([T04-informe.md](T04-informe.md)) |
| El contrato Java ↔ IA, que esta tarea amplía | [JAVA_IA_v1.md](../contratos/JAVA_IA_v1.md) y su JSON Schema |
| D5 (un solo proveedor: Gemini), D6 (consentimiento en el panel) y DEC-53 | [DECISIONES.md](../DECISIONES.md) |
| La observación de T02 ("por fin entendí recursividad" salió `TESTIMONIO`) | [README de tareas](README.md) |

## 3. Alcance: qué entra

### Parte A · La IA: el Agente-Mod y su puerta

1. **El Agente-Mod**, en `agents/agent_mod/` (la carpeta que `CLAUDE.md` marca como "no existe todavía"). Hace **una** llamada a Gemini con salida estructurada:

   | Campo | Qué es |
   |---|---|
   | `publicable` | `true` si el logro vale un post (decisión 2) |
   | `motivo` | Una frase: por qué sí o por qué no |
   | `postLinkedin` | El borrador del post, o `null` si no es publicable |
   | `casoExito` | El borrador del caso de éxito, con una estructura fija (situación, desafío, logro, cita textual y cierre), o `null` |

   Reglas que la ficha exige:
   - **Al LLM le llega solo el primer nombre del autor** (decisión 3). El agente lo saca de `autor.nombreVisible` y **no** envía `nombreUsuario`, IDs, el nombre completo ni los nombres de quienes respondieron. Es una defensa en el código, además de la regla del prompt.
   - La **cita** se toma literal de `textoOriginal` (brief: *"extracción de citas"*). La IA **no inventa** datos que no estén en el mensaje (empresas, cifras, fechas).
   - El texto del mensaje es un **dato**: nunca se siguen instrucciones que vengan dentro de él (como en el Etiquetador).
   - Usa Gemini (D5). El modelo se configura con `MOD_MODEL_NAME`; por defecto, el mismo que clasifica (DEC-85). Su tiempo máximo tiene que caber en los 30 s de lectura de Java.
2. **La guía de voz de CommunityLab** (DEC-84): un archivo de texto **dentro del Agente-Mod** (por ejemplo, `agents/agent_mod/guia_de_voz.md`), para que entre en la imagen de Docker sin cambiar el `Dockerfile`. Tiene que decir:
   - el tono (por ejemplo: cercano, motivador y profesional, en español neutro);
   - qué hacer y qué evitar;
   - el largo de cada borrador, los emojis y hashtags permitidos, y la estructura del caso de éxito.

   La IA lo lee al arrancar, así que una institución real solo cambia el archivo. **El chat de tarea redacta un primer borrador y se lo muestra a Harrison antes de usarlo** (👤 lo aprueba él).
3. **La puerta `POST /v1/generar`** en `agents/orquestador/api.py`:
   - queda protegida por el control de `X-Api-Key` que ya existe para `/v1/…` (S2);
   - recibe el mensaje del logro (la caja del contrato v1, tal cual) y, opcionalmente, las cajas de las respuestas que recibió (`respondeA`), con un tope de cantidad;
   - devuelve `publicable`, `motivo`, los dos textos (si corresponde), el estado (`OK` o `ERROR`) y las métricas (duración y tokens);
   - errores con el formato común: 401, 422 y 500. Un fallo del LLM es `ERROR`, **nunca** un borrador vacío ni inventado (F4).
4. **Contrato:** se documenta en [JAVA_IA_v1.md](../contratos/JAVA_IA_v1.md), en una sección nueva, con un ejemplo de pedido y de respuesta, y se regenera el JSON Schema. **Solo agrega**: `/v1/procesar` no cambia.

### Parte B · Java: la generación en segundo plano

5. **Migración `V4__…`** (nunca editar V1, V2 ni V3), con lo que haga falta para seguir la generación de cada mensaje:
   - un estado (por ejemplo, `generacion_estado`: `GENERADO`, `NO_PUBLICABLE` o `ERROR`; vacío = todavía no se intentó);
   - el motivo, los intentos, la fecha y una reserva propia (no reutilizar `reservado_hasta`, que es de la clasificación);
   - una protección para que **no haya dos borradores pendientes del mismo tipo para el mismo mensaje** (por ejemplo, un índice único parcial).

   El upsert de la ingesta no toca estas columnas.
6. **Tarea programada de generación** (`@Scheduled`, con intervalo, tanda chica y máximo de intentos configurables):
   - toma los mensajes con `estado_clasificacion = OK`, `intencion = TESTIMONIO` y `autor_tipo = persona` que todavía no tienen generación, y los reserva con `SKIP LOCKED`;
   - le pide a la IA el borrador **sin transacción abierta**, con un método nuevo de `NlpDataClient` (mismas cabeceras y tiempos);
   - incluye las respuestas que recibió el mensaje (las filas con `responde_a` igual a su `discord_id`), con un tope.

   Qué se guarda según la respuesta:

   | Respuesta de la IA | Qué se guarda |
   |---|---|
   | `publicable = true` | **Dos** filas en `borradores` (`POST_LINKEDIN` y `CASO_EXITO`), `PENDIENTE`, con `texto_ia` y tokens; generación `GENERADO`. Todo en una transacción y con la guarda de T04 (el mensaje no cambió y sigue siendo `TESTIMONIO` `OK`) |
   | `publicable = false` | Ningún borrador; generación `NO_PUBLICABLE` y el motivo |
   | `ERROR`, 500, tiempo agotado o IA caída | Suma un intento y libera la reserva; al máximo, `ERROR`. Nada a medias |

7. **Registros sin textos** (S11): cuántos tomó, cuántos generó, cuántos no eran publicables, cuántos fallaron y cuánto tardó.
8. **`docs/OPERACION.md`:** las variables nuevas y una consulta de solo lectura para ver los borradores.

## 4. Fuera de alcance

- El panel: listar, editar, aprobar, rechazar o volver a generar borradores, y la casilla de consentimiento (T07, D6). **No** se crean puertas de Java para los borradores.
- La FAQ semanal (T06b) y OCI (T09).
- Publicar en LinkedIn: lo hace Marketing, a mano, después de aprobar.
- Cambiar el clasificador, el bot, el contrato v1 o `/v1/procesar`.
- Qué pasa con los borradores si después se edita el mensaje del logro: se anota en el informe.
- **No ejecutar `simulate_students.py`** ni encender un segundo bot.

## 5. Pruebas exigidas

**Python, IA** (con un LLM falso, sin gastar Gemini):

| # | Caso | Resultado esperado |
|---|---|---|
| 1 | Un logro publicable | `publicable = true`, con los dos textos |
| 2 | Un logro menor ("por fin entendí recursividad", si el LLM falso lo marca así) | `publicable = false`, con motivo y sin textos |
| 3 | El LLM falla o se agota el tiempo | `ERROR`, sin textos |
| 4 | Lo que recibe el LLM | Tiene el primer nombre y **no** tiene el nombre completo, el `nombreUsuario`, los IDs ni los nombres de quienes respondieron |
| 5 | La guía de voz | Llega al LLM desde el archivo |
| 6 | `/v1/generar` sin clave / con un cuerpo inválido | 401 / 422, con el formato común |
| 7 | Las 38 pruebas de la IA | Siguen pasando |

**Java** (con PostgreSQL real e IA simulada):

| # | Caso | Resultado esperado |
|---|---|---|
| 1 | Un `TESTIMONIO` `OK` sin generación | 2 borradores `PENDIENTE` y `GENERADO` |
| 2 | La IA dice "no publicable" | `NO_PUBLICABLE` con motivo y 0 borradores |
| 3 | La IA falla | Un intento más y la reserva liberada; al máximo, `ERROR` |
| 4 | Dos ejecuciones a la vez | No toman el mismo mensaje |
| 5 | El mensaje cambió mientras la IA redactaba | No se guarda nada |
| 6 | Comentarios, dudas, mensajes de bots o mensajes `PENDIENTE` | No se envían |
| 7 | Correr la tarea otra vez | No duplica borradores |
| 8 | Un logro con respuestas | Las respuestas viajan en el pedido |
| 9 | Las 80 pruebas anteriores | Siguen pasando |

**Prueba real, la corre Harrison** (gasta unas 15 llamadas a Gemini):
1. `docker compose up -d --build`. La tarea procesará los logros que ya están en la base (unos 10).
2. En `#logros`, escribir un logro nuevo (por ejemplo, "¡Me contrataron como QA trainee después de 6 meses de bootcamp!") y otro menor ("por fin entendí recursividad").
3. Consulta de solo lectura: estados de generación, y cada borrador con su tipo, su estado y los primeros 300 caracteres. Comprobar con otra consulta que **ningún borrador contiene el nombre completo** del autor.
4. Harrison lee un post y un caso de éxito y dice si suenan como CommunityLab, según la guía. Se pegan las salidas en el informe.

## 6. Criterios de terminado

- [ ] Existe el Agente-Mod, con la guía de voz aprobada por Harrison, y la puerta `/v1/generar` protegida con la clave.
- [ ] Cada logro publicable tiene sus dos borradores `PENDIENTE`, los no publicables tienen su motivo, y un fallo no deja nada a medias ni duplicado.
- [ ] Ningún borrador lleva el nombre completo del alumno, y el LLM no lo recibe.
- [ ] `JAVA_IA_v1.md` y su JSON Schema documentan `/v1/generar`, y `/v1/procesar` no cambió.
- [ ] Las pruebas de Java y Python pasan, y la prueba real muestra los borradores en la base (🧪 con la salida en el informe).
- [ ] El informe `docs/tareas/T06-informe.md` está completo, y no se tocó nada fuera del alcance.

## 7. Comandos de git para Harrison

**Al empezar**, desde `C:\Users\LENOVO\Documents\Cursos\No Country\Hackaton ONE 10\insightedu-lab`:
```
git switch feature/integracion-arquitectura-3
git pull
git switch -c tarea/T06-agente-mod
```

**Al terminar:** el chat de tarea da los comandos de commit (un solo `-m`, **sin** `Co-Authored-By`: DEC-65). Se sugiere un commit por parte (A y B). Después:
```
git push -u origin tarea/T06-agente-mod
```

Luego le dices al chat principal **"T06 terminó"**.

## 8. Cómo abrir el chat de esta tarea

1. En VS Code, abrir un chat nuevo de Claude Code **en esta misma carpeta**.
2. Elegir el modelo **Opus 5.5** con `/model`.
3. Primer mensaje: *"Eres el chat de la tarea T06. Lee CLAUDE.md y docs/tareas/T06-agente-mod.md y empieza."*

⚠️ **Nunca pegues el contenido de un `.env` en el chat.** Para revisarlo, usa `Get-Content .env | ForEach-Object { ($_ -split '=')[0] }`, que muestra solo los nombres de las variables.
