# Informe de la tarea T13 — Borradores por logro, estado en LinkedIn y reintento de la FAQ

| Dato | Valor |
|---|---|
| Fecha | 2026-10-15 |
| Modelo de Claude usado | Opus 5.5 |
| Rama | `tarea/T13-borradores` |
| Commits | `d1c3790` (Parte A: Java y contrato), `5ecc982` (Parte B: panel), `77494a8` (Parte C: documentación) y el de este informe al día |

## 1. Resumen

La página **Borradores** es ahora una cola de logros con el diseño del prototipo: una tarjeta por logro (post + caso de éxito) y una por FAQ, con botones por texto, un solo consentimiento, el contador de la guía de voz y el aviso de LinkedIn antes de aprobar. Java guarda en la `V9` si cada post se publicó en LinkedIn (M12), y la página Errores reintenta la FAQ semanal. 🧪 Pasan 256 pruebas de Java y 136 del panel. 🧪 La prueba real de Harrison (sección 7) dio lo esperado en sus 9 pasos; la base real ya tiene la `V9`.

## 2. Criterios de terminado

| Criterio | Estado | Evidencia |
|---|---|---|
| La página Borradores sigue el prototipo zona por zona, con las piezas de T12 en `panel/estilo.py`, y el dashboard se ve igual que antes | ✅ | Capturas de la sección 4.3. El dashboard: misma imagen salvo el título del panel (pasó a la barra lateral, como pide la ficha) y la columna nueva "En LinkedIn". `test_dashboard.py` pasa (una aserción adaptada, sección 5) |
| Cada texto tiene sus botones y su tiempo, con un solo consentimiento por tarjeta, y la edición no se pierde al cambiar de pestaña | ✅ | `test_aprobar_el_post_y_despues_el_caso_cada_uno_con_su_tiempo`, `test_guardar_edicion_y_rechazar_tocan_solo_su_texto`, `test_una_edicion_no_se_pierde_al_cambiar_de_pestana_ni_de_tarjeta` |
| El botón del post dice antes de aprobar qué pasará en LinkedIn y, si va a publicar, pide confirmar | ✅ | `test_el_boton_del_post_dice_antes_de_aprobar_que_pasara_en_linkedin` (los 4 casos de la tabla); captura `real-confirmar` |
| Ningún texto ni nombre de alumno o de la IA va en HTML, en markdown o en una etiqueta sin escapar | ✅ | `test_un_nombre_con_markdown_o_html_se_ve_tal_cual` (5 nombres), `test_un_texto_con_html_se_muestra_escapado`, `test_un_nombre_escapado_se_ve_tal_cual` (10 casos) |
| La `V9` guarda el estado en LinkedIn, el panel lo muestra en Borradores y en el dashboard, y un post de más de 3.000 caracteres no se puede aprobar | ✅ (también en la prueba real, sección 7) | Java: `laV9AgregaLasColumnas…`, `aprobarUnPostConLinkedinApagado…`, `elEstadoEnLinkedinSeGuardaUnaSolaVez…`. Panel: `test_un_post_aprobado_dice_que_paso_en_linkedin`, `test_contenido_dice_si_cada_post_se_publico_en_linkedin`, `test_el_contador_cuenta_como_java…` |
| La FAQ en `ERROR` se reintenta desde Errores | ✅ | Java: `reintentarUnaFaqEnErrorLaDevuelveALaColaYLaArmaEnSegundoPlano` y sus 409/404/422/401/403. Panel: `test_la_pagina_de_errores_reintenta_una_faq` |
| El contrato solo agrega, y está en `PANEL_JAVA_v1.md` con ejemplos | ✅ | `git diff docs/contratos/PANEL_JAVA_v1.md`: las líneas con `-` son comas nuevas en los JSON o frases ampliadas; ningún campo cambió |
| Las pruebas de Java y del panel pasan, y las capturas en claro y en oscuro están descritas | ✅ | Sección 4 |
| DEC-159 a DEC-161, DEC-151 en 🔁, ARQUITECTURA, AGENTS (`V10`), OPERACION, ESTADO y diseno/README al día | ✅ | Sección 3 |
| El informe está completo, y no se tocó nada fuera del alcance | ✅ | Este archivo. No se tocaron la IA, el Agente-Mod, el bot, la ingesta ni OCI; no se encendió LinkedIn; no se aprobó ni editó nada de la base real |

