# Manual del chat principal (guía, orquestador y auditor)

> Para el chat de Claude que toma el rol de **chat principal** de InsightEdu Lab. Escrito el 2026-10-04 por el chat principal anterior, al llenarse su contexto.
> Se lee **después** de [CLAUDE.md](../CLAUDE.md). Tu memoria automática ya trae el perfil de Harrison y sus reglas de trabajo.

## 0. Primeros pasos, en orden

1. Lee `CLAUDE.md`, este archivo, [docs/DECISIONES.md](DECISIONES.md) (todas las decisiones en un solo lugar), [docs/tareas/README.md](tareas/README.md) (estado de las tareas y observaciones) y, del [análisis](ANALISIS_INGENIERIA_PROPUESTA_3.md), las secciones **Objetivos**, **0 · Decisiones** y **9 · Prioridades**.
2. Comprueba el estado real con comandos de solo lectura: `git fetch`, `git status -sb`, `git log --oneline -5 feature/integracion-arquitectura-3` y `docker compose ps`.
3. **Primera tarea: auditar T04** (procedimiento en la sección 3). Ojo: T04 **modificó `docs/contratos/JAVA_IA_v1.md` y su JSON Schema**. Verifica qué cambió y si cambia el contrato Java ↔ IA v1 sin aprobación de Harrison.
4. **Después de T04, el ciclo se repite hasta la entrega**, una tarea a la vez y en el orden de la sección 6 (**T05 → T06 → T06b → T07 → T08 → T09 → T10**):

   ```
   escribir la ficha → plantear a Harrison sus decisiones previas → Harrison abre el chat de tarea
        ↑                                                                  ↓
   fusionar y actualizar la documentación  ←  auditar  ←  "Txx terminó"
   ```

   Si el plazo aprieta, recorta los 🟡 y avisa a Harrison. Lo último que se recorta es OE1, OE3 y OE6 (análisis § Objetivos).

## 1. El rol

| Función | Qué hace | Qué **no** hace |
|---|---|---|
| **Guía** | Explica en simple, propone **una** opción con su motivo y espera la validación de Harrison | Decidir por él cosas de alcance, contrato o arquitectura |
| **Orquestador** | Escribe las fichas (`docs/tareas/Txx-*.md`), decide el orden y mantiene el índice y las observaciones | Programar las tareas de las fichas: eso lo hace un chat de tarea |
| **Auditor** | Verifica cada tarea antes de que Harrison la fusione | Fusionar o hacer commits: los comandos que cambian git los ejecuta Harrison |

El chat principal sí puede editar la documentación de seguimiento: índice, registro de avance, `CLAUDE.md` y fichas. **Cuida tu contexto:** respuestas breves, sin pegar archivos enteros, y lee solo las partes que necesitas.

## 2. Estado al 2026-10-04

| Qué | Estado |
|---|---|
| Rama de integración | `feature/integracion-arquitectura-3`. Harrison desarrolla todo aquí; base congelada (D1) |
| Tareas | T01 ✅ · T02 ✅ · T03 ✅ · T04 ✅ (fusión `--no-ff`) · T05 ✅ (auditada el 2026-10-04 con un cambio pedido y corregido) · T06 ✅ (auditada el 2026-10-04, sin cambios pedidos) · **T06b y T07 a T10 sin ficha** |
| Docker local | `postgres` (sin puerto), `api-java` (`127.0.0.1:8008`), `ia` (`127.0.0.1:8000`) y `bot` (sin puerto). Faltan el panel y la ingesta programada (cron, O3) |
| Datos | 39 mensajes reales del servidor de pruebas en `mensajes`, **todos clasificados** por T04 (🧪 39 en `OK`, migración V2 aplicada) |
| Decisiones | D1 a D8 en el análisis §0 y DEC-01 a DEC-92 en [DECISIONES.md](DECISIONES.md). **D3:** el bot responde sin aprobación, solo con respaldo en los PDFs |
| Plan de 2 días | ✅ Cumplido (T01 a T03) |
| Entrega final | **2026-10-26** |

## 3. Cómo auditar una tarea

Cuando Harrison dice **"Txx terminó"**:

1. **Rama y commits:**
   ```
   git fetch -q origin
   git log --oneline feature/integracion-arquitectura-3..tarea/Txx-…
   git merge-base --is-ancestor feature/integracion-arquitectura-3 tarea/Txx-… && echo "fusión directa posible"
   git ls-remote --heads origin tarea/Txx-…
   ```
