# Informe de la tarea T09 — OCI: guardar los borradores generados y los aprobados en Oracle Cloud

| Dato | Valor |
|---|---|
| Fecha | 2026-10-05 |
| Modelo de Claude usado | Sonnet 5.5 (`claude-sonnet-5-5`) |
| Rama | `tarea/T09-oci` |
| Commits | Los da Harrison al cerrar (ver la sección 7): `feat(backend): subida de borradores a OCI en segundo plano y migracion V8 (T09 parte A)`, `feat(panel): estado de OCI en el detalle del borrador (T09 parte B)` y `docs: informe de T09 (OCI)` |

## 1. Resumen

Una tarea de fondo de Java guarda cada borrador (post, caso de éxito o FAQ) como un JSON armado con Jackson: en `generados/` al crearse y en `aprobados/` solo si está aprobado (con su texto final). Si OCI falla, generar y aprobar siguen funcionando y la subida se reintenta; al quinto fallo queda en `ERROR`. Pasan **219 pruebas de Java** (169 anteriores + 50 nuevas), con el servidor de OCI simulado y PostgreSQL real; el panel suma el estado de OCI en el detalle (parte opcional). En la prueba real Java subió **27 archivos (16 a `generados/` y 11 a `aprobados/`), todos `SUBIDO` y con 0 errores**. **Pendiente (decisión de Harrison):** que el compañero Gabriel confirme lo que hay en el bucket, y repetir la comprobación con una PAR propia, creada por Harrison en su cuenta de OCI (sección 4.4).

## 2. Criterios de terminado

| Criterio | Estado | Evidencia |
|---|---|---|
| Cada borrador está en `generados/`, y cada aprobado también en `aprobados/`; los rechazados no | ⚠️ parcial | 🧪 Con OCI simulado: `unBorradorNuevoSeSubeAGeneradosConPutJsonValidoYElNombreEsperado`, `unBorradorAprobadoSeSubeTambienAAprobadosConElTextoFinal`, `unRechazadoOUnPendienteNoVanAAprobados`. 🧪 En la prueba real, la base dice que las 27 subidas quedaron `SUBIDO` (el rechazado solo está en `generados/`). **Lo que hay dentro del bucket lo confirma Gabriel y no lo vio este chat** (sección 4.4) |
| Los JSON se arman con Jackson, son válidos y no tienen datos de Discord del alumno | ✅ | 🧪 `unTextoConComillasSaltosDeLineaEmojisYBarrasDaUnJsonValido` y `elJsonNoTieneNombreDeUsuarioIdsDeDiscordNiElMensajeOriginal` (los campos del archivo son exactamente los 13 de DEC-128) |
| Un fallo de OCI no frena la generación ni la aprobación, y se reintenta hasta el máximo | ✅ | 🧪 `siOciRespondeError500SumaUnIntentoYSigueHastaElMaximo`, `siOciNoRespondeTambienSumaUnIntento`, `siOciEstaCaidoGenerarYAprobarSiguenFuncionando` |
| La URL PAR no aparece en ningún registro ni en el informe | ✅ | 🧪 `elRegistroNiLaBaseTienenLaUrlParEnNingunCaso` y `OciClientTest` (los errores dicen solo la clase o el código HTTP, sin causa encadenada). En la salida completa de Maven: 0 menciones de la PAR de prueba. Este informe no la lleva |
| Las pruebas pasan y la prueba real muestra los archivos en el bucket | ⚠️ parcial | 🧪 219 de 219 pasan. 🧪 La prueba real corrió y Java registró 27 `SUBIDO`. **Pendiente:** la confirmación de Gabriel y la repetición con una PAR propia (sección 4.4) |
| El informe está completo, y no se tocó nada fuera del alcance | ✅ | No se tocaron V1 a V7, el clasificador, la generación, la FAQ, la aprobación, el contrato v1, `JAVA_IA_v1`, el bot, la ingesta ni `agents/orquestador/storage/`. Lo que sí cambió fuera de la carpeta nueva `oci/` está en la sección 3 |

## 3. Archivos cambiados

Rutas Java relativas a `backend-java/src/main/java/com/insightedulab/backend_java/`.