## 3. Archivos cambiados

**Parte A · Java y el contrato**

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `db/migration/V9__estado_linkedin.sql` (nuevo) | `linkedin_estado`, `linkedin_post_id`, `linkedin_en`, `linkedin_motivo` en `borradores`, con `borradores_linkedin_check` (solo un `POST_LINKEDIN` `APROBADO`, con fecha) y `borradores_linkedin_publicado_check` (el URN solo en `PUBLICADO`) | Punto 1 |
| `linkedin/LinkedinPostResponse.java` | Pasa a `estado`, `idPost` y `motivo` | Un resultado que se guarda, con motivo fijo |
| `linkedin/LinkedinHttpException.java` (nuevo) | Excepción con solo el código HTTP | Que el motivo nunca lleve el cuerpo de LinkedIn |
| `linkedin/LinkedinClient.java` | Lanza `LinkedinHttpException` | Ídem |
| `linkedin/LinkedinService.java` | `modo()` (`APAGADO`/`SIMULADO`/`REAL`); motivos fijos ("Pasa de 3.000 caracteres", "Texto vacío", "LinkedIn respondió HTTP n", "LinkedIn no respondió a tiempo", "No se pudo conectar con LinkedIn", "Falló la publicación en LinkedIn"); el registro ya no lleva `e.getMessage()` | Puntos 2 y 3 |
| `curaduria/VistasPanel.java` | `ResumenBorrador` + `mensajeId`, `motivoIa`, `linkedin`; `ListaBorradores` + `linkedinModo`; `DetalleBorrador` + `linkedin`; `EstadoLinkedin`, `SemanaEnError`, `ListaErrores` + `faq`, `ReintentoFaq` | Puntos 3 a 6 |
| `curaduria/CuraduriaRepository.java` | SQL de la lista y el detalle con lo nuevo; `guardarLinkedin` (con la guarda), `erroresFaq`, `reintentarFaq`, `existeSemana` | Puntos 2 a 6 |
| `curaduria/CuraduriaService.java` | `publicarYGuardar` en segundo plano (toda excepción termina en `ERROR`); `linkedinModo` en la lista; `reintentarFaq` (422/404/409) que arma la semana en segundo plano | Puntos 2, 3 y 6 |
| `controller/ErroresController.java` | Puerta `POST /api/v1/errores/faq/{semana}/reintentar`, con la segunda revisión del cliente | Punto 6 |
| `faqsemanal/FaqSemanalService.java` | `reintentarSemana(semana)`: reserva esa semana y la arma | Punto 6 |
| `LinkedinServiceTest.java`, `CuraduriaApiTest.java` | +5 y +8 pruebas (sección 4) | Sección 5 de la ficha |
| `docs/contratos/PANEL_JAVA_v1.md` | Nota "Agregado en T13", puerta 9, §2.1, §2.2, §2.4, §2.6, §2.8 (nueva), §3, §4 y §6 | Punto 7 |

**Parte B · El panel**

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `panel/estilo.py` (nuevo) | Las piezas de T12 (colores, `ESTILOS`, íconos, `DESTINOS`, `bloque`, `seccion`, `titulo`, `nota`, `tarjeta`, `encabezado_lista`, `hace`, `dia`, `corto`) más las reglas `bor-*` y `nav-*` | Punto 8 |
| `panel/logros.py` (nuevo) | La lógica sin dibujar: agrupar en tarjetas, contar como Java (UTF-16), contador de la guía de voz, `escapar_markdown`, el botón del post por modo, el enlace y el estado en LinkedIn | Puntos 10 y 12, y para probarla sola |
| `panel/paginas/borradores.py` | Rehecha según el prototipo | Punto 10 |
| `panel/paginas/dashboard.py` | Importa de `estilo.py` (mismos nombres internos); columna "En LinkedIn"; ya no inyecta los estilos (lo hace `app.py`) | Puntos 8 y 13 |
| `panel/paginas/errores.py` | Lista "FAQ semanal en ERROR" con **Reintentar** | Punto 14 |
| `panel/app.py` | Sin título arriba de cada página; barra lateral con "CommunityLab · Panel de curaduría", navegación propia con el número de tarjetas por revisar y la sesión; el inicio de sesión conserva su título | Punto 9 |
| `panel/cliente_java.py` | `listar_con_modo` y `reintentar_faq` (valida la semana antes de pedir) | Punto 15 |
| `panel/ui.py` | Sale `ESTADOS`, que ya no usa nadie | Limpieza |
| `panel/Dockerfile` | Copia `estilo.py` y `logros.py` | ⚠️ Sin esto la imagen no arrancaba: el Dockerfile copia los archivos uno por uno |
| `panel/tests/test_logros.py` (nuevo), `test_paginas.py` (rehecho), `test_cliente.py`, `test_dashboard.py` | Sección 4 | Sección 5 de la ficha |

