# Informe de la tarea T07 — Panel de curaduría

| Dato | Valor |
|---|---|
| Fecha | 2026-10-04 |
| Modelo de Claude usado | Opus 5.5 |
| Rama | `tarea/T07-panel` |
| Commits | Pendientes: uno para la Parte A (Java) y otro para la Parte B (panel). Los ejecuta Harrison (§7) |

## 1. Resumen

Java tiene 8 puertas nuevas para el panel (listar, ver, editar, aprobar, rechazar y reintentar), que solo abre la clave `panel`. Las protegen la regla del estado `PENDIENTE` ("gana el primero") y el consentimiento (D6), en Java y en la base (V6). El CORS quedó cerrado.
El panel se reescribió con el diseño del viejo: inicio de sesión por persona con hash scrypt, páginas "Borradores" y "Errores", y corre en Docker en `127.0.0.1:8501`.
Las pruebas automáticas pasan (Java 143 y panel 37), y la prueba real de Harrison con los borradores de la base salió completa (§4.3).

## 2. Criterios de terminado

| Criterio | Estado | Evidencia |
|---|---|---|
| Solo se entra con usuario y contraseña, y las contraseñas nunca se guardan en claro | ✅ | `panel/auth.py` (scrypt con sal, `hmac.compare_digest` y hash de relleno para los usuarios que no existen). Pruebas `test_auth.py`, `test_crear_usuario.py` y las de inicio de sesión de `test_paginas.py` |
| Se editan, aprueban y rechazan borradores, con el consentimiento obligatorio en posts y casos de éxito, y sin aprobaciones dobles | ✅ | `CuraduriaApiTest`, casos 3 a 8 (el 7, con dos hilos y 10 vueltas). Panel: `test_un_post_no_se_aprueba_sin_la_casilla`. Prueba real §4.3 |
| Se reintentan los `ERROR` desde el panel | ✅ en pruebas | `CuraduriaApiTest` caso 9: después del reintento, `procesarTanda()` de T04 y de T06 toma el mensaje. Panel: `test_la_pagina_de_errores_reintenta` |
| Las puertas del panel solo aceptan la clave `panel`, y el CORS quedó cerrado | ✅ | `CuraduriaApiTest` casos 1 y 10: sin clave 401; con la clave de `bot` o de `ingesta`, 403, también con `;x=1`, `%65`, `%73`, `//` y `/` al final. Además, la segunda capa en el controlador. Se borró `CorsConfig.java` |
| `PANEL_JAVA_v1.md` está escrito, y el panel corre en Docker en `127.0.0.1:8501` | ✅ | [PANEL_JAVA_v1.md](../contratos/PANEL_JAVA_v1.md). 🧪 `docker compose ps`: `panel Up (healthy)`, junto a `api-java` y los demás. Corre como el usuario `panel` (no root) |
| Las pruebas de Java y de Python pasan, y la prueba real muestra las aprobaciones en la base | ✅ | §4 |
| El informe está completo y no se tocó nada fuera del alcance | ✅ | No se tocó nada fuera del alcance (§6) |

## 3. Archivos cambiados

### Parte A · Java

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `db/migration/V6__curaduria.sql` | Nuevas columnas `rechazado_por`, `rechazado_en` y `motivo_rechazo` (hasta 500 caracteres). `CHECK`: un post o un caso de éxito no queda `APROBADO` sin consentimiento, lo aprobado tiene quién, cuándo y `texto_final`, y lo rechazado tiene quién y cuándo. Dos índices parciales para listar los `ERROR` | V1 no tenía cómo registrar un rechazo. D6 en una segunda capa |
| `curaduria/CuraduriaRepository.java` (nuevo) | El SQL. Cada cambio es un solo `UPDATE … WHERE estado = 'PENDIENTE'` (o `= 'ERROR'` al reintentar) | "Gana el primero" sin bloqueos explícitos |
| `curaduria/CuraduriaService.java` (nuevo) | Las reglas: 404, 409 o 422; validación de `X-Usuario` (`[A-Za-z0-9._-]{1,40}`), de los textos (sin NUL, de 1 a 20 000 caracteres) y del tiempo (0 a 604 800 s). El registro no lleva textos (S11) | Ficha §3.2 |
| `curaduria/VistasPanel.java` (nuevo) | Las formas de pedidos y respuestas (records) | Contrato |
| `controller/BorradorController.java` y `ErroresController.java` (nuevos) | Las 8 puertas. Cada método exige el cliente `panel` (segunda capa, DEC-70) | Ficha §3.1 |
| `seguridad/ApiKeyFilter.java` | `CLIENTE_POR_PREFIJO`: `/api/v1/borradores` y `/api/v1/errores`, y todo lo que cuelga de ellas, son del cliente `panel`. Usa la misma ruta normalizada | Las rutas llevan un id, y el mapa viejo solo comparaba la ruta exacta |
| `seguridad/ClientePermitido.java` | La constante `PANEL` | — |
| `error/ConflictoException.java` y `DatoInvalidoException.java` (nuevos), `ManejadorErrores.java` | Las respuestas 409 (`CONFLICTO`) y 422 (`DATO_INVALIDO`, con el campo), y un 422 para un parámetro con mal formato (por ejemplo, `/borradores/abc`) | Códigos de la ficha §3.6 |
| `config/CorsConfig.java` | **Borrado** | S6: aceptaba cualquier origen con credenciales |
| `application.properties` | `seguridad.api-keys.panel=${API_KEY_PANEL:}` | — |
| `test/.../CuraduriaApiTest.java` (nuevo) | 33 pruebas | Ficha §5 |
| `test/.../GeneracionTest.java` | Una prueba aprobaba un borrador con un `UPDATE` sin quién ni consentimiento: ahora los completa | La V6 lo rechazaría (es justo lo que tiene que impedir) |

