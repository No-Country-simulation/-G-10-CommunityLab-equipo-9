# T13 · Borradores por logro: una tarjeta, dos textos con sus botones, un consentimiento, y el estado en LinkedIn

> Esta ficha **sí es la orden de trabajo vigente** de T13, aunque viva en `docs/historico/tareas/`. Para todo lo demás manda [AGENTS.md](../../../AGENTS.md).

| Dato | Valor |
|---|---|
| Objetivos | **OE6** (panel de curaduría) y **OE3** (post y caso de éxito), mejorados para Marketing. Cierra el riesgo aceptado DEC-151 (M12) |
| Usuario | **Marketing** |
| Tamaño | L: una migración `V9`, el guardado del estado en LinkedIn, una puerta nueva en Java, el contrato del panel y la página Borradores rehecha |
| Modelo de Claude recomendado | **Opus 5.5**: toca la base (una migración que no se puede editar después de aplicarla), una tarea en segundo plano que escribe en la base y textos de alumnos en pantalla |
| Depende de | T07 (curaduría), T12 ✅ (el estilo del panel y sus piezas), DEC-149 (LinkedIn) |
| Rama | `tarea/T13-borradores` (ya creada desde `main`; esta ficha es su primer commit) |
| Diseño aprobado | [docs/historico/diseno/borradores.dc.html](../diseno/borradores.dc.html), con su explicación en [diseno/README.md §2 y §3](../diseno/README.md). Es el mismo archivo del prototipo privado de Harrison |
| Decisiones previas 👤 | Las de la sección 1.1, validadas por Harrison el 2026-10-15 |

## 1. Objetivo

Que la página **Borradores** deje de ser una lista desplegable de borradores sueltos ("#12 · POST_LINKEDIN") y pase a ser una **cola de logros**: cada tarjeta es un logro de un alumno, con sus dos textos (el post de LinkedIn y el caso de éxito), **dónde se publica cada uno**, un contador con las reglas de la guía de voz, **un solo consentimiento** y botones para aprobar o rechazar **cada texto por separado**. El botón del post avisa, antes de aprobar, si eso lo publicará en LinkedIn.

Además:
- **M12:** Java guarda en la base si cada post aprobado se publicó en LinkedIn, y el panel lo muestra en Borradores y en la columna **"En LinkedIn"** del dashboard;
- la página **Errores** puede reintentar una **FAQ semanal en `ERROR`**;
- el título del panel pasa a la **barra lateral**, como en el prototipo.

**Dato que define el diseño** (🧪 consulta del 2026-10-15): hoy el caso de éxito se aprueba 5 s (mediana) después del post: Marketing ya los revisa juntos, y por eso van en la misma tarjeta, aunque cada uno tenga sus botones. Y hay **2 logros con el post aprobado y el caso de éxito todavía pendiente** (mensajes 183 y 254): la tarjeta tiene que funcionar también con un solo texto pendiente.

### 1.1 Decisiones previas 👤 (2026-10-15)