**Parte C · La documentación**

| Archivo | Qué cambió |
|---|---|
| `docs/DECISIONES.md` | DEC-159, DEC-160 y DEC-161; DEC-151 → 🔁 |
| `docs/ARQUITECTURA.md` | §4.6 (curaduría por logro), §4.9 (modo y estado guardado; sale "Límites"), §5 (columnas, `V9`, siguiente `V10`), §10 (los módulos nuevos del panel) y §12 |
| `AGENTS.md` | §4: el siguiente es `V10__…`; fecha |
| `docs/OPERACION.md` | §5 (`V9`, `V10`), §9 (reintentar la FAQ desde el panel, sin SQL), §10 (uso diario de la página nueva) y §13 (dónde se ve si un post se publicó, el aviso de 3.000) |
| `docs/ESTADO.md` | OE3 y OE6; la mejora de la FAQ, hecha; la nueva 🟡 del tipo de logro; la sesión al recargar sigue |
| `docs/LINKEDIN_AUTOMATIZACION.md` | Las filas de `LinkedinPostResponse`, `LinkedinService`, `CuraduriaService`, la excepción nueva y el número de pruebas |
| `docs/historico/diseno/README.md` | §1, Borradores ✅; §2, Consentimiento, Acciones, Después de aprobar y Estado en LinkedIn. `borradores.dc.html` no se tocó |
| `docs/historico/tareas/T13-informe.md` | Este informe |

## 4. Pruebas

| Comando ejecutado | Resultado (🧪) |
|---|---|
| Java: el de [OPERACION.md §5](../../OPERACION.md) con `-e LINKEDIN_ACCESS_TOKEN=` (en Git Bash, con `$(pwd -W)`) | **256 pruebas, 0 fallas, 0 errores** (eran 243) |
| Panel: el de [TRASPASO_ORQUESTADOR.md §6](../TRASPASO_ORQUESTADOR.md) | **136 passed** (eran 63) |
| `docker build -t t13-panel-captura panel` | La imagen se construye y el panel arranca `healthy` con los módulos nuevos |

### 4.1 Java

```
BackendJavaApplicationTests 1 · ClasificacionTest 15 · CuraduriaApiTest 41 (+8) · DashboardApiTest 44
EnVivoApiTest 29 · FaqSemanalArranqueTest 1 · FaqSemanalTest 10 · GeneracionTest 14
LinkedinServiceTest 11 (+5) · LotesApiTest 19 · ModeloDatosTest 10 · NlpDataClientTest 11
OciClientTest 22 · SubidaOciTest 28                       → 256, Failures: 0, Errors: 0
```

| # de la ficha | Prueba |
|---|---|
| 1 | `laV9AgregaLasColumnasYSoloUnPostAprobadoTieneEstadoEnLinkedin` (un `CASO_EXITO` aprobado y un post pendiente: la base los rechaza) |
| 2 | `aprobarUnPostConLinkedinApagadoLoGuardaComoApagado` (responde en menos de 5 s; sondeo cada 50 ms con tope de 10 s) |
| 3 | `LinkedinServiceTest`: simulado, más de 3.000, vacío, un error cualquiera (el motivo no contiene "401", "Unauthorized" ni "token"), HTTP 401, tiempo agotado, ID demasiado largo, un emoji cuenta 2 |
| 4 | `elEstadoEnLinkedinSeGuardaUnaSolaVezYSoloEnUnPostAprobado` (filas con ids altos, para que ninguna tarea en segundo plano de otra prueba las toque) |
| 5 y 5b | `listarYVerTraenElLogroElMotivoYElEstadoEnLinkedin`; `elModoDeLinkedinNoMuestraElTokenNiElAutor` (modo `REAL` con propiedades de prueba, sin llamar a LinkedIn) y `elModoSaleDeLaConfiguracionSinLlamarALinkedin` |
| 6 y 7 | `reintentarUnaFaqEnErrorLaDevuelveALaColaYLaArmaEnSegundoPlano` (la IA simulada espera a que la prueba mire la base: así no depende de cuánto tarda) y `reintentarUnaFaqQueNoEstaEnError…` (409, 404, 422 con 4 formas, sin usuario) |
| 8 | `laPuertaDeReintentarLaFaqSoloLaAbreElPanel` (401, 403, `;x=1`, `%65`, y la segunda capa del controlador) |
| 9 | Las 243 de antes siguen pasando |