### Parte B · Panel, Docker y documentación

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `panel/app.py` | Reescrito: configuración de la página, los estilos del panel viejo, el inicio y el cierre de sesión (con pausa de 2 s por fallo, bloqueo y vencimiento a las 8 h sin uso) y la navegación entre páginas | DEC-109, DEC-110 y DEC-114 |
| `panel/auth.py` (nuevo) | Hash scrypt (n = 2¹⁴, r = 8, p = 1, sal de 16 bytes), lectura de `PANEL_USUARIOS` (con topes, para que un valor alterado no pida GB de memoria) y `ControlIntentos` (5 fallos → 5 minutos) | S3 |
| `panel/cliente_java.py` (nuevo) | Cliente `httpx`: `X-Api-Key` siempre, `X-Usuario` en los cambios y cuerpo JSON en todo POST y PUT (para que lleven `Content-Length`). Convierte los `ErrorApi` en `ErrorJava`, sin detalles internos | C5 y observación de T03 (411) |
| `panel/ui.py` (nuevo) | Estilos, cliente compartido, fechas en hora de Bogotá y `mostrar_texto()` (`st.code`, sin interpretar) | §11 de la ficha |
| `panel/paginas/borradores.py` y `errores.py` (nuevos) | Las dos páginas | Ficha §3.9 y §3.10 |
| `panel/mock_data.json` | **Borrado** | DEC-109 |
| `panel/Dockerfile`, `.dockerignore`, `requirements.txt` y `.streamlit/config.toml` (nuevos) | Imagen `python:3.12-slim` con un usuario sin privilegios y prueba de salud en `/_stcore/health`. Streamlit sin estadísticas de uso, con protección XSRF y sin detalles de errores en el navegador (`showErrorDetails = "none"`). `streamlit==1.65.0` fijo | Ficha §3.12 |
| `panel/tests/` (nuevo) | 37 pruebas (AppTest, `httpx.MockTransport`, script) | Ficha §5 |
| `scripts/crear_usuario_panel.py` (nuevo) | Pide la contraseña dos veces con `getpass` y escribe solo `PANEL_USUARIOS`, respetando los saltos de línea. No pisa un usuario sin `--reemplazar` | Ficha §3.8 |
| `scripts/generar_api_key.py` | `--cliente panel` | Ficha §3.12 |
| `compose.yml` | Servicio `panel` (`127.0.0.1:8501`, `depends_on` de `api-java` sano) y `API_KEY_PANEL` para `api-java` | Ficha §3.12 |
| `.env.example` | `API_KEY_PANEL` y `PANEL_USUARIOS` | — |
| `docs/contratos/PANEL_JAVA_v1.md` (nuevo) | El contrato | DEC-112 |
| `docs/OPERACION.md` | Sección 10 (panel), variables, servicios y puertos; V6 y V7. El `UPDATE` a mano de la §8 se reemplazó por el botón Reintentar | Ficha §3.13 |

## 4. Pruebas

