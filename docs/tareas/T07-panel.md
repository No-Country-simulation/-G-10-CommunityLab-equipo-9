# T07 · Panel de curaduría: iniciar sesión, editar, aprobar o rechazar borradores

| Dato | Valor |
|---|---|
| Fase del plan | 5 · Panel y dashboard ([análisis §9](../ANALISIS_INGENIERIA_PROPUESTA_3.md#9-prioridades-y-orden)) |
| Objetivos | **OE6** (panel con inicio de sesión para revisar, editar, aprobar o rechazar, con la casilla de consentimiento). Es de lo último que se recorta (DEC-11) |
| Hallazgos que resuelve | S3 (inicio de sesión), S6 (CORS), S12 y D6 (consentimiento), C5 (panel → Java) y observaciones de T04, T06 y T06b ([README](README.md)) |
| Tamaño | L (puertas nuevas en Java, un panel nuevo en Streamlit, un contrato y Docker) |
| Modelo de Claude recomendado | **Opus 5.5**: seguridad (inicio de sesión, la única pieza abierta a internet) y concurrencia (dos personas aprobando a la vez) |
| Depende de | T03 ✅ y T05 ✅ (`ApiKeyFilter` con ruta normalizada y cliente por puerta, DEC-70), T06 ✅ y T06b ✅ (los borradores). **Reutilizarlos** |
| Rama | `tarea/T07-panel` |
| Decisiones previas 👤 | Las de la sección 1.1, validadas por Harrison el 2026-10-04 |

## 1. Objetivo

Que una persona de Marketing entre al panel con **su usuario y su contraseña**, vea los borradores pendientes (posts de LinkedIn, casos de éxito y la FAQ semanal) junto al mensaje que les dio origen, y pueda **editarlos, aprobarlos o rechazarlos**.

Un post o un caso de éxito que nombra a un alumno **solo se aprueba si se marca la casilla de consentimiento** (D6). Queda registrado quién aprobó, cuándo y cuánto tardó la revisión.

Hoy esperan **11 borradores**: 5 posts, 5 casos de éxito y 1 FAQ.

### 1.1 Decisiones previas 👤 (2026-10-04)

| # | Pregunta | Decisión | Descartada |
|---|---|---|---|
| 1 | ¿Qué hacemos con el panel que existe? (DEC-109) | **Conservar su diseño** (título, tarjetas, botón índigo y estilos de `panel/app.py`) y **reescribir los datos**: se va `mock_data.json` y el modelo de "un paquete por lote" | Empezar de cero |
| 2 | ¿Cómo se inicia sesión? (DEC-110) | **Usuario y contraseña por persona.** Las contraseñas se guardan **cifradas** (un hash) en el `.env`, con un script que no las muestra. Así se sabe quién aprobó cada borrador | Una contraseña compartida: cualquiera podría firmar como otra persona |
| 3 | ¿Se puede reintentar lo que quedó en `ERROR`? (DEC-111) | **Sí:** un botón que devuelve a la cola los mensajes con la clasificación en `ERROR` y los logros con la generación en `ERROR` | Dejarlo para después |
| 4 | ¿Cómo habla el panel con Java? (DEC-112) | **Contrato nuevo, `docs/contratos/PANEL_JAVA_v1.md`**, con una clave propia (`panel`) que **solo** abre las puertas del panel (DEC-70) | Leer la base directo: rompe la regla 2 de la propuesta 3 |

Decisiones del chat principal (Harrison no se opuso):
- **DEC-113:** aprobar solo cambia el estado en la base; subir a OCI es T09.
- **DEC-114:** el panel queda preparado para tener varias páginas, porque el dashboard (T08) será otra página.

## 2. Contexto que hay que leer

| Qué | Dónde |
|---|---|
| N6: el panel muestra lo pendiente, Marketing edita o aprueba, Java guarda la aprobación | [PDF de la propuesta 3](../referencias/Propuesta_3_Arquitectura_InsightEdu.pdf), §6 (N6) |
| S3, S6, S12 y C5 | [Análisis](../ANALISIS_INGENIERIA_PROPUESTA_3.md) §2 y §3 |
| D6 (consentimiento), DEC-42 (el panel es el único servicio público), DEC-70 (cada clave, su puerta), DEC-81 (primer nombre) y DEC-91 (reintentos) | [DECISIONES.md](../DECISIONES.md) |
| La tabla `borradores` (`texto_ia`, `texto_final`, `estado`, `consentimiento_confirmado`, `aprobado_por`, `aprobado_en`, `tiempo_curaduria_seg`) y las columnas de generación y de la FAQ | Migraciones V1, V4 y V5; `model/Borrador.java` |
| La API key por cliente y la ruta normalizada (la lección de la auditoría de T05) | `seguridad/ApiKeyFilter.java`, `ClientePermitido.java` y [CHAT_PRINCIPAL.md §5](../CHAT_PRINCIPAL.md) |
| El panel viejo, por su diseño | `panel/app.py` |
| Observaciones que pasan a esta tarea: reintentar los `ERROR`, consentimiento, `OPTIONS` con 401, `Content-Length`, entidad `Mensaje` sin las columnas de V3 y V4, nombre dentro de una duda | [README de tareas](README.md) |

## 3. Alcance: qué entra

### Parte A · Java

1. **Puertas del panel**, que **solo** puede usar el cliente `panel` (`seguridad.api-keys.panel`, variable `API_KEY_PANEL`). Usan el mismo filtro con la ruta normalizada y la segunda revisión en cada controlador (DEC-70). La forma exacta la fija el contrato:

   | Para qué | Ejemplo |
   |---|---|
   | Listar borradores, filtrando por estado y tipo | `GET /api/v1/borradores?estado=PENDIENTE&tipo=…` |
   | Ver un borrador con su contexto: el mensaje original (canal, fecha, texto, nombre visible del autor), el motivo de la IA y, en la FAQ, la semana | `GET /api/v1/borradores/{id}` |
   | Guardar una edición (`texto_final`) | `PUT /api/v1/borradores/{id}` |
   | Aprobar | `POST /api/v1/borradores/{id}/aprobar` |
   | Rechazar | `POST /api/v1/borradores/{id}/rechazar` |
   | Listar y reintentar lo que quedó en `ERROR` (clasificación y generación) | `GET` y `POST …/reintentar` (DEC-111) |

2. **Reglas al aprobar o rechazar:**
   - solo se editan, aprueban o rechazan borradores **`PENDIENTE`**; si no, **409**;
   - **dos personas a la vez:** gana la primera y la otra recibe 409 (`UPDATE … WHERE estado = 'PENDIENTE'`);
   - **consentimiento (D6):** un `POST_LINKEDIN` o un `CASO_EXITO` **no se aprueba sin `consentimiento = true`**. La FAQ no lo necesita, porque no nombra alumnos;
   - al aprobar se guardan `aprobado_por` (el usuario del panel), `aprobado_en`, `tiempo_curaduria_seg` y `consentimiento_confirmado`. Si no se editó, `texto_final` queda igual a `texto_ia`;
   - al rechazar, quién y cuándo, y opcionalmente el motivo. Si V1 no alcanza, se agregan columnas en una **`V6__…`**;
   - el usuario lo envía el panel en una cabecera (por ejemplo, `X-Usuario`). Java confía en él porque solo el panel tiene la clave, pero lo valida: no vacío y con largo máximo.
3. **Reintentar:** la clasificación en `ERROR` vuelve a `PENDIENTE` con sus intentos en 0; la generación en `ERROR` vuelve a "sin generar". Las tareas de T04 y T06 los toman en su vuelta siguiente.
4. **S6:** cerrar el CORS abierto (`CorsConfig`). El panel llama a Java **desde el servidor**, no desde el navegador.
5. Si hace falta, la entidad `Mensaje` suma las columnas de V3, V4 y V5 que lean estas puertas (observación de T05 y T06).
6. **Contrato `PANEL_JAVA_v1.md`** (DEC-112): cada puerta con un ejemplo de pedido y de respuesta, los códigos de error (401, 403, 404, 409, 422) y las reglas del punto 2.

### Parte B · El panel

7. **Reescribir `panel/`** conservando el diseño del panel viejo (DEC-109). Se borra `mock_data.json`. El panel habla **solo con Java**: nunca con la base ni con la IA.
8. **Inicio de sesión** (DEC-110, S3):
   - usuarios y hashes en una variable del `.env` de la raíz (por ejemplo, `PANEL_USUARIOS`);
   - un hash lento con sal (por ejemplo, `hashlib.scrypt` o `pbkdf2_hmac`, de la biblioteca estándar), comparado en tiempo constante;
   - una pausa después de cada intento fallido, y un botón para cerrar sesión;
   - **sin usuarios configurados, el panel no deja entrar a nadie**;
   - un script, `scripts/crear_usuario_panel.py`, pide la contraseña sin mostrarla (`getpass`) y escribe el hash en el `.env`, igual que `generar_api_key.py`. Ojo: el `.gitignore` ignora los nombres `probar_*`, `verificar_*` y `temp_*`.
9. **Página "Borradores"**:
   - la lista de pendientes, con filtros por tipo;
   - el detalle: el mensaje original y el motivo de la IA, el texto editable, la casilla de consentimiento (obligatoria en posts y casos de éxito) y los botones aprobar y rechazar;
   - se mide el tiempo de curaduría desde que se abre el borrador;
   - se muestran también los ya aprobados y rechazados, solo para leer.
10. **Página "Errores":** la lista de lo que quedó en `ERROR`, con su botón de reintentar.
11. **Seguridad de lo que se muestra:** los textos de alumnos y de la IA se muestran **escapados**, nunca con `unsafe_allow_html` (evita que un mensaje meta HTML o scripts en el panel). Los registros no tienen textos (S11).
12. **Docker:** un `Dockerfile` para el panel y el servicio `panel` en `compose.yml`, en `127.0.0.1:8501` en la PC (en el servidor será el único público, T10), con `depends_on` de `api-java` sano. Variables nuevas en `.env.example`: `API_KEY_PANEL`, `PANEL_USUARIOS` y la URL de Java. `scripts/generar_api_key.py --cliente panel`.
13. **`docs/OPERACION.md`:** cómo crear un usuario, entrar al panel y apagarlo.

## 4. Fuera de alcance

- Subir a OCI lo aprobado (T09, DEC-113). El dashboard (T08).
- Volver a generar un borrador (🟡). Publicar en LinkedIn (lo hace Marketing, a mano).
- Roles, permisos distintos por usuario y JWT (fuera del MVP, análisis §9). HTTPS (T10).
- Cambiar el bot, la IA, la ingesta o los contratos existentes.
- **No ejecutar `simulate_students.py`** ni encender un segundo bot.

## 5. Pruebas exigidas

**Java** (PostgreSQL real):

| # | Caso | Resultado esperado |
|---|---|---|
| 1 | Las puertas sin clave / con la clave de `bot` o de `ingesta` / con una ruta disfrazada (`;x=1`, `%xx`, `//`) | 401 / 403 / 403 |
| 2 | Listar pendientes y ver el detalle | Trae el contexto del mensaje y el motivo |
| 3 | Editar y aprobar | `texto_final` editado, `APROBADO`, `aprobado_por`, `aprobado_en` y el tiempo |
| 4 | Aprobar un post sin consentimiento | Rechazado (422 o 409), sigue `PENDIENTE` |
| 5 | Aprobar la FAQ sin consentimiento | Se aprueba |
| 6 | Aprobar o editar un borrador que ya no está `PENDIENTE` | 409 |
| 7 | Dos aprobaciones a la vez | Una gana y la otra recibe 409 |
| 8 | Rechazar | `RECHAZADO`, con quién y cuándo |
| 9 | Reintentar una clasificación y una generación en `ERROR` | Vuelven a la cola, y la tarea correspondiente las toma |
| 10 | Un pedido de un navegador con otro origen (CORS) | Sin cabeceras CORS abiertas |
| 11 | Las 110 pruebas anteriores | Siguen pasando |

**Python, panel** (sin Java real: con un cliente simulado):
- inicio de sesión correcto, incorrecto y sin usuarios configurados;
- el hash nunca es la contraseña;
- el script crea el hash sin mostrar la contraseña y conserva el resto del `.env`;
- el cliente envía la clave y el usuario;
- no se puede aprobar un post sin la casilla;
- un texto con `<script>` se muestra escapado.

Con `streamlit.testing` (AppTest) si es posible.

**Prueba real, la corre Harrison** (no gasta Gemini):
1. `python scripts/generar_api_key.py --cliente panel`, `python scripts/crear_usuario_panel.py` (con su nombre) y `docker compose up -d --build`.
2. Abrir `http://127.0.0.1:8501`, probar una contraseña equivocada y después entrar.
3. Con los borradores reales: aprobar un post marcando el consentimiento, editar y aprobar un caso de éxito, rechazar otro, aprobar la FAQ y comprobar que un post **no** se aprueba sin la casilla.
4. Consulta de solo lectura: estados, `aprobado_por`, `tiempo_curaduria_seg` y `consentimiento_confirmado`. Se pegan las salidas en el informe.

## 6. Criterios de terminado

- [ ] Solo se entra con usuario y contraseña, y las contraseñas nunca se guardan en claro.
- [ ] Se editan, aprueban y rechazan borradores, con el consentimiento obligatorio en posts y casos de éxito, y sin aprobaciones dobles.
- [ ] Se reintentan los `ERROR` desde el panel.
- [ ] Las puertas del panel solo aceptan la clave `panel`, y el CORS quedó cerrado.
- [ ] `PANEL_JAVA_v1.md` está escrito, y el panel corre en Docker en `127.0.0.1:8501`.
- [ ] Las pruebas de Java y Python pasan, y la prueba real muestra las aprobaciones en la base (🧪 con la salida en el informe).
- [ ] El informe `docs/tareas/T07-informe.md` está completo, y no se tocó nada fuera del alcance.

## 7. Comandos de git para Harrison

**Al empezar**, desde `C:\Users\LENOVO\Documents\Cursos\No Country\Hackaton ONE 10\insightedu-lab`, **después de subir la ficha** y con `git status` en `working tree clean`:
```
git switch feature/integracion-arquitectura-3
git pull
git switch -c tarea/T07-panel
```

**Al terminar:** el chat de tarea da los comandos de commit (un solo `-m`, **sin** `Co-Authored-By`: DEC-65), uno por parte (A y B). Después:
```
git push -u origin tarea/T07-panel
```

Luego le dices al chat principal **"T07 terminó"**.

## 8. Cómo abrir el chat de esta tarea

1. En VS Code, abrir un chat nuevo de Claude Code **en esta misma carpeta**.
2. Elegir el modelo **Opus 5.5** con `/model`.
3. Primer mensaje: *"Eres el chat de la tarea T07. Lee CLAUDE.md y docs/tareas/T07-panel.md y empieza."*

⚠️ **Nunca pegues el contenido de un `.env` en el chat.** Para revisarlo, usa `Get-Content .env | ForEach-Object { ($_ -split '=')[0] }`, que muestra solo los nombres de las variables. Tampoco escribas tu contraseña del panel en el chat: el script te la pide en la terminal.