| # | Decisión | Detalle |
|---|---|---|
| 1 | **Botones separados por texto** (cambia el prototipo) | Cada pestaña tiene sus propios **Aprobar**, **Guardar edición** y **Rechazar…**: el post y el caso de éxito se aprueban o se rechazan por separado, con las puertas que ya existen (el contrato de aprobar y rechazar **no cambia**). El prototipo tenía un solo "Aprobar post y caso de éxito": Harrison prefirió separarlos, porque **aprobar el post puede publicarlo en LinkedIn** y el caso de éxito no. La tarjeta sigue siendo una por logro, y sale de "Por revisar" cuando no le queda ningún texto pendiente |
| 2 | Tiempo de revisión | Cada texto guarda **su propio tiempo**: desde que se abrió la tarjeta, o desde la última aprobación o rechazo en esa misma tarjeta. Así la tarjeta M5 del dashboard sigue midiendo lo mismo que hoy |
| 2b | **El botón del post dice qué va a pasar en LinkedIn** | Java informa el modo de LinkedIn (`APAGADO`, `SIMULADO` o `REAL`) y el panel lo muestra **antes** de aprobar. Apagado: "Aprobar post", con la nota "La publicación en LinkedIn está apagada: aprobar no publica nada". Real: **"Aprobar y publicar en LinkedIn"**, con un paso de confirmación ("Se publicará en público en el LinkedIn de CommunityLab"). Hoy está apagado (DEC-149); se enciende para la demo |
| 2c | Un solo consentimiento por logro | Una casilla en la tarjeta, porque el consentimiento es del alumno y vale para sus dos textos. **Cada** botón Aprobar exige que esté marcada |
| 3 | Etiqueta del tipo de logro ("Contratación") | **No entra en T13**: la base no guarda ese dato. La tarjeta muestra el motivo de la IA, que ya lo dice ("Contratación: consiguió…"). Queda como mejora 🟡 en ESTADO.md |
| 4 | M12 · Estado en LinkedIn | Java **guarda** el resultado de cada publicación (publicado, simulado, apagado o falló, con un motivo corto) en una migración **`V9`**. El panel lo muestra y **no deja aprobar un post de más de 3.000 caracteres**. **Sin reintento**: evita publicar dos veces en público. Reemplaza a DEC-151 |
| 5 | Reintentar la FAQ en `ERROR` | Botón en la página **Errores**. Java la devuelve a la cola y la **arma enseguida, en segundo plano** (tarda hasta 150 s y gasta Gemini), sin hacer esperar al panel |
| 6 | Mantener la sesión al recargar la página | **Fuera de T13.** Sigue como mejora en ESTADO.md §3 |
| 7 | Fuera | El recuadro "Datos al día" de la barra lateral (es T14). Volver a generar un borrador. Roles por usuario |

La tarea suma estas filas a [DECISIONES.md](../../DECISIONES.md):
- **DEC-159:** Borradores por logro, con botones por texto, un consentimiento y el aviso de LinkedIn (decisiones 1, 2, 2b, 2c y 3);
- **DEC-160:** el estado en LinkedIn con la `V9` (decisión 4). **DEC-151 pasa a 🔁**, reemplazada por DEC-160;
- **DEC-161:** reintentar la FAQ en `ERROR`, enseguida y en segundo plano (decisión 5).

Si durante la tarea decides algo más (por ejemplo, cómo armar las tarjetas en Streamlit), va en el informe §5 y, si Harrison lo valida, como DEC-162 en adelante.

## 2. Contexto: qué leer

| Qué | Dónde |
|---|---|
| El diseño, zona por zona | [diseno/README.md §2](../diseno/README.md) y [borradores.dc.html](../diseno/borradores.dc.html). Los textos del prototipo (títulos, frases, avisos y botones) son los que van en pantalla. **No copies sus colores**: son del tema claro y están escritos a mano |
| Las piezas que hay que reutilizar | [diseno/README.md §3](../diseno/README.md): `ESTILOS`, `BORDE`, `FONDO_TARJETA`, `SUAVE`, `_bloque`, `_seccion`, `_titulo`, `_nota`, `_hace`, `_corto`, `DESTINOS`, los íconos… en `panel/paginas/dashboard.py` |
| Cómo se hizo el dashboard, con sus trampas | [T12-informe.md](T12-informe.md) §4.4 (capturas), §5 (por qué no se eligen colores según el tema: DEC-156) y §6.3 (el título del panel) |
| La página de hoy | `panel/paginas/borradores.py` (la medición del tiempo, el consentimiento y el aviso de 409 se conservan) |
| El contrato del panel | [PANEL_JAVA_v1.md](../../contratos/PANEL_JAVA_v1.md) §2 (borradores y errores) |
| La publicación en LinkedIn | `backend-java/.../linkedin/LinkedinService.java` y `curaduria/CuraduriaService.java` (`aprobar`, que la lanza con `CompletableFuture.runAsync`); [ARQUITECTURA.md §4.9](../../ARQUITECTURA.md); [LINKEDIN_AUTOMATIZACION.md](../../LINKEDIN_AUTOMATIZACION.md) |
| La FAQ semanal | `backend-java/.../faqsemanal/` (`FaqSemanalService.reintentar()` y los estados de `faq_semanas` en `V5__faq_semanal.sql`) |
| La guía de voz (los largos del contador) | `agents/agent_mod/guia_de_voz.md`: post de 90 a 160 palabras, caso de 150 a 250, sin emojis ni hashtags |

