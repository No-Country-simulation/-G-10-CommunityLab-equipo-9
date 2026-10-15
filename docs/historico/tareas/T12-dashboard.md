# T12 · Dashboard por rol: KPIs de Comunidad y de Contenido, con tema claro y oscuro

> Esta ficha **sí es la orden de trabajo vigente** de T12, aunque viva en `docs/historico/tareas/`. Para todo lo demás manda [AGENTS.md](../../../AGENTS.md).

| Dato | Valor |
|---|---|
| Objetivos | **OE5** (dashboard) y **OE6** (panel), mejorados para el usuario final. Demuestra la "validación de mercado" del brief con datos |
| Usuarios | **Community Manager** (vista Comunidad) y **Marketing** (vista Contenido) |
| Tamaño | L: puertas de solo lectura en Java, el contrato del panel y la página Dashboard rehecha |
| Modelo de Claude recomendado | **Opus 5.5**: toca Java, el contrato, el panel y el tema, con reglas analíticas finas |
| Depende de | T08 ✅ (las 6 puertas del dashboard, `DashboardApiTest`, `paginas/dashboard.py`). **Reutilizar todo lo que se pueda** |
| Rama | `tarea/T12-dashboard` (ya creada desde `main`) |
| Prototipo aprobado | [Prototipo del panel](https://claude.ai/artifact/MSvJegGQj1HkaFyXgM2s3f), pantallas "Dashboard · Comunidad" y "Dashboard · Contenido" (privado: si no lo puedes abrir, guíate por esta ficha, que lo describe completo) |
| Decisiones previas 👤 | Las de la sección 1.1, validadas por Harrison el 2026-10-14 |

## 1. Objetivo

Que la página **Dashboard** del panel deje de ser una lista de números técnicos y responda, para cada rol, **qué pasa, qué decidir y a quién atender**. Tiene dos vistas:

- **Comunidad (CM):** cómo está el clima de los alumnos, si el bot ayuda, quién espera respuesta, a quién escribir y qué falta en los documentos;
- **Contenido (Marketing):** cuánto trabajo hay pendiente, cuánto tarda la revisión, si la IA propone cosas útiles y qué se aprobó.

Las dos empiezan con la franja **"Lo que hizo InsightEdu en este período"**: el valor del producto para la institución y el jurado.

**Dato que define el diseño** (🧪 consultas del 2026-10-14): hay 64 mensajes de 11 personas en 3 semanas, y el 83 % es de la primera. Por eso **cada porcentaje e índice muestra su n**.

### 1.1 Decisiones previas 👤 (2026-10-14)

| # | Decisión | Detalle |
|---|---|---|
| 1 | Usuarios | Marketing y el CM |
| 2 | Base de los KPI | La "validación de mercado" del brief oficial: el contenido de los usuarios convierte más, la IA elimina el trabajo manual, equipos chicos publican a diario y el sentimiento mueve la adquisición y la retención. El "hasta 4 veces" del brief es un dato del brief: **nunca** se muestra como resultado nuestro |
| 3 | Orden en pantalla | Franja de valor → **máximo 4 tarjetas** por vista → 2 o 3 gráficos → listas de acción. P5 (OCI) va a la barra lateral |
| 4 | P1, horas ahorradas | Es una **estimación** y el panel lo dice junto al número: *"Estimado: supone 30 min por historia encontrada y redactada a mano, menos la revisión en el panel"*. Los 30 min son configurables (`PANEL_MINUTOS_POR_HISTORIA`, 30 por defecto) |
| 5 | Reglas analíticas | **Siempre la n** junto a cada porcentaje o índice; **mediana** para los tiempos; **alumnos separados de mentores** en los KPI de comunidad; el % del bot **sobre las dudas que vio el bot** (respondidas + derivadas), no sobre todas; período por defecto de 30 días con atajos de 7 y 90. **No** hay muestra mínima y **no** se limpian los datos de prueba: la demo muestra la efectividad con los datos del servidor de pruebas, tal como están |
| 6 | Deserción | Se queda en 14 días. Con los datos de hoy marca 7 de 9 alumnos (el servidor de pruebas está quieto), y la tarjeta lo explica |
| 7 | Tema claro y oscuro | Entra en esta tarea, con el selector de tema de Streamlit y los colores de los gráficos validados para los dos fondos |
| 8 | Mejoras de ESTADO §3 | Entran aquí: **mostrar el tiempo de revisión** y que **la alerta de frustración ignore los mensajes viejos**. Las otras dos (sesión al recargar y reintentar la FAQ en `ERROR`) van en T13 |
| 9 | Fuera | M12 "publicados en LinkedIn" (T13, con su migración `V9`), la página Borradores (T13), la ingesta y el aviso "Datos al día" (T14) |

La tarea suma estas filas a [DECISIONES.md](../../DECISIONES.md): **DEC-153** (los KPI por rol y su orden, decisiones 1 a 3), **DEC-154** (P1 y su supuesto), **DEC-155** (las reglas analíticas), **DEC-156** (el tema claro y oscuro) y **DEC-157** (la frustración solo con mensajes del período). DEC-124 se actualiza: el sentimiento y los temas ahora aceptan un filtro de rol.

## 2. Los KPI elegidos

"¿Existe?" = **Sí**: el panel ya lo recibe · **Nuevo**: el dato está en la base, pero falta en una puerta (sección 3). El "valor hoy" sirve para la prueba real (sección 5), y cambia si entran datos nuevos o pasan los días.

### 2.1 Franja "Lo que hizo InsightEdu en este período" (las dos vistas)

| # | KPI | Cálculo | ¿Existe? | Valor hoy |
|---|---|---|---|---|
| P1 | Horas ahorradas a Marketing (estimado) | (minutos por historia − mediana de revisión de los posts) × logros con su post aprobado. Con el supuesto escrito debajo | Nuevo | ≈ 4,4 h ((30 − 1) min × 9) |
| P4 | Historias encontradas solas | Logros publicables, sobre los mensajes de personas y los logros del período | Nuevo | 9 (de 64 mensajes y 16 logros) |

### 2.2 Vista Comunidad (CM)

| Nivel | # | KPI | Cálculo | ¿Existe? | Valor hoy |
|---|---|---|---|---|---|
| Tarjeta | C2 + C1 | Clima de los alumnos (y de toda la comunidad, debajo) | (% positivos + muy positivos) − (% negativos + muy negativos), de −100 a +100, con su n. Solo alumnos en C2; todas las personas en C1. Cambio frente al período anterior **solo si ese período tiene datos**; si no, decirlo | Nuevo (filtro de rol) | +29 (n = 35) · +31 (n = 61) · sin período anterior |
| Tarjeta | C4 | Dudas que respondió el bot | Respondidas / (respondidas + derivadas), con el n. Debajo: el tiempo medio de reacción del bot, cuántas derivó y cuántas llegaron por lote sin pasar por el bot | Nuevo | 40 % (4 de 10) · 6 s · 6 derivadas · 17 por lote |
| Tarjeta | C5 | Dudas sin respuesta (más de N horas) | La puerta `dudas-sin-responder` que ya existe | Sí | 14 de 18 |
| Tarjeta | C7 + C8 | Alumnos que necesitan apoyo | Posible deserción (con el total de alumnos) y posible frustración, con una línea que explica el umbral | Sí | 7 de 9 · 2 |
| Gráfico | C3 | Clima de los alumnos por semana (o por día) | **Barras divergentes**: negativos a la izquierda, positivos a la derecha, neutro partido al medio; índice y n por fila; una tabla con los números debajo, plegada | Nuevo (filtro de rol) | Semana del 28 sep: +28 (n = 32) · 5 oct: +33 (n = 3) |
| Gráfico | C6 | Alumnos activos | Alumnos con al menos un mensaje en los últimos 7 y 30 días, sobre el total de alumnos | Nuevo | 2 de 9 · 9 de 9 |
| Gráfico | C9 | De qué hablan los alumnos | Barras horizontales ordenadas, un solo color, con el valor en la punta | Nuevo (filtro de rol) | Contenido del curso 9, herramientas y entorno 7, empleo 4, comunidad 4… |
| Lista | C5 | Esperan respuesta | Las dudas sin responder, con un botón **"Abrir en Discord"** | Nuevo (servidor y canal) | 14 |
| Lista | C7 + C8 | A quién escribir | Los nombres de deserción y de frustración, con su motivo | Sí | 9 |
| Lista | C12 | Qué falta en los documentos | Dudas derivadas por el bot, contadas por tema | Nuevo | 6: contenido del curso 2, y evaluaciones, inscripciones, proyectos y otro, 1 cada uno |

### 2.3 Vista Contenido (Marketing)

| Nivel | # | KPI | Cálculo | ¿Existe? | Valor hoy |
|---|---|---|---|---|---|
| Tarjeta | M1 + M2 | Por revisar | Borradores `PENDIENTE` por tipo, y cuántos días lleva esperando el más antiguo. Botón a Borradores | Nuevo (por tipo y antigüedad) | 3 (2 casos de éxito y 1 FAQ) · 9 días |
| Tarjeta | M5 | Tiempo de revisión | **Mediana** de `tiempo_curaduria_seg` de los posts, con el n. Debajo, el caso de éxito y la FAQ con su n | Nuevo | Post 62 s (n = 9) · caso 5 s (n = 7) · FAQ 1.000 s (n = 1) |
| Tarjeta | M4 | Tasa de aprobación | Aprobados / (aprobados + rechazados), con el n | Nuevo | 94 % (16 de 17) |
| Tarjeta | M9 | Del logro al contenido aprobado | Mediana de (aprobación del post − fecha del mensaje del logro), con el n | Nuevo | 6 días (n = 9) |
| Gráfico | M6 + M7 | De logro a contenido aprobado | Embudo de 3 barras: logros → publicables según la IA (con el %) → aprobados por Marketing (con el %), y los no publicables explicados | Nuevo | 16 → 9 (56 %) → 9 (100 %) |
| Gráfico | M8 | Contenido aprobado por semana | Columnas por semana de aprobación (todos los tipos), con el valor arriba | Nuevo | 4 · 9 · 3 (semanas del 28 sep, 5 oct y 12 oct) |
| Lista | M11 | Listos para publicar | Los aprobados recientes, con el destino de cada tipo (post → LinkedIn; caso de éxito → web y presentaciones a empresas; FAQ → `#anuncios` y la web) y un botón para copiar el texto | Sí (`GET /borradores?estado=APROBADO` y el detalle) | 16 aprobados |

En la **barra lateral**, debajo del usuario: **P5**, los activos guardados en OCI (subidas `SUBIDO`). Valor hoy: 36.

## 3. Alcance: qué entra

### Parte A · Java y el contrato (solo agrega)

1. **Filtro de rol** opcional en `GET /api/v1/dashboard/sentimiento` y `/temas`: `rol=todos` (por defecto, como hoy) o `rol=alumnos` (`autor_rol = miembro`). Sin el parámetro, la respuesta es idéntica a la de hoy.
2. **Puerta nueva `GET /api/v1/dashboard/comunidad`** (`desde`, `hasta`): alumnos (total, activos en 7 y en 30 días contados hasta `hasta`); bot (respondidas, derivadas y segundos promedio de reacción, `respondido_en − fecha`); derivadas por tema.
3. **Puerta nueva `GET /api/v1/dashboard/contenido`** (`desde`, `hasta`):
   - por revisar: total, por tipo y la fecha del pendiente más antiguo;
   - revisión: mediana y n de `tiempo_curaduria_seg` por tipo;
   - aprobación: aprobados y rechazados;
   - embudo: logros (`TESTIMONIO` `OK` de personas), publicables (`generacion_estado = GENERADO`), no publicables y logros con su post aprobado;
   - aprobados por semana;
   - mediana de horas del logro a la aprobación del post, con su n;
   - mensajes de personas del período;
   - activos en OCI (`subidas_oci` en `SUBIDO`).
4. **Dudas sin responder:** sumar `servidorId` y `canalId` a cada duda, para que el panel arme el enlace `https://discord.com/channels/<servidor>/<canal>/<discordId>`. Solo agrega campos.
5. **Frustración (mejora):** "2 negativos entre sus últimos 3" mira solo los mensajes **del período**, no los de cualquier fecha. Actualizar DEC-121 con DEC-157.
6. Las puertas nuevas usan el prefijo `/api/v1/dashboard/`, que ya abre solo la clave `panel` (`ApiKeyFilter` y la segunda revisión del controlador). Consultas con los índices existentes; si hace falta uno, va en una **`V9__…`** (y avisar: T13 también planea una `V9`).
7. **Contrato:** sumar todo a [PANEL_JAVA_v1.md](../../contratos/PANEL_JAVA_v1.md) §7, con un ejemplo por puerta. **Solo agrega**: ningún campo existente cambia de nombre ni de significado.

### Parte B · El panel

8. **`paginas/dashboard.py` rehecha** según el prototipo:
   - selector de vista **Comunidad / Contenido** (por ejemplo, `st.segmented_control`), que pida a Java solo lo de la vista elegida;
   - período con atajos **7, 30 (por defecto) y 90 días** y "Elegir fechas" (solo entonces aparece el selector de fechas);
   - **"Ajustes de las alertas"** (umbral de deserción y horas sin respuesta) dentro de un `st.expander`;
   - la franja de valor (P1 con su supuesto escrito, y P4), las tarjetas (`st.metric` en un `st.container(border=True)`, con la n en un `st.caption`), los gráficos y las listas de la sección 2;
   - se quita "Sin clasificar" de la vista;
   - el botón **"Abrir en Discord"** con `st.link_button`; los textos de alumnos, siempre **escapados** (nunca `unsafe_allow_html`).
9. **Gráficos con Altair** (ya viene con Streamlit: 🔎 comprobarlo en la imagen del panel, sin agregar dependencias) y `st.altair_chart`, para poder dibujar las barras divergentes y el embudo. Con un texto al pasar el mouse en cada barra.
10. **Tema claro y oscuro:**
    - en `panel/.streamlit/config.toml`, una sección `[theme.light]` y otra `[theme.dark]` (📘 [Streamlit, Theming](https://docs.streamlit.io/develop/concepts/configuration/theming));
    - 📘 `toolbarMode = "minimal"` muestra *"solo las opciones fijadas externamente o con `st.set_page_config`"* ([config.toml](https://docs.streamlit.io/develop/api-reference/configuration/config.toml)): comprobar si así se ve el selector de tema y, si no, pasar a `"viewer"`, que solo esconde las opciones de desarrollador;
    - los gráficos eligen su paleta según el tema activo: 🔎 comprobar si Streamlit 1.65 expone el tema en `st.context.theme`; si no, usar colores que se lean en los dos fondos;
    - las paletas, ya validadas para el daltonismo (las del prototipo):

| Uso | Tema claro | Tema oscuro |
|---|---|---|
| Sentimiento: muy negativo → muy positivo | `#9b2626`, `#e8726a`, `#dcdad3`, `#6da7ec`, `#184f95` | `#f4877d`, `#a5453e`, `#3b3e46`, `#3b6db3`, `#8cc0fb` |
| Una sola serie (temas, activos, aprobados por semana) | `#2a78d6` | `#3987e5` |
| Embudo: logros → publicables → aprobados | `#86b6ef`, `#3987e5`, `#1c5cab` | `#1c5cab`, `#3987e5`, `#86b6ef` |

11. `cliente_java.py`: los métodos de las puertas nuevas y el parámetro `rol`. `PANEL_MINUTOS_POR_HISTORIA` en `compose.yml` y `.env.example`, con 30 por defecto.

### Parte C · La documentación

12. DEC-153 a DEC-157 en DECISIONES.md y la actualización de DEC-121 y DEC-124. ARQUITECTURA.md §4.7 (el dashboard por rol). OPERACION.md §11 (cómo leer el dashboard, el supuesto de P1 y cómo cambiar el tema). ESTADO.md (OE5 y las mejoras hechas).

## 4. Fuera de alcance

- La página **Borradores**, M12 "publicados en LinkedIn", la sesión al recargar y el reintento de la FAQ en `ERROR` (T13). La ingesta automática y el aviso "Datos al día" (T14).
- Cambiar la IA, el bot, la ingesta, OCI o LinkedIn. Cargar o inventar datos: se usan los de la base, tal como están.
- **No ejecutar `simulate_students.py`** ni encender un segundo bot. **Nunca** leer ni mostrar el `.env`.

## 5. Pruebas exigidas

**Java** (contra `insightedu_test`). **Reutilizar las propiedades de `DashboardApiTest` o `CuraduriaApiTest`**: cada combinación nueva abre otro grupo de conexiones a PostgreSQL.

| # | Caso | Resultado esperado |
|---|---|---|
| 1 | Sentimiento y temas sin `rol`, con `rol=todos` y con `rol=alumnos` | Sin parámetro, igual que hoy; con `alumnos`, sin mentores |
| 2 | `/comunidad`: activos en 7 y 30 días; respondidas, derivadas y segundos del bot; derivadas por tema | Los conteos correctos con datos armados en la prueba |
| 3 | `/contenido`: medianas con un número par e impar de datos; aprobación; embudo; aprobados por semana en hora de Bogotá; pendiente más antiguo | Los valores correctos; sin datos, ceros y medianas nulas (no errores) |
| 4 | Frustración: 2 negativos viejos (fuera del período) y uno reciente | Sin alerta (antes había) |
| 5 | Dudas sin responder | Traen `servidorId` y `canalId` |
| 6 | Claves en las puertas nuevas: sin clave / con la de `bot` / con una ruta disfrazada | 401 / 403 / 403 |
| 7 | Período inválido o de más de 366 días | 422 |
| 8 | Las pruebas que ya existían (225 hoy) | Siguen pasando |

**Python, panel:** las dos vistas se dibujan con un cliente simulado; el selector de vista pide solo lo suyo; P1 muestra el supuesto con los minutos configurados; cada porcentaje muestra su n; sin datos, un aviso en lugar de un error; un texto con `<script>` en una duda se muestra escapado; el enlace de Discord se arma bien; la paleta cambia con el tema. Las 51 pruebas del panel siguen pasando.

**Prueba real, la corre Harrison** (no gasta Gemini):
1. `docker compose up -d --build api-java panel`.
2. Entrar al panel y abrir **Dashboard**: revisar la vista Comunidad y la vista Contenido.
3. Comparar con la columna "Valor hoy" de la sección 2 (pueden variar si entraron datos nuevos o pasaron días).
4. Cambiar el tema a oscuro desde el menú de Streamlit: todo se lee, también los gráficos.
5. Abrir una duda con "Abrir en Discord": lleva al mensaje correcto.

## 6. Criterios de terminado

- [ ] Las dos vistas muestran los KPI de la sección 2, en el orden de la decisión 3, con la n visible y el supuesto de P1 escrito.
- [ ] Las puertas nuevas solo agregan, solo abren con la clave `panel` y están en `PANEL_JAVA_v1.md` con ejemplos.
- [ ] El tema claro y oscuro funciona desde el menú de Streamlit, y los gráficos se leen en los dos.
- [ ] Las pruebas de Java y de Python pasan, y la prueba real coincide con los valores de hoy (🧪 en el informe).
- [ ] DEC-153 a DEC-157, ARQUITECTURA, OPERACION y ESTADO al día.
- [ ] El informe `docs/historico/tareas/T12-informe.md` está completo ([plantilla](PLANTILLA_INFORME.md)), y no se tocó nada fuera del alcance.

## 7. Git

La rama `tarea/T12-dashboard` ya existe, y esta ficha es su primer commit. El chat de tarea **no** ejecuta comandos de git que cambian algo: se los da a Harrison **uno por línea**, con la carpeta y lo que debería ver. Un commit por parte (A, B y C), con un solo `-m` y **sin** `Co-Authored-By` (DEC-65). Al final, `git push` y avisarle al chat principal **"T12 terminó"**. El chat principal revisa y Harrison abre el Pull Request a `main`.

## 8. Cómo abrir el chat de esta tarea

1. En VS Code, abrir un chat nuevo de Claude Code **en esta misma carpeta**, con la rama `tarea/T12-dashboard` activa.
2. Elegir **Opus 5.5** con `/model`.
3. Primer mensaje: *"Eres el chat de la tarea T12. Lee AGENTS.md y docs/historico/tareas/T12-dashboard.md completos y empieza. Respóndeme en español y dame los comandos de git uno por línea."*

⚠️ **Nunca pegues el contenido de un `.env`, un token ni tu contraseña del panel en el chat.**
