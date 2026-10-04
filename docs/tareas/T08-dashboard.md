# T08 · Dashboard: sentimiento, temas en tendencia y alertas para el CM

| Dato | Valor |
|---|---|
| Fase del plan | 5 · Panel y dashboard ([análisis §9](../ANALISIS_INGENIERIA_PROPUESTA_3.md#9-prioridades-y-orden)) |
| Objetivos | **OE5**: un dashboard con el sentimiento, los temas en tendencia y alertas de deserción, frustración y dudas sin responder (N5) |
| Hallazgos que resuelve | N5 del PDF (5 indicadores), C5 (consultas en Java) y observaciones de T01, T04, T05, T06 y T07 ([README](README.md)) |
| Tamaño | M (consultas de lectura en Java y una página nueva del panel) |
| Modelo de Claude recomendado | **Sonnet 5.5**: es acotada y reutiliza todo lo de T07. **Opus 5.5** si hay dudas con las consultas |
| Depende de | T07 ✅ (el panel con varias páginas, `cliente_java.py`, la clave `panel`, la ruta normalizada y `PANEL_JAVA_v1`). **Reutilizarlos** |
| Rama | `tarea/T08-dashboard` |
| Decisiones previas 👤 | Las de la sección 1.1, validadas por Harrison el 2026-10-04 |

## 1. Objetivo

Que el CM, después de iniciar sesión en el mismo panel, abra la página **"Dashboard"** y vea:
- el clima de la comunidad (sentimiento en el tiempo);
- los temas del momento;
- **a quién ayudar**: alertas de deserción y de frustración, y las dudas sin responder.

📘 El PDF dice que N5 *"no necesita IA nueva: usa lo que N1 y N2 ya guardaron"*: todo sale de las etiquetas que ya están en `mensajes`.

**Dato que define el diseño** (🧪 consulta del 2026-10-04):
- hay 52 mensajes de 10 personas, y **38 son de un solo día** (2026-09-28);
- con 14 días de umbral, la alerta de deserción no marcaría a nadie;
- por eso hay vista por día y un umbral ajustable.

### 1.1 Decisiones previas 👤 (2026-10-04)

| # | Pregunta | Decisión | Descartada |
|---|---|---|---|
| 1 | Umbral de deserción (DEC-119) | **14 días por defecto, ajustable en la página** con un selector | Fijo en 14: con los datos de hoy no habría alertas |
| 2 | ¿Qué datos se muestran? (DEC-120) | **Solo los reales**, con un selector **día / semana**. Los datos de demo más largos, si hacen falta, se deciden en T10 con el guion (Q7) | Cargar ahora mensajes de prueba ya etiquetados: se mezclarían con los reales |
| 3 | ¿Cuándo hay alerta de frustración? (DEC-121) | Si la persona tiene **un mensaje `MUY_NEGATIVO`** en el período, **o 2 negativos (`NEGATIVO` o `MUY_NEGATIVO`) entre sus últimos 3 mensajes** | Solo 2 negativos seguidos |
| 4 | ¿Cómo pide el panel los datos? (DEC-122) | **Puertas nuevas de solo lectura en `PANEL_JAVA_v1`**, con la misma clave `panel`. Solo agrega al contrato | Un contrato aparte |

Decisiones del chat principal (Harrison no se opuso), **DEC-123**:
- Java calcula y el panel solo dibuja, con los gráficos de Streamlit y sin librerías nuevas;
- solo cuentan los mensajes `OK` de personas;
- el tema `otro` se puede filtrar;
- una duda está **atendida** si el bot la respondió (`RESPONDIDA`) o si **una persona distinta del autor** le contestó (`respondeA`). Una duda `DERIVADA` sigue sin responder hasta que alguien la conteste;
- las alertas muestran el nombre visible del alumno (el panel tiene inicio de sesión).

## 2. Contexto que hay que leer

| Qué | Dónde |
|---|---|
| Los 5 indicadores y cómo se calcula cada uno | [PDF de la propuesta 3](../referencias/Propuesta_3_Arquitectura_InsightEdu.pdf), §6 (N5) y [análisis §5](../ANALISIS_INGENIERIA_PROPUESTA_3.md) (tabla de indicadores) |
| Las columnas: `fecha`, `autor_id`, `autor_tipo`, `estado_clasificacion`, `intencion`, `sentimiento`, `tema`, `responde_a`, `respuesta_estado`, `respondido_en`, y el nombre visible dentro de `contrato` | Migraciones V1 a V3 |
| El panel: páginas, cliente, estilos y cómo se muestran los textos | `panel/` ([T07-informe.md](T07-informe.md)) |
| El contrato del panel, que esta tarea amplía | [PANEL_JAVA_v1.md](../contratos/PANEL_JAVA_v1.md) |
| Las observaciones que pasan a esta tarea | [README de tareas](README.md) (filas que dicen "T08" o "Fase 5") |

## 3. Alcance: qué entra

### Parte A · Java

1. **Puertas de solo lectura** para el dashboard, dentro de las que solo abre la clave `panel`. Por ejemplo, bajo `/api/v1/dashboard/…`: si se usa un prefijo nuevo, hay que sumarlo a `CLIENTE_POR_PREFIJO` de `ApiKeyFilter` y a la segunda capa del controlador. Todas reciben el período (desde, hasta) y, donde corresponda, la granularidad (día o semana) y si se excluye el tema `otro`.

   | Indicador | Qué devuelve | Regla |
   |---|---|---|
   | **Sentimiento en el tiempo** | Por día o por semana, la cantidad de cada sentimiento | Solo `estado_clasificacion = OK`, `autor_tipo = persona` y con sentimiento |
   | **Temas en tendencia** | Por tema, la cantidad en el período y la del período anterior de igual largo (para ver si sube o baja) | Ídem |
   | **Alerta de deserción** | Las personas cuyo último mensaje tiene más de N días (N entra como parámetro, 14 por defecto): nombre visible, último mensaje y cuántos escribió antes | Personas que escribieron alguna vez, aunque no en el período |
   | **Alerta de frustración** | Las personas con un `MUY_NEGATIVO` en el período, o con 2 negativos entre sus últimos 3 mensajes (DEC-121): nombre, cuántos negativos y la fecha del último. **Sin textos** en la respuesta de la lista | Solo mensajes `OK` |
   | **Dudas sin responder** | Las `PREGUNTA_FAQ` sin atender después de N horas (24 por defecto, parámetro), con fecha, tema, si fue `DERIVADA` y el texto de la duda (para que el CM la conteste) | Atendida = `RESPONDIDA` del bot o una respuesta de otra persona (DEC-123) |

   Además, unos **totales** para la cabecera: mensajes, personas activas, dudas, logros y borradores pendientes.
2. **Rendimiento:** consultas SQL con los índices existentes (`fecha`, `autor_id` e `intencion`, de V1). Si hace falta uno nuevo, va en una **`V7__…`**. Topes de período (por ejemplo, 1 año) y de cantidad de filas en las listas.
3. **Contrato:** agregar las puertas a [PANEL_JAVA_v1.md](../contratos/PANEL_JAVA_v1.md), con un ejemplo cada una. **Solo agrega.**
4. Si hace falta, la entidad `Mensaje` suma las columnas de V3 y V4 (observación de T05, T06 y T07), o se usa SQL directo, como en el resto de las consultas.

### Parte B · El panel

5. **Página "Dashboard"** en el panel de T07:
   - **controles:** el período (por defecto, los últimos 30 días), día o semana, "excluir el tema otro", el umbral de deserción (14 por defecto) y las horas para "sin responder" (24 por defecto);
   - **cabecera** con los totales, usando el estilo de métricas del panel viejo;
   - **gráficos con lo que trae Streamlit** (por ejemplo, `st.bar_chart` o `st.line_chart`): sentimiento en el tiempo y temas;
   - **tres tablas de alertas:** deserción, frustración y dudas sin responder. Los textos se muestran **escapados**, como en T07;
   - un texto corto bajo cada indicador que diga cómo se calcula (por ejemplo, "solo mensajes clasificados `OK`").
6. Si una consulta falla o no hay datos, la página lo dice con claridad y no se rompe.

## 4. Fuera de alcance

- Cargar datos de demo (T10, DEC-120). OCI (T09).
- IA nueva, cambios en el clasificador, en el bot o en la ingesta.
- Medir el tiempo de curaduría (observación de T07: se mide desde que se abre el borrador): **no** se muestra en esta tarea; queda como 🟡.
- Exportar a Excel, enviar alertas por correo o a Discord.
- **No ejecutar `simulate_students.py`** ni encender un segundo bot.

## 5. Pruebas exigidas

**Java** (PostgreSQL real, con datos armados en la prueba):

| # | Caso | Resultado esperado |
|---|---|---|
| 1 | Sentimiento por día y por semana | Las cantidades correctas; no cuentan los mensajes `PENDIENTE` ni `ERROR`, los de bots ni los que no tienen sentimiento |
| 2 | Temas, con y sin el tema `otro` | Las cantidades y la comparación con el período anterior |
| 3 | Deserción con 14 días y con 3 días | Aparecen las personas correctas |
| 4 | Frustración: un `MUY_NEGATIVO`; 2 negativos de los últimos 3; 1 negativo de 3 | Alerta, alerta y sin alerta |
| 5 | Dudas: respondida por el bot, contestada por otra persona, contestada solo por su autor, `DERIVADA` sin respuesta, reciente | Atendida, atendida, sin responder, sin responder y fuera (menos de N horas) |
| 6 | Claves: sin clave / con la de `bot` / con una ruta disfrazada | 401 / 403 / 403 |
| 7 | Un período inválido o demasiado largo | 422 |
| 8 | Las 143 pruebas anteriores | Siguen pasando |

**Python, panel:** la página dibuja con un cliente simulado; los controles envían los parámetros correctos; sin datos, muestra un aviso; un texto con `<script>` en una duda se muestra escapado; las 37 pruebas del panel siguen pasando.

**Prueba real, la corre Harrison** (no gasta Gemini):
1. `docker compose up -d --build api-java panel`.
2. Entrar al panel, abrir "Dashboard" y mirar los gráficos por día y por semana.
3. Bajar el umbral de deserción a 3 días y comprobar que aparecen personas.
4. Revisar las alertas de frustración y las dudas sin responder: ¿tienen sentido con lo que se sabe de los mensajes?
5. Captura o descripción en el informe, y una consulta de solo lectura que confirme uno de los números.

## 6. Criterios de terminado

- [ ] La página "Dashboard" muestra los 5 indicadores y los totales, con los controles de la sección 3.
- [ ] Las cuentas siguen las reglas: solo `OK` y personas, frustración según DEC-121, dudas atendidas según DEC-123.
- [ ] Las puertas nuevas solo aceptan la clave `panel` y están en `PANEL_JAVA_v1.md`.
- [ ] Las pruebas de Java y Python pasan, y la prueba real muestra los indicadores con los datos reales (🧪 en el informe).
- [ ] El informe `docs/tareas/T08-informe.md` está completo, y no se tocó nada fuera del alcance.

## 7. Comandos de git para Harrison

**Al empezar**, desde `C:\Users\LENOVO\Documents\Cursos\No Country\Hackaton ONE 10\insightedu-lab`, **después de subir la ficha** y con `git status` en `working tree clean`:
```
git switch feature/integracion-arquitectura-3
git pull
git switch -c tarea/T08-dashboard
```

**Al terminar:** el chat de tarea da los comandos de commit (un solo `-m`, **sin** `Co-Authored-By`: DEC-65), uno por parte (A y B). Después:
```
git push -u origin tarea/T08-dashboard
```

Luego le dices al chat principal **"T08 terminó"**.

## 8. Cómo abrir el chat de esta tarea

1. En VS Code, abrir un chat nuevo de Claude Code **en esta misma carpeta**.
2. Elegir el modelo **Sonnet 5.5** con `/model` (u **Opus 5.5** si prefieres más margen).
3. Primer mensaje: *"Eres el chat de la tarea T08. Lee CLAUDE.md y docs/tareas/T08-dashboard.md y empieza."*

⚠️ **Nunca pegues el contenido de un `.env` ni tu contraseña del panel en el chat.**