## 3. Alcance: qué entra

### Parte A · Java y el contrato (solo agrega)

1. **Migración `V9__estado_linkedin.sql`** (nueva; ninguna migración existente se toca). En `borradores`:
   - `linkedin_estado` (`PUBLICADO`, `SIMULADO`, `APAGADO` o `ERROR`; vacío = sin dato);
   - `linkedin_post_id` (el `urn:li:share:…` que devuelve LinkedIn), `linkedin_en` (cuándo) y `linkedin_motivo` (un texto corto);
   - un `CHECK`: solo un `POST_LINKEDIN` puede tener estado en LinkedIn.

   Los posts aprobados antes de la `V9` quedan **sin dato** (no se rellenan).
2. **Guardar el resultado de la publicación.** Después de llamar a LinkedIn (en segundo plano, como hoy), Java guarda el estado con un `UPDATE … WHERE id = :id AND estado = 'APROBADO' AND linkedin_estado IS NULL`, **sin transacción abierta durante la llamada** (AGENTS.md §6). Toda excepción termina en `ERROR`; nunca queda un hilo que falle sin guardar nada.

   | Caso | Estado | Motivo |
   |---|---|---|
   | LinkedIn apagado (`LINKEDIN_HABILITADA=false`) | `APAGADO` | — |
   | Encendido sin token (modo simulado) | `SIMULADO` | — |
   | Publicado | `PUBLICADO`, con `linkedin_post_id` | — |
   | Más de 3.000 caracteres o texto vacío | `ERROR` | "Pasa de 3.000 caracteres" o "Texto vacío" |
   | LinkedIn respondió con error o no respondió | `ERROR` | **Un texto fijo armado por Java**, por ejemplo "LinkedIn respondió HTTP 401" o "LinkedIn no respondió a tiempo". **Nunca** `e.getMessage()` ni el cuerpo de la respuesta de LinkedIn: pueden traer datos que no deben quedar en la base |

   **Sin reintento** (decisión 4). El token nunca se guarda ni aparece en un registro.
3. **Listar borradores** (`GET /api/v1/borradores`) suma a cada borrador:
   - `mensajeId` (el logro del que salió; `null` en la FAQ), para que el panel agrupe el post y el caso del mismo logro;
   - `motivoIa` (el mismo campo del detalle), para el resumen de la tarjeta;
   - `linkedin` (abajo), para la columna "En LinkedIn" del dashboard.

   Y la respuesta suma, junto a la lista, **`linkedinModo`**: `APAGADO` (`LINKEDIN_HABILITADA=false`), `SIMULADO` (encendido sin token o sin autor) o `REAL` (encendido con token y autor), con la misma regla que usa `LinkedinService` (decisión 2b). Solo dice el modo: **nunca** el token, el autor ni si el token venció.
4. **Ver un borrador** (`GET /api/v1/borradores/{id}`, y las puertas que devuelven el mismo borrador) suma `linkedin`: `{ "estado": "PUBLICADO", "postId": "urn:li:share:…", "en": "…", "motivo": null }` en un `POST_LINKEDIN`, y `null` en los otros tipos. Un post sin dato trae los cuatro campos en `null`.
5. **Errores** (`GET /api/v1/errores`) suma la lista `faq`: las semanas en `ERROR`, con `semana`, `desde`, `hasta`, `intentos` y `motivo`.
6. **Puerta nueva `POST /api/v1/errores/faq/{semana}/reintentar`** (con `X-Usuario` y cuerpo `{}`, como las otras dos de reintentar):
   - `semana` con el formato `2026-W41` (si no: `422`); si no existe: `404`; si no está en `ERROR`: `409`;
   - devuelve la semana a la cola (`estado`, `reservada_hasta` y `terminada_en` vacíos, `intentos = 0`) con una guarda `WHERE … AND estado = 'ERROR'`, y responde `{ "semana": "2026-W41", "etapa": "faq", "estado": "PENDIENTE" }`;
   - **después de responder**, lanza en segundo plano el reintento de la FAQ (`FaqSemanalService.reintentar()` o una variante para esa semana). La reserva de `faq_semanas` impide que la arme dos veces si el reintento programado pasa al mismo tiempo;
   - 🔎 la ruta ya está bajo `/api/v1/errores`, que solo abre la clave `panel` (`ApiKeyFilter`). Compruébalo con una prueba, y que el controlador vuelva a revisar el cliente, como las otras.