La primera corrida falló entera: el `CHECK` de largo de `linkedin_post_id` ya tomaba el nombre `borradores_linkedin_post_id_check`. Se renombró la otra restricción. 🧪 La migración había fallado dentro de su transacción: la base de prueba seguía en `V8` (`flyway_schema_history`), y la `V9` final se aplicó limpia.

### 4.2 Panel

| # de la ficha | Prueba |
|---|---|
| 1 | `test_el_post_y_el_caso_del_mismo_logro_son_una_tarjeta…`, `test_lo_aprobado_va_primero…`, `test_sin_mensaje_id…`, `test_la_cola_tiene_una_tarjeta_por_logro_y_cuenta_tarjetas`, `test_la_barra_lateral…` ("Borradores :gray-badge[3]") |
| 2 | `test_aprobar_el_post_y_despues_el_caso_cada_uno_con_su_tiempo` (post ≥ 1000 s, caso < 1000 s; la tarjeta sigue y después sale; el enlace abre el dashboard en Contenido) |
| 3 | `test_el_boton_del_post_dice_antes_de_aprobar…` (4 modos; en `REAL` y sin dato: sin confirmar no hay pedido, Cancelar tampoco, al confirmar sí) |
| 4 | `test_guardar_edicion_y_rechazar_tocan_solo_su_texto` |
| 5 | `test_una_edicion_no_se_pierde_al_cambiar_de_pestana_ni_de_tarjeta` |
| 6 | `test_los_caracteres_se_cuentan_como_java`, `test_el_contador…`, `test_el_contador_cuenta_como_java_y_un_post_muy_largo_no_se_aprueba` (1.500 🎉 = 3.000: se aprueba; uno más: apagado) |
| 7 | `test_un_nombre_con_markdown_o_html_se_ve_tal_cual` (`**x**`, `[x](…)`, `![x](…)`, `<b>x</b>`, `<script>…`: tal cual en la tarjeta y el título; escapado en la casilla y en el aviso de aprobado; nunca crudo en markdown ni en HTML) y `test_un_nombre_escapado_se_ve_tal_cual` |
| 8 | `test_un_post_aprobado_dice_que_paso_en_linkedin` (6 casos, uno con `postId` `javascript:…`: sin enlace) y `test_el_enlace_a_linkedin…` (10 casos) |
| 9 | `test_la_pagina_de_errores_reintenta_una_faq`, `test_errores_de_un_java_de_antes_de_t13…` |
| 10 | `test_contenido_dice_si_cada_post_se_publico_en_linkedin` y las del dashboard |
| 11 | Las 63 de antes: las de inicio de sesión, OCI, errores y el dashboard pasan. Las de Borradores se reescribieron para la página nueva, con lo que comprobaban (casilla, FAQ sin casilla, edición en la aprobación, 409, escapado, solo lectura, OCI) |

### 4.3 Capturas

Como en T12: una copia aparte del panel en una red de Docker propia (`t13-capturas`), **sin puertos publicados**, con un usuario de captura que solo existía ahí, y Chromium sin pantalla (Playwright 1.49.1) a 1440 px. Como el Java real todavía no tiene los campos nuevos, el panel hablaba con un **Java de mentira** (un servidor de Python con datos inventados como los del prototipo, que responde 409 a todo cambio). Una segunda copia usaba ese Java en modo `REAL`. **Nada tocó la base real, la IA ni LinkedIn.** Al terminar se borraron los contenedores, la red y las imágenes `t13-*`.