### Parte A · Java

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `backend-java/src/main/resources/db/migration/V8__subidas_oci.sql` | Nuevo: tabla `subidas_oci` (una fila por borrador y carpeta, `UNIQUE (borrador_id, carpeta)`), con `estado` (`PENDIENTE`, `SUBIDO` o `ERROR`), `ruta`, `intentos`, `ultimo_error`, `reservada_hasta` y `subido_en`. `CHECK`: solo lo `SUBIDO` tiene ruta y fecha. Índice parcial de los pendientes. `COMMENT` en `estado_oci` y `ruta_oci` de V1: quedan sin uso | §3.1 de la ficha |
| `oci/OciProperties.java` | Nuevo: propiedades `oci.*`. La PAR vive en un `Par` cuyo `toString()` la oculta. Dice si la PAR está ausente, mal formada (debe empezar con `https://objectstorage.` y terminar en `/o/`) o lista | §3.4 |
| `oci/OciClient.java`, `oci/OciException.java`, `oci/OciConfig.java` | Nuevos: `PUT <PAR><objeto>` con `Content-Type: application/json`, 5 s para conectar y 30 s para leer. Solo un `2xx` es éxito. Los errores dicen el código HTTP o la clase del error, nunca la URL ni la causa original | §3.4 |
| `oci/ArchivoOci.java` | Nuevo: el objeto que Jackson convierte en el JSON (DEC-128), con sus 13 campos | §3.3 |
| `oci/SubidaOciRepository.java` | Nuevo: encola lo que falta (`INSERT … ON CONFLICT DO NOTHING`), reserva con `FOR UPDATE SKIP LOCKED`, lee el borrador y anota el resultado con guarda (`AND estado = 'PENDIENTE'`). Cada método es una sola sentencia: nada queda abierto mientras se espera a OCI | §3.2 |
| `oci/SubidaOciService.java` | Nuevo: encola, reserva una tanda, arma el JSON, sube y anota. Sin PAR (o mal formada) no hace nada y lo avisa una sola vez. Guarda de F11: una subida a `aprobados/` de un borrador que no está `APROBADO` no se envía | §3.2 |
| `oci/SubidaOciProgramada.java` | Nuevo: `@Scheduled` cada 30 s, con su propio `@EnableScheduling`. Valida la PAR al arrancar (sin mostrarla). Registro solo con números | §3.2 y §3.4 |
| `curaduria/VistasPanel.java`, `curaduria/CuraduriaRepository.java` | `DetalleBorrador` suma `oci` (`generados` y `aprobados`: solo el estado). Dos subconsultas en el `SELECT` del detalle | §3.5 (opcional) |
| `model/Borrador.java` | Solo el comentario de `estadoOci` y `rutaOci`: sin uso desde la V8 | §3.1 |
| `application.properties` | `oci.*` (intervalo, tanda, intentos, reserva, espera, zona), `OCI_HABILITADA`; el pool de tareas pasa de 3 a 4 hilos (hay una tarea más); y `logging.level.org.springframework.web.client=INFO` fijo | §3.2, §3.4 |
| `pom.xml` | El plugin de pruebas (`surefire`) apaga la tarea de OCI en **todas** las pruebas con una propiedad del sistema | Ver la decisión 6 |
| `test/…/OciClientTest.java` | Nuevo: 22 pruebas del cliente y de la forma de la PAR | §5 |
| `test/…/SubidaOciTest.java` | Nuevo: 28 pruebas contra PostgreSQL real y OCI simulado. Mismas propiedades, `@MockitoBean` y `@AutoConfigureMockMvc` que `CuraduriaApiTest`: reutiliza su contexto y su grupo de conexiones | §5 |
| `compose.yml`, `.env.example` | `OCI_HABILITADA` para `api-java`; el texto de `OCI_PAR_URL` explica que es una credencial, de solo escritura y con vencimiento | §3.6 |
| `docs/OPERACION.md` | Variables, `V8`, y **§12 nueva**: qué se guarda y dónde, qué trae el archivo, cómo crear la PAR, dónde pegarla, cómo comprobar en la consola de Oracle, consultas de solo lectura, `ERROR` y cómo reintentarlos, y cómo apagarla | §3.6 |

### Parte B · Panel (opcional)

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `panel/ui.py`, `panel/paginas/borradores.py` | `lineas_oci()` y el bloque **Guardado en OCI** en el detalle: una línea por carpeta, solo el estado. Usa `st.text`, no `st.caption`, para no cambiar el orden de los avisos que ya prueba otra prueba | §3.5 |
| `panel/tests/test_paginas.py` | +7 pruebas (3 de la página y 4 de `lineas_oci`); el borrador de prueba lleva `oci` | §3.5 |
| `docs/contratos/PANEL_JAVA_v1.md` | Cabecera y §2.2: el campo `oci`. **Solo agrega** | §3.5 |