2. **Alcance:** `git diff --stat feature/integracion-arquitectura-3...tarea/Txx-…`, comparado con las secciones 3 y 4 de la ficha.
3. **Informe:** `git show tarea/Txx-…:docs/tareas/Txx-informe.md`. Comprueba que cada criterio tenga evidencia 🧪 y que las decisiones estén validadas por Harrison.
4. **Código clave** (con `git show rama:archivo | grep …`, sin leer todo): seguridad, transacciones, manejo de errores, que no queden secretos, y que las pruebas tengan aserciones reales.
5. **Verificación propia**, sin efectos:
   - `python -m pytest agents/orquestador/tests -q` (desde la raíz) y `python -m pytest -q` (desde `ingestion/discord`), con `%USERPROFILE%/.venvs/insightedu-discord/Scripts/python.exe`;
   - `curl` a `/actuator/health` y a `/health`;
   - consultas `SELECT` con `docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "…"'`.

   Las pruebas de Java las corre el chat de tarea; si dudas, pídele a Harrison el comando de [OPERACION.md §5](OPERACION.md).
6. **Veredicto** en una tabla: ✅ aprobada o ❌ con cambios pedidos. Las observaciones que no frenan la tarea van a la tabla de [docs/tareas/README.md](tareas/README.md), indicando a qué tarea pasan.
7. **Actualiza la documentación:**
   - estado en `docs/tareas/README.md`;
   - **[docs/DECISIONES.md](DECISIONES.md): una fila por cada decisión nueva** (del informe §5 o de Harrison), y cierra las ❓ que se resolvieron;
   - el análisis: fila del **registro de avance** y columna **"Estado"** de los OE;
   - `CLAUDE.md`, si cambió el mapa o se agregó una pieza.
8. **Dale a Harrison los comandos**, uno por línea, con la carpeta y qué debería ver:
   - `git switch feature/integracion-arquitectura-3`
   - `git merge --ff-only tarea/Txx-…` y `git push`
   - `git add …`, el commit de la documentación (un solo `-m`, **sin** `Co-Authored-By`: DEC-65), **`git status` para confirmar** y `git push`
   - `git switch -c tarea/T(xx+1)-…`

⚠️ **Si la rama de integración avanzó después de que se creó la tarea**, `--ff-only` falla. Es el caso de **T04**, porque después se guardó este manual. Entonces hay que usar `git merge --no-ff tarea/Txx-… -m "Merge Txx"`, siempre que la tarea no haya tocado los mismos archivos; compruébalo antes con `git diff --name-only`.

## 4. Cómo escribir una ficha

Copia la estructura de [T03](tareas/T03-puerta-lotes.md) o [T04](tareas/T04-clasificacion-java-ia.md):

| Sección | Qué lleva |
|---|---|
| Tabla inicial | Fase, objetivos (OE), hallazgos que resuelve, tamaño, modelo recomendado, de qué depende, rama y decisiones previas 👤 |
| 1 · Objetivo | Qué debe quedar funcionando, en 3 a 5 líneas |
| 2 · Contexto | Qué leer y dónde: análisis, contratos, informes anteriores y observaciones |
| 3 · Alcance | Lista numerada y concreta |
| 4 · Fuera de alcance | Lo que no debe tocar. Incluye siempre "no ejecutar `simulate_students.py`" |
| 5 · Pruebas | Tabla de casos con su resultado esperado, más una **prueba real que corre Harrison** (avisando el costo si usa Gemini) |
| 6 · Criterios de terminado | Casillas verificables |
| 7 · Git | Comandos de inicio y de fin |
| 8 · Abrir el chat | Modelo y primer mensaje |

- **Modelo del chat de tarea:** **Opus 5.5** si define una base o tiene concurrencia o seguridad delicada; **Sonnet 5.5** si es acotada.
- **Decisiones previas:** antes de mandar la ficha, plantéaselas a Harrison con una opción recomendada y su motivo, y anota la respuesta en la ficha.

## 5. Lecciones y trampas conocidas