| Captura | Qué se vio (🧪) |
|---|---|
| Borradores, claro y oscuro (el tema cambiado **sin recargar**) | Encabezado, píldoras "Por revisar (4)", cola con 4 tarjetas (nombre, hace cuánto, motivo recortado, etiqueta) y la elegida con borde grueso; detalle con "Logro de …", canal y fecha, los dos recuadros, la casilla, las pestañas, "Dónde se publica", el texto, el contador, Copiar texto y los botones. Los colores cambian solos |
| Logro con un solo texto pendiente | El post aprobado se ve solo para leer, con "No publicado: la publicación en LinkedIn está apagada" |
| Filtro Aprobados | Abre la pestaña del post aprobado, con quién lo aprobó y su estado en LinkedIn |
| Modo `REAL`, al pulsar "Aprobar y publicar en LinkedIn" | El diálogo "¿Publicar en LinkedIn?" con **Publicar ahora** y **Cancelar** (no se pulsó ninguno) |
| Errores | La lista "FAQ semanal en ERROR" con la semana, los intentos, el motivo y Reintentar |
| Dashboard, antes (`main`) y después, claro y oscuro | Iguales, salvo el título del panel (ahora en la barra lateral) y la columna "En LinkedIn" |

Lo que se corrigió al mirarlas: el botón **Aprobar** apagado salía índigo con el texto casi invisible (el estilo de DEC-109 lo pintaba igual que uno encendido); en Aprobados se abría la pestaña pendiente en vez de la aprobada; y el ícono de "Dónde se publica" no se veía (ver sección 6).

## 5. Decisiones que se tomaron

Para validar con Harrison; si las valida, van como DEC-162 en adelante.

| Decisión | Alternativas descartadas | ¿Cambia el contrato, la arquitectura o D1 a D7? |
|---|---|---|
| **La casilla de consentimiento va arriba de las pestañas** (en el prototipo, abajo del texto) | Abajo de las pestañas, debajo de los botones (quedaría después de los botones que habilita) | No. Cambia el lugar que dibujó el prototipo: la ficha pide la casilla "arriba de los botones" y los botones "dentro de cada pestaña"; una sola casilla no puede estar dentro de las dos |
| **Las ediciones se guardan en `st.session_state["ediciones"]`** y se dibujan las dos pestañas | `persist_state="page"` de Streamlit 1.65: 🧪 en la prueba no conservó la edición al cambiar de tarjeta | No |
| **Toda la tarjeta de la cola es un botón**: un `st.button` transparente que la cubre (CSS fijo `bor-*`), con la etiqueta "Abrir: <nombre escapado>" | Un botón "Revisar" visible en cada tarjeta (se alejaba del prototipo) | No |
| **Navegación propia**: `st.navigation(position="hidden")` y tres `st.page_link`; el número va como `:gray-badge[n]` (un número, no un dato del alumno). El título de la barra lateral va en markdown con texto fijo, no en `st.html` | `st.navigation` normal: Streamlit la dibuja arriba de todo y el título no podía ir encima | No |
| **"Verlos en Listos para publicar" es un botón** que elige la pestaña Contenido y cambia de página (`st.switch_page`) | `st.page_link`: no puede elegir la pestaña del dashboard | No |
| **Java corre lo de segundo plano en hilos virtuales** (`Executors.newVirtualThreadPerTaskExecutor()`), también la publicación en LinkedIn, que antes usaba `CompletableFuture.runAsync` | El grupo común de Java: la FAQ espera a la IA hasta 150 s y podía frenar a LinkedIn | No (es interno de Java) |
| **`LinkedinPostResponse` cambia de campos** (`estado`, `idPost`, `motivo`) | Conservar `publicado`/`simulado`/`mensaje`: `mensaje` llevaba `e.getMessage()` | No: es interno de Java, no un contrato |
| **El botón principal apagado se ve gris** (una regla CSS en `estilo.ESTILOS`, solo para `:disabled`) | Dejarlo índigo (ilegible) o cambiar el índigo de DEC-109 (lo prohíbe la ficha) | No. El índigo encendido no cambió |
| **"Dónde se publica" usa `DESTINOS`** ("LinkedIn de CommunityLab", "Web y presentaciones a empresas"), los mismos textos de la columna del dashboard | Los textos del prototipo ("el LinkedIn de CommunityLab", "la web de CommunityLab y las presentaciones…"): habría dos listas | No |
| En **Aprobados** y **Rechazados** la tarjeta es el mismo logro: un texto que siga pendiente se puede revisar ahí también | Mostrar solo los textos de ese estado | No |
| La clave de las pestañas incluye el filtro y lo pendiente, para que se abra la pestaña que corresponde | — | No |