| Comando ejecutado | Resultado (🧪) |
|---|---|
| `docker run … maven:3.9-eclipse-temurin-21 mvn test` (contra `insightedu_test`, [OPERACION.md §5](../OPERACION.md)) | **143 pruebas, 0 fallos y 0 errores** (110 de antes y 33 de `CuraduriaApiTest`). La primera corrida tuvo 3 errores en mis pruebas (creaban un borrador sin su mensaje); se corrigieron y se volvió a correr todo |
| `python -m pytest panel/tests -q` | **37 passed** |
| `python -m pytest agents/orquestador/tests -q` | 79 passed |
| `python -m pytest agents/bot_discord/tests -q` | 22 passed, 1 warning (ya estaba) |
| `python -m pytest -q` (desde `ingestion/discord`) | 36 passed |
| `docker compose config --quiet` | Válido |
| `docker compose build panel` y la imagen encendida sola 20 s en `127.0.0.1:18501` | `healthy`, la página respondió `200` y el usuario es `panel` (no root). Se detuvo enseguida |

### 4.1 Java: los casos de la ficha

| # | Caso | Prueba(s) en `CuraduriaApiTest` |
|---|---|---|
| 1 | Sin clave 401; con la clave de `bot` o de `ingesta`, 403; ruta disfrazada, 403 | `sinClaveEs401`, `lasClavesDelBotYDeLaIngestaNoAbrenLasPuertasDelPanel`, `laClaveDelBotNoEntraConUnaRutaDisfrazada` (6 rutas), `laClaveDelBotNoApruebaConUnaRutaDisfrazada`, `laClaveDelPanelNoAbreLasPuertasDeLaIngestaNiDelBot`, `segundaCapaElControladorRechazaOtroCliente` |
| 2 | Listar y ver el detalle, con el contexto | `listaLosPendientesConSuContexto`, `elDetalleTraeElMensajeOriginalYElMotivoDeLaIa`, `elDetalleDeLaFaqTraeSuSemana`, `unBorradorQueNoExisteEs404YUnFiltroRaroEs422` |
| 3 | Editar y aprobar | `editarYDespuesAprobarGuardaElTextoEditadoYQuienAprobo`, `editarYAprobarEnElMismoPaso`, `sinEdicionElTextoFinalQuedaIgualAlDeLaIa`, `sinUsuarioOConUnUsuarioRaroEs422`, `unaEdicionVaciaOSinTiempoEs422`, `unCaracterNulEnLaEdicionSeQuita` |
| 4 | Un post sin consentimiento | `unPostSinConsentimientoNoSeAprueba` (422, sigue `PENDIENTE`), `laV6ImpideEnLaBaseUnPostAprobadoSinConsentimiento` |
| 5 | La FAQ sin consentimiento | `laFaqSeApruebaSinConsentimiento` |
| 6 | Algo que ya no está `PENDIENTE` | `aprobarEditarORechazarAlgoYaRevisadoEs409` |
| 7 | Dos aprobaciones a la vez | `dosAprobacionesALaVezUnaGanaYLaOtraRecibe409` (10 vueltas: siempre 1 gana y 1 recibe 409, y lo guardado es todo del ganador) |
| 8 | Rechazar | `rechazarGuardaQuienCuandoYElMotivo`, `rechazarSinMotivoTambienSirve` |
| 9 | Reintentar clasificación y generación | `unaClasificacionEnErrorVuelveALaColaYLaTomaLaTarea`, `unaGeneracionEnErrorVuelveALaColaYLaTomaLaTarea`, `reintentarSinUsuarioEs422` |
| 10 | CORS | `unNavegadorDeOtroOrigenNoRecibeCabecerasCors` (con clave, una petición preliminar `OPTIONS` con clave y otra sin clave: ninguna trae `Access-Control-Allow-*`) |
| 11 | Las 110 anteriores | Pasan (total 143) |

### 4.2 Panel: los casos de la ficha

| Caso | Prueba(s) |
|---|---|
| Inicio de sesión correcto, incorrecto y sin usuarios | `test_la_contrasena_correcta_entra_…`, `test_una_contrasena_equivocada_no_entra`, `test_un_usuario_que_no_existe_recibe_el_mismo_mensaje`, `test_sin_usuarios_configurados_no_se_puede_entrar`, `test_cinco_fallos_bloquean_…`, `test_cerrar_sesion` |
| El hash nunca es la contraseña | `test_el_hash_nunca_es_la_contrasena_y_lleva_sal` |
| El script no muestra la contraseña y conserva el `.env` | `test_crea_el_usuario_sin_mostrar_…`, `test_conserva_el_resto_del_env_y_sus_saltos_de_linea` (CRLF), `test_main_pide_la_contrasena_con_getpass_…` y 4 más |
| El cliente envía la clave y el usuario | `test_cada_pedido_lleva_la_clave_…`, `test_los_post_y_put_llevan_content_length_…` y 5 más |
| No se aprueba un post sin la casilla | `test_un_post_no_se_aprueba_sin_la_casilla` (el botón queda apagado y AppTest no deja pulsarlo, igual que un navegador; con la casilla se envía `consentimiento = true`) |
| Un `<script>` se muestra escapado | `test_un_texto_con_html_se_muestra_escapado` (aparece tal cual en `st.code`, `st.text` y el área de texto, y en ningún markdown) y en la página de errores |