7. **Contrato:** todo lo anterior en [PANEL_JAVA_v1.md](../../contratos/PANEL_JAVA_v1.md), con una nota "Agregado en T13" arriba, ejemplos y la puerta 9 en la tabla de §2. **Solo agrega:** ningún campo existente cambia de nombre ni de significado. Actualizar §6 ("Fuera de este contrato"), que hoy dice que reintentar la FAQ está fuera.

### Parte B · El panel

8. **Un módulo común, `panel/estilo.py`**, con las piezas de T12 de la tabla de [diseno/README.md §3](../diseno/README.md). Las importan `dashboard.py` y `borradores.py`. **El dashboard se tiene que ver igual que antes**: compruébalo con capturas antes y después, y con sus pruebas.
9. **`app.py`:**
   - sale el título "Panel de Curaduría B2B - CommunityLab" de arriba de cada página;
   - la barra lateral empieza con **"CommunityLab"** y, debajo, "Panel de curaduría" (texto fijo, como en el prototipo), y sigue con la navegación, donde Borradores lleva el **número de tarjetas por revisar**, y la sesión;
   - 🔎 Streamlit dibuja la navegación de `st.navigation` arriba de todo lo demás de la barra lateral. Para que el título quede encima, prueba `st.navigation(position="hidden")` con `st.page_link` propios, o lo que funcione en Streamlit 1.65, y explícalo en el informe;
   - la pantalla de inicio de sesión conserva un título ("CommunityLab · Panel de curaduría").