| Tema | Lección |
|---|---|
| Commits | **Verifica siempre** con `git log` o `git status` que el commit de Harrison se hizo. Una vez el `add` se ejecutó y el `commit` no, y los cambios viajaron a la rama de la tarea |
| Editar docs en otra rama | Si editas la documentación mientras está activa una rama de tarea, primero comprueba con `git diff --name-only integracion tarea -- <archivos>` que la tarea no tocó esos archivos; así viajan sin conflicto al cambiar de rama |
| Fin de línea (Windows) | La copia de trabajo usa CRLF. Edita con la herramienta Edit, o con Python usando `open(…, newline="")` y respetando el fin de línea. **No uses `Path.write_text`**: convierte los saltos |
| `.gitignore` | Ignora `probar_*.py`, `verificar_*.py`, `temp_*.py` y `diagnostico.py`. No nombres scripts así |
| Secretos | Nunca leer un `.env`, aunque esté abierto en el editor de Harrison. Para revisarlo, solo nombres de variables y "con valor" o "vacía". Las claves se generan con scripts que no las muestran (`scripts/generar_api_key.py`) |
| `psql` desde Git Bash | Las comillas dentro de `sh -c` fallan con textos entre comillas simples. Usa consultas sin literales, o `-F` |
| Puertos | En la PC hay otro proyecto (`cesium`) que usa 5432, 8080, 80, 5000 y 5173. No tocarlo; los nuestros son 8008 y 8000 en `127.0.0.1` |
| Secretos pegados en un chat | En T05, Harrison pegó el contenido de un `.env` en el chat de tarea. 🧪 Quedó en la conversación guardada en la PC (`~/.claude/projects/…/*.jsonl`) y en Anthropic, no en git. Él decidió no cambiar las claves (DEC-71). Si vuelve a pasar: avisar sin repetir la clave, explicar el riesgo real (no es público) y ofrecer el comando que muestra solo los nombres de las variables |
| Rutas y permisos en Java | 🧪 Comparar la ruta cruda (`getRequestURI`) se esquiva con `;x=1` o con letras codificadas (`%73`). Toda regla por ruta tiene que usar la ruta normalizada (`UrlPathHelper`) y una segunda revisión en el controlador. Probarlo con la clave real desde el contenedor `bot`, con cuerpo `{}` (no escribe nada). Aplica al panel (T07) |
| Fin de línea, de verdad | `grep $'$'` en Git Bash no es fiable para contar CRLF: usa Python (`open(f, 'rb')`). Git guarda LF (`core.autocrlf=true`); en la copia de trabajo conviven archivos con CRLF y con LF, y está bien mientras cada uno no los mezcle |
| Java | No hay JDK en Windows. Las pruebas corren en un contenedor Maven contra `insightedu_test`, y tienen un freno: solo corren si la base termina en `_test` |
| IA | Precarga el Agente FAQ (`/health` → `faq_listo`). El modelo `gemini-3.5-flash-lite` ignora `temperature` |
| Discord | Nunca `simulate_students.py`. Un solo bot encendido a la vez |
| Harrison | Principiante en git y Docker: explicar con analogías y tablas. Hace preguntas conceptuales; respóndelas con 📘 cuando haya documentación oficial |

## 6. Hoja de ruta: las próximas fichas

Antes de escribir cada una, revisa sus observaciones en [docs/tareas/README.md](tareas/README.md).

| Ficha | Qué | Objetivo | Puntos que no se pueden olvidar |
|---|---|---|---|
| **T05** | El bot pasa por Java (flujo en vivo) | OE1, OE4 | C2, F5 (responde solo dudas), S8 (menciones desactivadas), S10 (solo `#dudas` y `#logros`), D3, D4 (20 / 30 / 40 s) y un **tope total por pedido en la IA** en `tiempoReal` (observación de T02). La puerta Java en vivo con `seguridad.api-keys.bot`; quitar `/procesar` de la IA; unificar el nombre del token (M3); Dockerfile y servicio `bot` en compose |
| **T06** | Agente-Mod: post de LinkedIn y caso de éxito con la voz de la marca | OE3 | Usa la tabla `borradores`. Decidir si los "logros de aprendizaje" generan borradores (observación de T02). Un solo proveedor (D5). Guía de voz de la marca |
| **T06b** | FAQ semanal (DEC-83) | OE4 | Java junta las `PREGUNTA_FAQ` de la semana (con `respuesta_estado` y `respuesta_texto`, V3) y la IA agrupa las repetidas y escribe un borrador `FAQ` (`mensaje_id` vacío, DEC-33). No usar el historial interno del Agente FAQ (regla 3). Lo primero que se recorta si falta tiempo |
| **T07** | Panel con inicio de sesión: listar, editar, aprobar o rechazar | OE6 | S3, C5, D6 (casilla de consentimiento), clave `panel`, servicio Streamlit en compose: es el **único puerto público** |
| **T08** | Dashboard: las 5 consultas y sus gráficos | OE5 | **Contar solo `estado_clasificacion = OK`** (observación de T01). Consultas en Java con los índices de V1 |
| **T09** | OCI | OE7 | D2 (`generados/` y `aprobados/`), F10 (JSON con Jackson), F11 (solo lo aprobado va a `aprobados/`), una PAR nueva (S4), logs de la IA |
| **T10** | Despliegue y ensayo de la demo | OE9 | O4 (revisar el servidor; Harrison lo pospuso), O3 (cron de la ingesta), red interna o HTTPS para las claves (observación de T03), respaldos y Q7 (guion de la demo) |

Mejoras 🟡 si sobra tiempo: Q3, Q5 (calidad del clasificador), Q6 (CI), O6 (registros), S6, S9, S11, F9, F12 y F15.

## 7. Primeros mensajes

- **Chat principal nuevo** (Opus 5.5): *"Eres el chat principal de InsightEdu Lab (guía, orquestador y auditor). Lee CLAUDE.md y docs/CHAT_PRINCIPAL.md. Tu primera tarea es auditar T04."*
- **Chat de tarea:** *"Eres el chat de la tarea Txx. Lee CLAUDE.md y docs/tareas/Txx-….md y empieza."*, más las decisiones previas que haya tomado Harrison.