## 6. Dudas, riesgos y pendientes

1. ✅ **Prueba real** hecha (sección 7): la `V9` ya está en la base real y **no se edita** (el siguiente cambio de base es `V10`).
2. 🧪 **Los íconos SVG dentro de `st.html` no se ven** en Streamlit 1.65: tampoco el reloj de "El más antiguo espera…" ni los de "A quién ayudar hoy" del dashboard de T12, ni antes ni después de T13. No se tocó el dashboard (fuera de alcance); Borradores usa un ícono de Material (`:material/location_on:`) en un markdown de texto fijo. 🔎 Probablemente el sanitizador de `st.html` quita el `<svg>`. Para el orquestador: decidir si se cambian los íconos del dashboard.
3. **El índigo de DEC-109** (`ui.ESTILOS`) choca con el prototipo, que usa botones oscuros y píldoras rellenas. Propuesta: dejarlo como está hasta después de la demo; si se cambia, también se ve en el inicio de sesión.
4. Una edición sin guardar se pierde al **recargar la página** o cerrar la sesión (la sesión no sobrevive a una recarga: mejora pendiente en ESTADO.md). Las capturas tuvieron que navegar con la barra lateral por eso.
5. En las pruebas del dashboard, la primera corrida de la página Borradores deja un `AttributeError` en el registro (el Java simulado del dashboard no tiene `listar_con_modo`); después cambia de página y las pruebas comprueban el dashboard. No afecta el resultado; no se tocó ese simulador para no cambiar lo que comprueban.
6. La imagen de Playwright (`mcr.microsoft.com/playwright/python:v1.49.1-noble`, unos 2 GB) quedó en Docker. Si no se usa más: `docker rmi mcr.microsoft.com/playwright/python:v1.49.1-noble`.
7. 📘 El formato del enlace: la documentación de LinkedIn (Posts API) dice que `x-restli-id` devuelve `urn:li:share:…` o `urn:li:ugcPost:…`, y que un post se ve en `https://www.linkedin.com/feed/update/urn:li:ugcPost:<id>/`. 🔎 Para `urn:li:share:` se usa el mismo patrón; conviene confirmarlo en la demo con LinkedIn encendido.

## 7. Comandos que ejecutó Harrison

Desde la raíz del repositorio, el 2026-10-15:

| # | Comando | Resultado |
|---|---|---|
| 1 | `git add backend-java docs/contratos/PANEL_JAVA_v1.md` y `git commit -m "feat(java): …"` | `d1c3790`, 13 archivos |
| 2 | `git add panel` y `git commit -m "feat(panel): …"` | `5ecc982`, 13 archivos |
| 3 | `git add AGENTS.md docs` y `git commit -m "docs: …"` | `77494a8`, 8 archivos |
| 4 | `git log --oneline -3` después de cada commit | Cada commit quedó en su lugar, sin mezclarse |
| 5 | `git push` | `2e8e088..77494a8  tarea/T13-borradores -> tarea/T13-borradores` |

**Prueba real** (sección 5 de la ficha), corrida por Harrison el 2026-10-15. 🧪 Los 9 pasos dieron lo esperado:

| Paso | Qué se hizo | Resultado |
|---|---|---|
| 1 | `docker compose exec api-java printenv LINKEDIN_HABILITADA` | `false` |
| 2 y 3 | `docker compose up -d --build api-java panel` y `docker compose ps` | Java aplicó la `V9`; `api-java` y `panel` en `(healthy)` |
| 4 | Borradores, en claro y en oscuro | 5 tarjetas por revisar: los logros 183 y 254 (solo el caso de éxito), 256 y 257 (post y caso) y la FAQ |
| 5 | Editar el post, pasar al caso y volver | La edición siguió ahí (no se guardó) |
| 6 | El botón del post antes de aprobar | "Aprobar post", con "La publicación en LinkedIn está apagada…" |
| 7 | Aprobar el post y después el caso de un logro real | Aprobados; el post dice "No publicado: la publicación en LinkedIn está apagada" |
| 8 | Dashboard → Contenido → Listos para publicar | "En LinkedIn": "No: apagado" en ese post |
| 9 | Errores | "FAQ semanal en ERROR" vacía |