10. **`paginas/borradores.py` rehecha** según el prototipo, zona por zona ([diseno/README.md §2](../diseno/README.md)):
    - **Encabezado:** "Borradores" y la frase del prototipo;
    - **Filtro de estado:** píldoras **Por revisar (n)** · Aprobados · Rechazados (por ejemplo, `st.segmented_control`), donde **n son tarjetas, no borradores**;
    - **Cola (izquierda):** una tarjeta por logro, agrupando por `mensajeId`, del más antiguo al más nuevo. Cada tarjeta lleva el primer nombre del alumno (la primera palabra de `autorNombre`), el motivo de la IA recortado (`_corto`), hace cuánto (`_hace`) y una etiqueta: "Post + caso de éxito", "Solo caso de éxito" o "Solo post". La FAQ es otra tarjeta: "FAQ de la semana 2026-W41", con su motivo y la etiqueta "FAQ · sin consentimiento". La elegida se marca con un borde más grueso;
    - **Detalle (derecha):** "Logro de Ana", el canal, la fecha y hace cuánto; dos recuadros, **Mensaje original** y **Por qué la IA lo propuso**;
    - **Pestañas** Post de LinkedIn · Caso de éxito, cada una con **"Dónde se publica"** (`DESTINOS`), el texto editable, el **contador** y **Copiar texto** (puede ser el ícono de copiar de `st.code`, como en T12). Si un texto ya no está pendiente (el post de los mensajes 183 y 254), su pestaña lo muestra **solo para leer**, con quién lo aprobó y cuándo;
    - **Contador:** "N palabras (la guía pide 90 a 160) · N de 3.000 caracteres de LinkedIn" en el post, y "N palabras (la guía pide 150 a 250) · sin emojis ni hashtags" en el caso. **Los caracteres se cuentan como Java** (`String.length()`, en UTF-16: un emoji como 🎉 cuenta 2), no con `len()` de Python. Un post de más de 3.000 caracteres pinta el contador como alerta y **apaga "Aprobar"**, con el aviso "LinkedIn acepta hasta 3.000 caracteres: acorta el post para aprobarlo";
    - **Consentimiento:** una sola casilla por tarjeta, arriba de los botones, "Ana dio su consentimiento para publicar su nombre y su historia. **Vale para los dos textos.**" (decisión 2c; ver la regla de seguridad del punto 12). Si el post ya se aprobó con consentimiento, la casilla aparece marcada para el caso de éxito, y se puede desmarcar;
    - **Acciones, dentro de cada pestaña** (decisión 1): **Aprobar** (apagado hasta marcar la casilla, con el aviso "Para aprobar, marca la casilla de consentimiento"), **Guardar edición** (solo el texto de esa pestaña) y **Rechazar…** (con un motivo opcional, solo para ese texto). Un `409` se muestra como hoy ("…Actualiza la lista");
    - **El botón del post y LinkedIn** (decisión 2b, con `linkedinModo`):

      | Modo | Botón | Nota debajo | Al hacer clic |
      |---|---|---|---|
      | `APAGADO` | "Aprobar post" | "La publicación en LinkedIn está apagada: aprobar no publica nada." | Aprueba |
      | `SIMULADO` | "Aprobar post" | "LinkedIn está en modo simulado: aprobar no publica nada." | Aprueba |
      | `REAL` | **"Aprobar y publicar en LinkedIn"** | "Al aprobar, el post se publica en público en el LinkedIn de CommunityLab." | Pide confirmar (por ejemplo, `st.dialog` con "Publicar ahora" y "Cancelar"); solo al confirmar, aprueba |
      | No se sabe (Java no lo dijo) | "Aprobar post" | "No se pudo saber si LinkedIn está encendido: al aprobar, podría publicarse." | Pide confirmar, como en `REAL` |

      El caso de éxito dice siempre "Aprobar caso de éxito" y no se publica solo: va a OCI (`aprobados/`) para la web y las presentaciones;
    - **Después de aprobar:** un aviso verde por texto ("Post aprobado", "Caso de éxito aprobado"). Si al logro todavía le queda un texto pendiente, el aviso lo dice ("Falta revisar el caso de éxito") y la tarjeta sigue en la cola, con esa pestaña abierta. Cuando ya no queda ninguno: "Aprobados los dos textos de Ana", con un enlace a "Listos para publicar" del dashboard (`st.page_link`; si se puede abrir con la pestaña Contenido elegida, mejor);
    - **Estado en LinkedIn** (en el post aprobado): "Publicado en LinkedIn el …" con el botón **"Ver en LinkedIn"**, "No publicado: la publicación en LinkedIn está apagada", "Simulado: LinkedIn está encendido sin token", "Falló: <motivo>" o "Sin dato (se aprobó antes de que se guardara este estado)". El enlace se arma **solo** si `postId` tiene la forma `urn:li:share:<números>` (o `urn:li:ugcPost:<números>`); 🔎 comprobar el formato de la URL de LinkedIn para un post;
    - **La FAQ:** una sola pestaña ("FAQ semanal"), con su destino, la semana y "Aprobar FAQ", sin casilla (como hoy);
    - se conservan: la medición del tiempo desde que se abre la tarjeta en la sesión, las tres capas del consentimiento y lo guardado en OCI (T09), en un lugar discreto del detalle.