### 4.3 Prueba real (la corrió Harrison el 2026-10-04)

Con la clave `panel`, el usuario `harrison` creado con el script y `docker compose up -d --build api-java panel`. 🧪 `flyway_schema_history`: la última versión es `6 · curaduria`.

| Paso de la ficha | Resultado | Evidencia |
|---|---|---|
| Contraseña equivocada | ✅ "Usuario o contraseña incorrectos" | 🧪 Registro del panel: `21:12:15 WARNING panel: Intento de inicio de sesión fallido` y, después, `21:12:35 INFO panel: Inicio de sesión: harrison` |
| Un post **no** se aprueba sin la casilla | ✅ | Harrison: "si no se selecciona la casilla el botón está deshabilitado". No deja rastro en la base: Java ni siquiera recibe el pedido |
| Aprobar un post con la casilla | ✅ | #1 |
| Editar y aprobar un caso de éxito | ✅ | #2 (`editado = t`) |
| Rechazar otro | ✅ | #4, con su motivo |
| Aprobar la FAQ (sin casilla) | ✅ | #11 |

Registro de `api-java` (sin textos, S11):
```
Borrador 1 (POST_LINKEDIN) aprobado por harrison en 179 s
Borrador 2 (CASO_EXITO) aprobado por harrison en 139 s, con edición
Borrador 4 (CASO_EXITO) rechazado por harrison
Borrador 11 (FAQ) aprobado por harrison en 1000 s
```

Consulta de solo lectura ([OPERACION.md §10](../OPERACION.md)), solo los revisados. Los otros 7 siguen `PENDIENTE`:
```
 id |     tipo      |  estado   | aprobado_por | tiempo_curaduria_seg | consentimiento_confirmado | rechazado_por | editado
----+---------------+-----------+--------------+----------------------+---------------------------+---------------+---------
  1 | POST_LINKEDIN | APROBADO  | harrison     |                  179 | t                         |               | f
  2 | CASO_EXITO    | APROBADO  | harrison     |                  139 | t                         |               | t
  4 | CASO_EXITO    | RECHAZADO |              |                   51 | f                         | harrison      | f
 11 | FAQ           | APROBADO  | harrison     |                 1000 | f                         |               | f
```
`motivo_rechazo` de #4: "El alumno no permitio publicarlo".

**Error encontrado en la prueba, y corregido:** la primera versión de la consulta usaba `texto_final IS DISTINCT FROM texto_ia AS editado`, que marcaba `t` en todos los borradores sin editar (porque `texto_final` está vacío). Se cambió a `(texto_final IS NOT NULL AND texto_final <> texto_ia)`. Solo afectaba a la consulta del documento, no a los datos.

🔎 **Los 1000 s de la FAQ:** el tiempo corre desde la primera vez que se abre el borrador en la sesión, aunque se mire otro mientras tanto. La FAQ se había abierto en la primera parte de la prueba y se aprobó unos 17 minutos después. Ver §6, punto 13.

## 5. Decisiones que se tomaron

Las validó Harrison el 2026-10-04, antes de empezar (puntos a–h de la propuesta del chat).