## 4. Pruebas

| Comando ejecutado | Resultado (🧪) |
|---|---|
| Java, en Docker contra `insightedu_test` (`docs/OPERACION.md` §5), con el código final | **219 pruebas, 0 fallas, 0 errores, `BUILD SUCCESS`**: las 169 de antes + 22 de `OciClientTest` + 28 de `SubidaOciTest` |
| `python -m pytest panel/tests -q` | **51 passed** (las 44 de antes + 7 nuevas) |
| `python -m pytest agents/orquestador/tests -q` | **79 passed** (sin cambios) |
| `python -m pytest agents/bot_discord/tests -q` | **22 passed** (sin cambios) |
| `python -m pytest -q` (desde `ingestion/discord`) | **36 passed** (sin cambios) |
| `docker compose config --quiet` | Sin errores |

Cómo se corrió Java: el contenedor de pruebas recibió una PAR **falsa** (`https://objectstorage.invalid.example/…`) por encima de la del `.env`, para que ni un error mío pudiera subir nada al bucket real. No se tocó el stack que estaba encendido (`api-java` sigue con el código anterior hasta que Harrison lo reconstruya).

### 4.1 Las pruebas de la ficha (sección 5) y dónde están

| # | Caso | Pruebas |
|---|---|---|
| 1 | Un borrador nuevo se sube a `generados/` | `unBorradorNuevoSeSubeAGeneradosConPutJsonValidoYElNombreEsperado` (PUT, `application/json`, JSON válido, nombre con la fecha en hora de Bogotá), `correrLaTareaOtraVezNoSubeDosVecesLoMismo`, `losBorradoresQueYaExistenSeSubenLaPrimeraVezQueCorreLaTarea` (DEC-131) |
| 2 | Un aprobado se sube también a `aprobados/`, con `texto_final` | `unBorradorAprobadoSeSubeTambienAAprobadosConElTextoFinal`, `siSeApruebaAntesDeLaPrimeraSubidaSubenLasDosCarpetasConElEstadoDeAhora`, `laFaqLlevaLaSemanaYElResumenYNoNecesitaConsentimiento` |
| 3 | Un rechazado o pendiente **no** va a `aprobados/` (F11) | `unRechazadoOUnPendienteNoVanAAprobados`, `unPendienteEnAprobadosPorUnErrorNoSeSubeYQuedaEnError` (la guarda), `lasRespuestasDelBotNoSeSuben` |
| 4 | Comillas, saltos de línea, emojis y `\` | `unTextoConComillasSaltosDeLineaEmojisYBarrasDaUnJsonValido` |
| 5 | OCI responde 500 o no responde | `siOciRespondeError500SumaUnIntentoYSigueHastaElMaximo`, `siOciNoRespondeTambienSumaUnIntento`, `cadaSubidaEsIndependienteYLaDeVueltaDeUnERROREsSubirla` (incluye el `UPDATE` de `OPERACION.md` §12), `siOciEstaCaidoGenerarYAprobarSiguenFuncionando`, `OciClientTest` (400, 401, 403, 404, 409, 500, 503, un 3xx, el tiempo agotado y la conexión rechazada) |
| 6 | Dos ejecuciones a la vez | `dosReservasAlMismoTiempoNoTomanLasMismasSubidas`, `dosEjecucionesCompletasALaVezNoSubenDosVecesLoMismo` (8 borradores, dos hilos, 150 ms por subida para que se superpongan: 8 archivos distintos, ninguno repetido), `unaSubidaReservadaPorOtraEjecucionNoSeTomaHastaQueVence`, `laGuardaNoPisaUnaSubidaQueOtraEjecucionYaAnoto` |
| 7 | Sin PAR | `sinParNoLlamaANadaAvisaUnaSolaVezYNoMarcaErrores`, y `unaParConOtraFormaTampocoSubeNadaYNoSeMuestraEnElRegistro` (4 formas inválidas) |
| 8 | El JSON no tiene datos de Discord | `elJsonNoTieneNombreDeUsuarioIdsDeDiscordNiElMensajeOriginal` (los campos son exactamente los de DEC-128; el archivo no contiene el usuario, los ids de mensaje, autor, canal y servidor, el mensaje original ni el nombre completo) |
| 9 | El registro no tiene la PAR | `elRegistroNiLaBaseTienenLaUrlParEnNingunCaso` (un éxito, un 500 y un tiempo agotado hasta llegar a `ERROR`; el registro y la columna `ultimo_error` sin la PAR), `OciClientTest.laParNoSeEscribeNiSiSeImprimenLasPropiedades` y `siOciNoRespondeElErrorDiceLaClaseYNuncaLaPar` |
| 10 | Las 169 pruebas anteriores | Pasan (219 en total) |
| Extra | La tarea no corre sola en las pruebas | `laTareaProgramadaEstaApagadaEnLasPruebas` |
| Extra | Panel y V8 | `elDetalleDelPanelDiceElEstadoDeLasSubidasSinLaRutaNiLaPar`, `laV8NoDejaRepetirNiAnotarMal` |

### 4.2 Un fallo que apareció y se corrigió

La primera corrida de `SubidaOciTest` dio 49 de 50: Jackson, al escribir **bytes**, convierte cada emoji en `🎉`. Sigue siendo JSON válido, pero quien abra el archivo en la consola de Oracle vería código en vez del emoji. Ahora el JSON se arma primero como texto y luego se codifica a UTF-8 (`SubidaOciService`); la prueba comprueba que el archivo lleva los emojis tal cual.

### 4.3 Comprobaciones previas

- 🧪 El estado de Docker al empezar: el stack estaba encendido con el código anterior. No se reconstruyó.
- 🧪 La base principal está en la migración 7 y tiene **13 borradores** (consulta de solo lectura): 8 `PENDIENTE`, 4 `APROBADO` y 1 `RECHAZADO`. La primera vez que corra la tarea con una PAR debería subir **13 archivos a `generados/` y 4 a `aprobados/`** (17 en total, en unos 2 minutos con tandas de 10 cada 30 s).

### 4.4 Prueba real contra el bucket de Oracle

**⚠️ Parcial.** La prueba real corrió el 2026-10-05 y Java funcionó de punta a punta. Lo que **no** vio este chat es el contenido del bucket en la consola de Oracle. Harrison indicó que **el compañero Gabriel se lo confirmó**, y que la comprobación con una PAR propia, creada por él en su cuenta de OCI, se hará después.

**Lo que este chat observó (🧪, solo lectura):**

| Qué | Resultado |
|---|---|
| Migración | `Migrating schema "public" to version "8 - subidas oci"` → `now at version v8` (salida pegada por Harrison) |
| Arranque | `OCI: hay una PAR con la forma esperada; la subida de borradores está activa` (sin la PAR) |
| Primera vez (borradores que ya existían) | `Subida a OCI: tomadas 10, subidas 10, reintento 0, ERROR 0` y luego `tomadas 7, subidas 7, reintento 0, ERROR 0`: los **17** esperados (13 a `generados/` y 4 a `aprobados/`) |
| Después | `tomadas 2, subidas 2` y `tomadas 4, subidas 4`, con `ERROR 0` |
| Estado final en la base | **27 subidas, todas `SUBIDO`, con 1 intento cada una:** 16 en `generados/` y 11 en `aprobados/`. Ninguna `PENDIENTE` ni `ERROR` |
| Borradores nuevos | Los #14, #15 y #16 (creados durante el día) se subieron solos a `generados/`. Las 7 aprobaciones hechas en el panel (#3, #5, #6, #7, #8, #9 y #10) quedaron en `aprobados/` |
| Rechazados | El rechazado (#4) solo está en `generados/` |
| El registro | Solo nombres de archivo, números y códigos. Ninguna línea lleva la PAR |

**Pendiente (a cargo de Harrison, acordado en el chat):**

- [ ] **Confirmación del compañero Gabriel** de lo que hay en el bucket: las carpetas `generados/` y `aprobados/`, los nombres de los archivos y que un archivo abierto no tenga datos de Discord del alumno.
- [ ] **Repetir la comprobación con una PAR propia**, creada por Harrison en su OCI (pasos en `OPERACION.md` §12). Al cambiar la PAR, hay que volver a poner las subidas en `PENDIENTE` (la consulta "Cambiar de PAR o de bucket" de `OPERACION.md` §12).
- [ ] (Opcional, resuelve el riesgo 1) Con el bucket a la vista, volver a subir un solo archivo ya `SUBIDO` con el `UPDATE` de `OPERACION.md` §12 y ver si termina `SUBIDO` otra vez.
- [ ] (Opcional) Ver en el panel el bloque "Guardado en OCI" de un borrador aprobado. Este chat no lo vio; está cubierto por las pruebas de la página (🧪 `test_un_aprobado_muestra_las_dos_carpetas`).

## 5. Decisiones que se tomaron

| # | Decisión | Alternativas descartadas | ¿Cambia el contrato, la arquitectura o D1 a D7? |
|---|---|---|---|
| 1 | **Una tabla `subidas_oci`**, una fila por borrador y carpeta, en vez de columnas nuevas en `borradores`. Cada subida lleva su estado, intentos, reserva y fecha, y el `UNIQUE (borrador_id, carpeta)` impide encolar dos veces lo mismo. `estado_oci` y `ruta_oci` de V1 quedan sin uso (con un `COMMENT`); no se borran porque `Borrador.java` las mapea | Diez columnas nuevas en `borradores` (cinco por carpeta) | No |
| 2 | **La tarea encola lo que falta** (un `INSERT … ON CONFLICT DO NOTHING` por carpeta, en cada vuelta), en vez de crear la fila desde la generación, la FAQ o la aprobación. Así T06, T06b y T07 no se tocaron, los 13 borradores que ya existen se suben solos (DEC-131), y aprobar nunca depende de OCI | Insertar la fila dentro de las transacciones de generar y aprobar (acopla tres módulos y obliga a rellenar los existentes en la migración) | No |
| 3 | **El archivo es una foto del borrador al subirlo**, con el mismo formato en las dos carpetas. Si OCI estuvo caído y el borrador ya se aprobó, el de `generados/` ya dice `APROBADO` | Un formato aparte para `generados/` con solo lo de la IA (inventaría un estado `PENDIENTE` que ya no es cierto) | No |
| 4 | **El archivo lleva exactamente los 13 campos de DEC-128.** No lleva el `id` del mensaje de Discord, el motivo del rechazo (puede ser texto libre de Marketing) ni los tokens | Incluir el motivo del rechazo y los tokens | No (DEC-128) |
| 5 | **Reintentos con espera creciente:** tras el fallo `n`, la subida espera `60 × n` segundos; al quinto fallo, `ERROR` (unos 10 minutos de tolerancia). Reutiliza `reservada_hasta` como "no antes de" | Reintentar en la vuelta siguiente (30 s): una caída corta de OCI gastaría todos los intentos en dos minutos | No |
| 6 | **La tarea se apaga en todas las pruebas desde el `pom.xml`** (propiedad del sistema `oci.habilitada=false`). Las pruebas se corren con el `.env` completo, que tendrá una PAR real: sin esto, una prueba con borradores falsos podía subir al bucket de verdad a los 30 s | Agregar la propiedad a cada clase de prueba, como en T06 (se olvidaría en la siguiente) | No |
| 7 | **Sin PAR o con una PAR mal formada, Java arranca igual** y la tarea no hace nada: avisa una sola vez (en `ERROR` si tiene forma inválida) y no toca ninguna fila. La validación de la forma se hace al arrancar, sin mostrar la PAR | Que Java no arranque (una PAR mal pegada tumbaría la API, el bot y el panel por un problema de OCI) | No |
| 8 | **Solo un `2xx` cuenta como subido.** Cualquier otra respuesta, también un `401`, `403` o `404`, suma un intento de ese borrador; no se distingue "la PAR no sirve" de "OCI falló" | Detener toda la tanda ante un `401` o `403` (más código, y el resultado final es el mismo) | No |
| 9 | **Fecha del nombre:** la de `creado_en` en `generados/` y la de `aprobado_en` en `aprobados/`, en hora de Bogotá (`oci.zona`). Es estable: si se repite la subida, el nombre es el mismo | Fecha del momento de subir (cambiaría en cada reintento) | No |
| 10 | **Las respuestas del bot (`RESPUESTA_BOT`) no se suben**: no se aprueban (D3, DEC-66) y la ficha habla de post, caso de éxito y FAQ | Subirlas a `generados/` | No |
| 11 | **Parte opcional del panel hecha**, aditiva: `oci` con solo los dos estados en el detalle, y un bloque "Guardado en OCI". Nunca la ruta ni la PAR | Dejarla fuera | No (solo agrega a `PANEL_JAVA_v1`) |
| 12 | **El pool de tareas pasa de 3 a 4 hilos** (`spring.task.scheduling.pool.size`): es la cuarta tarea de fondo, y la FAQ puede ocupar un hilo 2 minutos | Dejar 3 | No |
| 13 | **El registro del cliente HTTP de Spring queda fijo en `INFO`**: a `DEBUG` escribiría la URL de cada pedido, o sea la PAR | Confiar en el nivel por defecto | No |
| 14 | **El JSON se arma como texto y luego se pasa a UTF-8** (ver 4.2), y se envía con la sangría de Jackson para que sea legible en la consola de Oracle | Escribir los bytes directo (emojis como `\uD83C…`) | No |

## 6. Dudas, riesgos y pendientes

| # | Qué | Para quién |
|---|---|---|
| 1 | 🔎 **Sobrescribir:** la documentación de Oracle no dice si un segundo `PUT` al mismo nombre reemplaza el objeto con una PAR de solo escritura. Afecta a un caso raro: OCI recibe el archivo pero la respuesta se pierde, y el reintento vuelve a enviar el mismo nombre. Si OCI lo rechazara, ese borrador terminaría en `ERROR` aunque el archivo ya esté. **Sigue sin comprobarse** (punto opcional de 4.4) | Harrison, con la PAR propia |
| 2 | ⚠️ **DEC-129 sin verificar.** Harrison dejó para después la comprobación con **una PAR propia, creada en su OCI**. Este chat no sabe quién creó la PAR que se usó en la prueba, ni sus permisos ni su vencimiento. Mientras no se repita con la PAR de DEC-129 (solo escritura, con vencimiento después de la entrega, creada por Harrison), la prueba real no cumple esa decisión. Al cambiarla: `OPERACION.md` §12, "Cambiar de PAR o de bucket" | Harrison / chat principal |
| 3 | Lo que se sube viene de un texto que escribió la IA: el `motivoIa` puede mencionar al alumno por su primer nombre o citar su mensaje (riesgo 6 de T06). Va al bucket por DEC-128. Conviene mirarlo al abrir un archivo en la prueba real | Harrison / chat principal |
| 4 | Si la PAR vence o se revoca (la ficha propone el `2026-11-30`), todas las subidas pasarán a `ERROR` en unos 10 minutos. No se pierde nada: `OPERACION.md` §12 explica cómo crear otra PAR y reintentarlas con un `UPDATE` | Harrison, antes de la entrega del 2026-10-26 |
| 5 | Lo ya subido a `generados/` no se actualiza (la PAR es de solo escritura y está fuera de alcance). Si un borrador se edita después, el de `aprobados/` tiene la versión final | — |
| 6 | **Falta la confirmación de Gabriel** sobre lo que hay en el bucket (ver 4.4). Hasta entonces, "los archivos están en el bucket" se apoya en el estado `SUBIDO` que guarda Java (Oracle respondió con un `2xx`) y en la palabra de Harrison, no en algo que este chat haya visto | Harrison |
| 7 | `CLAUDE.md` §3 todavía no menciona la subida a OCI ni la carpeta `backend-java/.../oci/` | Chat principal |
| 8 | 🔎 Se recomienda registrar en `DECISIONES.md` las decisiones 1, 2, 3, 5, 6 y 7 de la sección 5 | Chat principal |
| 9 | `laTareaProgramadaEstaApagadaEnLasPruebas` depende de que se corra con Maven (como indica `OPERACION.md` §5). Desde un IDE, sin la configuración del `pom.xml`, fallaría. En esta máquina no hay JDK, así que no aplica | — |
| 10 | `api-java` ya corre el código de T09 y la base principal está en la `V8`: de aquí en adelante, cada borrador nuevo y cada aprobación se suben solos. Si se vuelve a levantar sin una PAR válida, no se sube nada y queda el aviso en el registro (los borradores se acumulan y se suben cuando haya una) | — |

## 7. Comandos que ejecutó Harrison

Desde la raíz, en PowerShell:

1. Dejó una PAR en `OCI_PAR_URL=` del `.env` (no se pegó en el chat).
2. `docker compose up -d --build api-java` (la imagen tardó unos 187 s; Flyway aplicó la `V8`).
3. `docker compose logs api-java` y `docker compose ps` (api-java en `healthy`).
4. Aprobó borradores en el panel (7, según la base).
5. Los commits y el `git push` (sección de cierre del chat).

Lo que corrió el chat de tarea (solo lectura, o contenedores aparte): las pruebas de Java en Docker contra `insightedu_test` con una PAR falsa, las de Python, `docker compose config --quiet`, consultas `SELECT` a la base y un `UPDATE` dentro de una transacción deshecha (`ROLLBACK`) para probar la consulta de "Cambiar de PAR o de bucket".