11. **Trampa de las pestañas** 🧪 (T12 usó `st.tabs(on_change="rerun")`, que solo ejecuta la pestaña abierta): Streamlit **borra el estado de un widget que no se dibujó** en una pasada. Si solo se dibuja la pestaña abierta, la edición del post se pierde al pasar al caso de éxito. Dibuja las dos pestañas, o guarda los textos en `st.session_state` con claves propias. Tiene que haber una prueba de esto.
12. **Seguridad de lo que se muestra** (DEC-158 y AGENTS.md): los nombres, el mensaje original, los borradores y el motivo **nunca** van en `st.html` ni en `st.markdown`. Además:
    - 📘 las **etiquetas de los widgets** (`st.button`, `st.checkbox`, `st.tabs`, las píldoras…) **interpretan markdown**, con enlaces e imágenes incluidos ([st.button, parámetro `label`](https://docs.streamlit.io/develop/api-reference/widgets/st.button)). Una etiqueta lleva solo texto fijo, o el nombre **con el markdown escapado** por una función con pruebas (`**x**`, `[x](http://…)`, `![x](http://…)` y `<b>` se tienen que ver tal cual). Lo mismo para `st.success` y `st.subheader`, que también son markdown;
    - para dar tamaño o peso a un texto de alumno sin HTML: un `st.container(key=…)` con `st.text` adentro, y una regla CSS **fija** para esa clave en los estilos;
    - las tarjetas de la cola: si son botones, la etiqueta sigue esta misma regla.
13. **Dashboard, vista Contenido:** la columna **"En LinkedIn"** en "Listos para publicar" (Publicado · No: apagado · Simulado · Falló · Sin dato; "—" si no es un post).
14. **Errores:** una tercera lista, **"FAQ semanal"**, con la semana, los intentos, el motivo (con `st.text`) y el botón **Reintentar**, que avisa que se está armando y que tarda hasta unos minutos.
15. **`cliente_java.py`:** `reintentar_faq(semana, usuario)` y lo que haga falta para los campos nuevos.
16. **Colores:** los de T12, que no dependen del tema (DEC-156). El botón "Aprobar" usa `type="primary"`. Si el botón índigo de `ui.ESTILOS` (DEC-109) choca con el prototipo, propón el cambio en el informe en lugar de hacerlo por tu cuenta: también se ve en el inicio de sesión.

### Parte C · La documentación

17. DECISIONES.md: DEC-159 a DEC-161, y DEC-151 en 🔁.
18. ARQUITECTURA.md: §4.6 (curaduría por logro), §4.9 (el estado guardado; sacar la fila "Límites" que ya no aplica), §5 (las columnas nuevas de `borradores`, la fila de la `V9` y "el siguiente es `V10__…`") y §12 (el límite de LinkedIn).
19. **AGENTS.md §4:** "el siguiente es `V9__…`" pasa a `V10__…`.
20. OPERACION.md: §13 (dónde se ve si un post se publicó) y la sección de errores (reintentar la FAQ). ESTADO.md: las mejoras hechas (reintentar la FAQ), las que siguen (sesión al recargar) y la nueva 🟡 (el tipo de logro). [diseno/README.md](../diseno/README.md): §1, Borradores ✅; §2, las filas "Consentimiento", "Acciones" y "Después de aprobar" con lo que cambió (botones por texto y el aviso de LinkedIn, DEC-159). El archivo `borradores.dc.html` **no** se toca: es el prototipo tal como se aprobó.

## 4. Fuera de alcance

- Mantener la sesión al recargar (decisión 6), el recuadro "Datos al día" y la ingesta automática (T14), volver a generar un borrador, avisar si dos personas editan a la vez y roles por usuario.
- Cambiar la IA, el Agente-Mod, el bot, la ingesta u OCI. Cambiar las puertas de aprobar, rechazar o editar.
- **No encender LinkedIn** ni correr `scripts/publicar_linkedin.py`: con token, publica de verdad y en público. Las pruebas de Java lo apagan desde el `pom.xml`; no quitar esa línea.
- **No aprobar, rechazar ni editar borradores de la base real** para probar o sacar capturas: son acciones reales (lo aprobado sube a OCI). Solo Harrison lo hace, en la prueba real.
- **No levantar un `api-java` nuevo contra la base real** antes de la prueba real: aplicaría la `V9`, y una migración aplicada ya no se edita.
- **No ejecutar `simulate_students.py`** ni encender un segundo bot. **Nunca** leer ni mostrar el `.env`.

## 5. Pruebas exigidas

**Java** (contra `insightedu_test`, con el comando de [OPERACION.md §5](../../OPERACION.md) y `-e LINKEDIN_ACCESS_TOKEN=` por seguridad). **Reutiliza las propiedades de `CuraduriaApiTest`**: cada combinación nueva abre otro grupo de conexiones a PostgreSQL. Si cambias la `V9` después de correr las pruebas, la base de prueba ya la tiene: recréala antes de volver a correrlas.

| # | Caso | Resultado esperado |
|---|---|---|
| 1 | La `V9` se aplica sobre la base de prueba | Columnas y `CHECK` presentes; un `CASO_EXITO` con estado en LinkedIn es rechazado por la base |
| 2 | Aprobar un post con LinkedIn apagado | Queda `APAGADO`, y aprobar sigue respondiendo enseguida. La espera se hace con un sondeo corto con tope, no con una pausa fija larga |
| 3 | `LinkedinService` en modo simulado, con un post de más de 3.000 caracteres, con texto vacío y con un cliente que lanza un error (simulado, sin red) | `SIMULADO` / `ERROR` "Pasa de 3.000 caracteres" / `ERROR` "Texto vacío" / `ERROR` con un motivo fijo que **no** contiene el mensaje de la excepción |
| 4 | Guardar el estado dos veces, o en un borrador que ya no está `APROBADO` | No cambia nada (la guarda) |
| 5 | Listar y ver un borrador | Traen `mensajeId`, `motivoIa` y `linkedin` (en la FAQ, `mensajeId` y `linkedin` en `null`) |
| 5b | `linkedinModo` en la lista, con LinkedIn apagado, encendido sin token y encendido con token y autor (propiedades de prueba, **sin publicar**: el modo se lee de la configuración, no llama a LinkedIn) | `APAGADO` / `SIMULADO` / `REAL`. La respuesta no contiene el token ni el autor |
| 6 | Errores con una semana en `ERROR` | La lista `faq` la trae |
| 7 | Reintentar la FAQ: en `ERROR` / con otro estado / que no existe / con un formato inválido | `200` y la semana sin estado y con 0 intentos / `409` / `404` / `422`. El reintento en segundo plano usa la IA simulada de `FaqSemanalTest` (nunca la real) y la prueba no queda dependiendo de cuánto tarda |
| 8 | Claves en la puerta nueva: sin clave / con la de `bot` / con una ruta disfrazada (`;x=1`, `%65`) | 401 / 403 / 403 |
| 9 | Las pruebas que ya existían (243 hoy) | Siguen pasando |

**Python, panel** (en la imagen del panel, con el comando de [TRASPASO_ORQUESTADOR.md §6](../TRASPASO_ORQUESTADOR.md)):

| # | Caso | Resultado esperado |
|---|---|---|
| 1 | Agrupar: post y caso del mismo logro / solo el caso pendiente / la FAQ | Una tarjeta cada uno, del más antiguo al más nuevo, con su etiqueta; el contador de "Por revisar" cuenta tarjetas |
| 2 | Aprobar el post y, después, el caso de la misma tarjeta | Un pedido cada uno, con el consentimiento; el tiempo del caso cuenta desde la aprobación del post (decisión 2). Tras el primero, la tarjeta sigue en la cola y avisa lo que falta; tras el segundo, sale de "Por revisar" |
| 3 | El botón del post con cada `linkedinModo` y sin el dato | El texto y la nota de la tabla del punto 10. En `REAL` y sin el dato, **sin confirmar no se envía el pedido**; al confirmar, sí |
| 4 | Rechazar y Guardar edición en una pestaña | Un solo pedido, solo para ese texto; el otro texto no cambia |
| 5 | Editar el post, pasar a la pestaña del caso y volver | La edición sigue ahí |
| 6 | Contador | Palabras y caracteres como Java (un emoji cuenta 2); con más de 3.000, "Aprobar" apagado |
| 7 | Un nombre con `**x**`, `[x](http://…)`, `![x](http://…)` y `<script>` | Se ve tal cual en la tarjeta, el título, la casilla y el aviso de aprobado |
| 8 | Estado en LinkedIn: cada estado y sin dato; un `postId` con una forma rara | El texto de cada uno; sin enlace si el `postId` no tiene la forma esperada |
| 9 | Errores: reintentar una FAQ | Llama a la puerta nueva con la semana y el usuario |
| 10 | Dashboard | La columna "En LinkedIn" con cada estado; las pruebas del dashboard siguen pasando sin cambiar lo que comprueban |
| 11 | Las pruebas que ya existían (63 hoy) | Siguen pasando |

**Capturas** ([diseno/README.md §4](../diseno/README.md)): a 1440 px, en claro y en oscuro, cambiando el tema **sin recargar**, comparadas con `borradores.dc.html`. Como en T12 (informe §4.4): una copia aparte del panel dentro de la red de Docker, sin puertos publicados y con un usuario de captura que solo existe en esa copia. **Solo mirar**: ni aprobar, ni rechazar, ni editar (sección 4). Mientras Harrison no reconstruya `api-java`, el Java real no trae los campos nuevos: saca las capturas con un Java simulado, o después del paso 2 de la prueba real. Las capturas del dashboard, antes y después del punto 8, prueban que se ve igual.

**Prueba real, la corre Harrison** (no gasta Gemini; LinkedIn sigue apagado):
1. Comprobar que LinkedIn está apagado: `docker compose exec api-java printenv LINKEDIN_HABILITADA` debe decir `false` (no es un secreto).
2. `docker compose up -d --build api-java panel`: Java aplica la `V9` al arrancar.
3. Abrir **Borradores**: hoy son **5 tarjetas** por revisar: 4 logros (mensajes 183 y 254, solo el caso de éxito; 256 y 257, post y caso) y 1 FAQ. Revisar el diseño en claro y en oscuro.
4. En un logro: editar el post, pasar al caso de éxito y volver (la edición sigue), mirar el contador y copiar un texto. No guardar si no se quiere.
5. Elegir **un logro que de verdad aprobarías**. Antes de aprobar, comprobar que el botón del post dice "Aprobar post" con la nota "La publicación en LinkedIn está apagada…". Aprobar el post y después el caso de éxito, con sus botones. ⚠️ Es una aprobación real: sube a OCI (`aprobados/`), como siempre. Con LinkedIn apagado, no publica nada. Comprobar que el post aprobado dice "No publicado: la publicación en LinkedIn está apagada" y que la columna "En LinkedIn" del dashboard dice lo mismo.
6. Abrir **Errores**: la lista "FAQ semanal" sale vacía (hoy no hay ninguna en `ERROR`; el botón se prueba con las pruebas de Java).

## 6. Criterios de terminado

- [ ] La página Borradores sigue el prototipo zona por zona, con las piezas de T12 en `panel/estilo.py`, y el dashboard se ve igual que antes.
- [ ] Cada texto tiene sus botones (decisión 1) y su tiempo (decisión 2), con un solo consentimiento por tarjeta, y la edición no se pierde al cambiar de pestaña.
- [ ] El botón del post dice antes de aprobar qué pasará en LinkedIn y, si va a publicar, pide confirmar (decisión 2b).
- [ ] Ningún texto ni nombre de alumno o de la IA va en HTML, en markdown o en una etiqueta sin escapar (con pruebas).
- [ ] La `V9` guarda el estado en LinkedIn, el panel lo muestra en Borradores y en el dashboard, y un post de más de 3.000 caracteres no se puede aprobar.
- [ ] La FAQ en `ERROR` se reintenta desde Errores.
- [ ] El contrato solo agrega, y está en `PANEL_JAVA_v1.md` con ejemplos.
- [ ] Las pruebas de Java y del panel pasan (🧪 en el informe, con los números), y las capturas en claro y en oscuro están descritas.
- [ ] DEC-159 a DEC-161, DEC-151 en 🔁, ARQUITECTURA, AGENTS (`V10`), OPERACION, ESTADO y diseno/README al día.
- [ ] El informe `docs/historico/tareas/T13-informe.md` está completo ([plantilla](PLANTILLA_INFORME.md)), y no se tocó nada fuera del alcance.

## 7. Git

La rama `tarea/T13-borradores` ya existe, y esta ficha es su primer commit. El chat de tarea **no** ejecuta comandos de git que cambian algo: se los da a Harrison **uno por línea**, con la carpeta y lo que debería ver. Un commit por parte (A, B y C), con un solo `-m` y **sin** `Co-Authored-By` (DEC-65). **Después de cada commit, comprueba con `git log --oneline -3` que se hizo** (en T12, el commit de la Parte A no corrió y se mezcló con el de la B). Al final, `git push` y avisarle al orquestador **"T13 terminó"**. El orquestador revisa y Harrison abre el Pull Request a `main`.

## 8. Cómo abrir el chat de esta tarea

1. En VS Code, abrir un chat nuevo de Claude Code **en esta misma carpeta**, con la rama `tarea/T13-borradores` activa.
2. Elegir **Opus 5.5** con `/model`.
3. Primer mensaje: *"Eres el chat de la tarea T13. Lee AGENTS.md, docs/historico/tareas/T13-borradores.md y docs/historico/diseno/README.md completos, y el diseño docs/historico/diseno/borradores.dc.html, y empieza. Respóndeme en español y dame los comandos de git uno por línea."*

⚠️ **Nunca pegues el contenido de un `.env`, un token ni tu contraseña del panel en el chat.**