| Decisión | Alternativas descartadas | ¿Cambia el contrato, la arquitectura o D1 a D7? |
|---|---|---|
| V6 con las columnas del rechazo y `CHECK` de D6 y de "quién y cuándo" | Guardar el rechazo en `aprobado_por` (confuso) | No. Es una migración nueva (V1 a V5 no se tocaron) |
| `aprobar` acepta el texto editado: editar y aprobar ocurren juntos | Siempre `PUT` y después `aprobar` (podía quedar a medias) | No |
| `X-Usuario` con el formato `[A-Za-z0-9._-]{1,40}`, el mismo en Java y en el script | Cualquier texto: podría meter líneas falsas en el registro | No |
| `PANEL_USUARIOS` = `usuario:scrypt:n:r:p:sal:hash`, separados por coma, sin `$` | Formato `$scrypt$…`: 🔎 Compose reemplaza lo que va después de `$` | No |
| 2 s de pausa por fallo; 5 fallos seguidos bloquean ese usuario 5 minutos (exista o no), uno por proceso | Solo la pausa (se esquivaba abriendo pestañas nuevas) | No |
| Dos ediciones a la vez: queda la última. Aprobar o rechazar: gana el primero | Bloqueo optimista con versión (más complejo) | No |
| Reintentar solo la clasificación y la generación; la FAQ semanal en `ERROR`, no | Incluirla (fuera de la ficha) | No |
| No se tocó la entidad `Mensaje`: el panel lee con SQL directo | Agregar las columnas de V3 y V4 a la entidad | No |
| Decisiones menores del chat de tarea: `PANEL_JAVA_URL` fija en `compose.yml` (`http://api-java:8080`), como `BOT_JAVA_URL`, y no en `.env.example`; las fechas en hora de Bogotá (`PANEL_ZONA`); la sesión vence a las 8 h sin uso | — | No |

## 6. Dudas, riesgos y pendientes

| # | Tema | Detalle | Va a |
|---|---|---|---|
| 1 | Prueba real | Pendiente (§4.3) | Harrison, antes de auditar |
| 2 | La sesión vive en la pestaña | Si se recarga la página (F5), hay que volver a entrar: Streamlit guarda la sesión por conexión. Para el MVP, es aceptable | 🟡 |
| 3 | Bloqueo a propósito | Alguien que conozca un usuario puede bloquearlo 5 minutos con 5 contraseñas falsas. El contador vive en memoria: `docker compose restart panel` lo borra | 🟡 / T10 |
| 4 | HTTPS | Usuario y contraseña viajan sin cifrar entre el navegador y el panel. En `127.0.0.1` no importa; en el servidor hace falta HTTPS (DEC-56) | T10 |
| 5 | Ediciones simultáneas | Si dos personas editan el mismo borrador, la segunda que guarda pisa a la primera sin aviso. Aprobar o rechazar sí está protegido | 🟡 |
| 6 | Motivo de los `ERROR` de clasificación | No se guarda en la base (solo en el registro de `api-java`), así que la página "Errores" lo muestra vacío. Haría falta una columna (observación de T04) | 🟡 |
| 7 | FAQ semanal en `ERROR` | No tiene botón de reintentar (fuera de la ficha) | 🟡 |
| 8 | Nombre dentro de una duda (DEC-108) | El panel muestra un aviso en la FAQ ("Revisa que ninguna pregunta incluya el nombre de un alumno"), pero sigue dependiendo de la revisión humana | Riesgo aceptado |
| 9 | 🔎 "External URL" en el registro del panel | Al arrancar, Streamlit consulta un servicio externo para averiguar la IP pública y la escribe en el registro. No expone nada (el puerto está en `127.0.0.1`), pero es una salida a internet que no hace falta | 🟡 / T10 |
| 10 | Documentos del chat principal | No se tocaron `CLAUDE.md` (tabla de servicios: el panel ya no está "pendiente"; falta el contrato nuevo en el mapa), `docs/tareas/README.md` ni `DECISIONES.md` | Chat principal |
| 11 | Entidad `Mensaje` | Sigue sin las columnas de V3 y V4 | T08 |
| 12 | `streamlit` en el entorno | Se instaló `streamlit` 1.65.0 en `%USERPROFILE%\.venvs\insightedu-discord`, con permiso de Harrison, para correr las pruebas del panel | Anotar en `CLAUDE.md` §4 (chat principal) |
| 13 | Cómo se mide el tiempo de curaduría | Cuenta desde la primera vez que se abre el borrador en la sesión, aunque después se mire otro (la FAQ de la prueba dio 1000 s). Para medir solo el tiempo frente al borrador, habría que pausar el reloj al cambiar de borrador. Tenerlo en cuenta al leer el indicador | T08 (dashboard) o 🟡 |

## 7. Comandos que ejecutó Harrison

Desde la raíz del repositorio:

1. `python scripts/generar_api_key.py --cliente panel`
2. `python scripts/crear_usuario_panel.py --usuario harrison`
3. `docker compose up -d --build api-java panel`
4. La prueba en `http://127.0.0.1:8501` y las consultas de §4.3.
5. Los commits de la Parte A y de la Parte B, y el `push` (los da el chat de tarea al final).
