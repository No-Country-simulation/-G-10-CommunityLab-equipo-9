# Informe de la tarea T08 — Dashboard

| Dato | Valor |
|---|---|
| Fecha | 2026-10-04 |
| Modelo de Claude usado | Opus 5.5 |
| Rama | `tarea/T08-dashboard` |
| Commits | Pendientes: uno para la Parte A (Java) y otro para la Parte B (panel). Los ejecuta Harrison (§7) |

## 1. Resumen

Java tiene 6 puertas de solo lectura bajo `/api/v1/dashboard/` (totales, sentimiento, temas, deserción, frustración y dudas sin responder), que solo abre la clave `panel`. El panel tiene la página **Dashboard**, con sus controles, dos gráficos de Streamlit y tres listas de alertas.
Las pruebas automáticas pasan (Java 169 y panel 44), y la prueba real con los datos de la base muestra el dashboard completo, con los números que da la base (§4.3).

## 2. Criterios de terminado

| Criterio | Estado | Evidencia |
|---|---|---|
| La página "Dashboard" muestra los 5 indicadores y los totales, con los controles de la sección 3 | ✅ | `panel/paginas/dashboard.py`. Prueba real §4.3. `test_dibuja_los_indicadores_…` y `test_los_controles_envian_sus_valores` |
| Las cuentas siguen las reglas: solo `OK` y personas, frustración según DEC-121 y dudas atendidas según DEC-123 | ✅ | `DashboardApiTest`, casos 1 a 5 (§4.1) |
| Las puertas nuevas solo aceptan la clave `panel` y están en `PANEL_JAVA_v1.md` | ✅ | Caso 6. [PANEL_JAVA_v1.md §7](../contratos/PANEL_JAVA_v1.md#7-dashboard-t08) (solo agrega) |
| Las pruebas de Java y de Python pasan, y la prueba real muestra los indicadores con los datos reales | ✅ | §4 |
| El informe está completo y no se tocó nada fuera del alcance | ✅ | No se tocó nada fuera del alcance (§6) |

## 3. Archivos cambiados

### Parte A · Java

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `db/migration/V7__dashboard.sql` (nuevo) | Índice parcial en `mensajes.responde_a` | "¿Alguien le contestó a esta duda?" se busca por cada duda; antes no había índice |
| `dashboard/DashboardRepository.java` (nuevo) | Las 6 consultas SQL de solo lectura | Ficha §3.1 |
| `dashboard/DashboardService.java` (nuevo) | El período (por defecto, los últimos 30 días, hasta 366), los rangos (`dias` de 1 a 365, `horas` de 0 a 2160) y la serie completa de días o semanas (también las vacías). Zona `dashboard.zona` (Bogotá) | Ficha §3.1 y §3.2 |
| `dashboard/VistasDashboard.java` (nuevo) | Las formas de las respuestas | Contrato |
| `controller/DashboardController.java` (nuevo) | Las 6 puertas `GET`. Cada método exige el cliente `panel` (segunda capa) | DEC-70 y DEC-122 |
| `seguridad/ApiKeyFilter.java` | `/api/v1/dashboard` en `CLIENTE_POR_PREFIJO` | Ficha §3.1 |
| `application.properties` | `dashboard.zona=${DASHBOARD_ZONA:America/Bogota}` y el comentario de las claves | — |
| `test/.../DashboardApiTest.java` (nuevo) | 26 pruebas | Ficha §5 |
| `docs/contratos/PANEL_JAVA_v1.md` | Una nota en la cabecera y la **§7 Dashboard**. Lo anterior no cambió | DEC-122 |

### Parte B · Panel y documentación

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `panel/paginas/dashboard.py` (nuevo) | La página: controles (período, día o semana, excluir «otro», umbrales), resumen con `st.metric`, gráficos `st.bar_chart` (sentimiento apilado de verde a rojo; temas, este período contra el anterior), deserción y frustración en `st.dataframe`, y dudas con `ui.mostrar_texto`. Cada indicador se pide aparte: si uno falla, aparece un aviso solo en ese recuadro | Ficha §3.5 y §3.6 |
| `panel/app.py` | La página **Dashboard** en el menú, entre Borradores y Errores | DEC-114 |
| `panel/cliente_java.py` | 6 métodos `dashboard_*`: fechas ISO, `excluirOtro` como `true`/`false` y sin `X-Usuario` | Contrato §7 |
| `panel/tests/test_dashboard.py` (nuevo) y `test_cliente.py` | 6 pruebas de la página y 1 del cliente | Ficha §5 |
| `docs/OPERACION.md` | Sección 11 (Dashboard). V1 a V7, y la siguiente es V8 | — |

## 4. Pruebas

| Comando ejecutado | Resultado (🧪) |
|---|---|
| `docker run … maven:3.9-eclipse-temurin-21 mvn test` (contra `insightedu_test`) | **169 pruebas, 0 fallos y 0 errores** (143 de antes y 26 de `DashboardApiTest`). La primera corrida tuvo 10 errores en `ModeloDatosTest`, por `FATAL: sorry, too many clients already` (§5, decisión 6); se corrigió y se volvió a correr todo |
| `python -m pytest panel/tests -q` | **44 passed** (37 de antes y 7 nuevas) |
| `python -m pytest agents/orquestador/tests -q` | 79 passed |
| `python -m pytest agents/bot_discord/tests -q` | 22 passed, 1 warning (ya estaba) |
| `python -m pytest -q` (desde `ingestion/discord`) | 36 passed |

### 4.1 Java: los casos de la ficha

| # | Caso | Prueba(s) en `DashboardApiTest` |
|---|---|---|
| 1 | Sentimiento por día y por semana, sin contar `PENDIENTE`, `ERROR`, bots ni mensajes sin sentimiento | `sentimientoPorDiaCuentaSoloOkDePersonasConSentimiento` (también: un mensaje de las 22:00 en Bogotá cuenta en ese día, aunque en UTC sea el siguiente, y los días vacíos salen en 0); `sentimientoPorSemanaEmpiezaElLunesYPuedeExcluirElTemaOtro` |
| 2 | Temas, con y sin `otro`, contra el período anterior | `temasComparanConElPeriodoAnteriorDeIgualLargo` |
| 3 | Deserción con 14 y con 3 días | `desercionCon14YCon3Dias` (mentores y bots no salen; cuenta los mensajes sin clasificar) |
| 4 | Frustración: un `MUY_NEGATIVO`, 2 negativos de los últimos 3, y 1 de 3 | `frustracionUnMuyNegativoODosNegativosDeLosUltimosTres`: alerta, alerta y sin alerta; un mentor y un mensaje `PENDIENTE` no cuentan, y la lista no trae textos. `unMuyNegativoFueraDelPeriodoNoEsAlertaSiLosUltimosTresEstanBien` |
| 5 | Dudas: respondida por el bot, contestada por otra persona, contestada solo por su autor, `DERIVADA` sin respuesta y reciente | `dudasSinResponderSegunLaReglaDeAtendida`: atendida, atendida, sin responder, sin responder (con `derivada = true`, aunque el bot le haya puesto su aviso) y fuera; con `horas=1`, la reciente entra |
| 6 | Sin clave, 401; clave de `bot` o de `ingesta`, 403; ruta disfrazada, 403 | `sinClaveEs401`, `lasClavesDelBotYDeLaIngestaNoAbrenElDashboard` (las 6 puertas), `laClaveDelBotNoEntraConUnaRutaDisfrazada` (4 rutas), `segundaCapaElControladorRechazaOtroCliente` |
| 7 | Período inválido o demasiado largo | `unParametroInvalidoEs422` (8 casos: al revés, 400 días, fecha mal escrita, `agrupar=mes`, `excluirOtro=quizas`, `dias` 0 o 1000, `horas` −1), `unPeriodoDe366DiasSiSeAcepta` |
| 8 | Las 143 anteriores | Pasan (total 169) |
| — | Totales y "sin datos" | `totalesDelPeriodo`, `sinFechasUsaLosUltimos30DiasYSinDatosDevuelveCeros` |

### 4.2 Panel

| Caso de la ficha | Prueba(s) |
|---|---|
| La página dibuja con un cliente simulado | `test_dibuja_los_indicadores_con_los_parametros_por_defecto` (6 métricas, 2 gráficos y 3 listas) |
| Los controles envían los parámetros correctos | `test_los_controles_envian_sus_valores` y, en el cliente, `test_el_dashboard_envia_fechas_iso_y_booleanos_de_java_sin_usuario` |
| Sin datos, muestra un aviso | `test_sin_datos_lo_dice_y_no_se_rompe`; además, `test_si_un_indicador_falla_los_demas_se_ven` y `test_un_periodo_a_medio_elegir_no_pide_nada` |
| Un `<script>` en una duda se muestra escapado | `test_una_duda_con_html_se_muestra_escapada` (y un nombre `<b>Camila</b>` en la tabla de deserción queda como texto) |
| Las 37 pruebas anteriores | Pasan |

### 4.3 Prueba real (2026-10-04)

Harrison corrió `docker compose up -d --build api-java panel`. 🧪 `docker compose ps`: `api-java` y `panel` en `(healthy)`. `flyway_schema_history`: la última versión es `7`.

**Lo que vio Harrison en el panel** (sus palabras, resumidas): el dashboard completo, con el resumen de KPI, los gráficos de barras apiladas (clima por fecha y temas en tendencia) y la sección "A quién ayudar". Según él, la frustración y las dudas sin responder "ayudan mucho a gestionar de manera ágil la comunidad en Discord".

**Comprobación del chat de tarea:** se consultaron las puertas reales desde el contenedor `api-java`, con su propia clave (sin mostrarla), y se compararon con consultas de solo lectura a la base:

| Puerta (período por defecto: los últimos 30 días) | Respuesta de Java | Base (solo lectura) |
|---|---|---|
| `totales` | mensajes 52, personas activas 10, dudas 21, logros 13, sin clasificar 0, borradores pendientes 8 | 52, 10, 21 y 13 iguales. Borradores: 8 `PENDIENTE`, 4 `APROBADO` y 1 `RECHAZADO` (después de T07 se generaron borradores nuevos) |
| `desercion` (14 días) | 0 personas | 0 alumnos con su último mensaje hace más de 14 días |
| `desercion?dias=3` | 7 personas | 7 de 8 alumnos |
| `frustracion` | 2 alumnos, los dos por `MUY_NEGATIVO` (con 1 y 2 negativos en el período) | 2 mensajes `MUY_NEGATIVO` de alumnos |
| `dudas-sin-responder` (24 h) | total 15, ninguna derivada | 15 dudas de alumnos sin respuesta y de hace más de 24 h. La única `DERIVADA` de un alumno es de las últimas 24 h, así que todavía no cuenta. Las otras 5 dudas son de mentores (no son alertas) |
| `sentimiento?agrupar=semana` | Una sola semana con datos: la del lunes 2026-09-28, con 49 mensajes | Coincide con la ficha: casi todos los mensajes son del 28 de septiembre |

Como se esperaba (§6.2), casi todas las dudas salen sin responder: los mentores no usaron "Responder" de Discord.

## 5. Decisiones que se tomaron

Los puntos 1 a 5 los validó Harrison el 2026-10-04, antes de empezar (puntos a–g de la propuesta del chat).

| # | Decisión | Alternativas descartadas | ¿Cambia el contrato, la arquitectura o D1 a D7? |
|---|---|---|---|
| 1 | El sentimiento, los temas y los totales cuentan a **todas las personas**; las **alertas**, solo a los alumnos (`autor_rol = miembro`) | Alertas para cualquier persona: 🧪 hay 2 mentores con 19 mensajes, que saldrían como "deserción" | Solo agrega a `PANEL_JAVA_v1` (DEC-122) |
| 2 | La deserción se mide **desde hoy**, con cualquier mensaje del alumno (también sin clasificar) | Medirla contra el fin del período | No |
| 3 | Frustración: el `MUY_NEGATIVO` tiene que estar en el período; los "últimos 3" son los 3 últimos mensajes `OK` con sentimiento, hasta el fin del período (DEC-121) | — | No |
| 4 | Días y semanas en hora de Bogotá, semanas desde el lunes, y los días vacíos en 0 | Agrupar en UTC (un mensaje de la noche caería al día siguiente) | No |
| 5 | 6 puertas separadas, una por indicador, y la V7 con un índice en `responde_a` | Una sola puerta con todo: si fallaba, no se veía nada | No |
| 6 | 🔎 `DashboardApiTest` usa **las mismas propiedades** que `CuraduriaApiTest`, para compartir el contexto de Spring | Propiedades propias: un contexto más abre otro grupo de 10 conexiones, y PostgreSQL (máximo 100, compartido con `api-java`) se quedó sin conexiones | No |
| 7 | La página usa `pandas` para armar las tablas de los gráficos. Ya viene con Streamlit: no es una librería nueva | — | No |

## 6. Dudas, riesgos y pendientes

| # | Tema | Detalle | Va a |
|---|---|---|---|
| 1 | Prueba real | Pendiente (§4.3) | Harrison, antes de auditar |
| 2 | 🔎 Casi todas las dudas van a salir "sin responder" | De las 21 dudas reales, ninguna tiene la respuesta de una persona con "Responder" de Discord. Las 16 que llegaron por lote salen sin responder (ya lo había advertido el chat principal). Es correcto según DEC-123, y OPERACION.md §11 lo explica | T10 (guion de la demo) |
| 3 | Conexiones de prueba | Cada combinación nueva de propiedades en una prueba `@SpringBootTest` suma 10 conexiones. Las próximas tareas deberían reutilizar las propiedades de `CuraduriaApiTest`, o bajar el tamaño del grupo de conexiones en las pruebas (`spring.datasource.hikari.maximum-pool-size`) | Chat principal ([CHAT_PRINCIPAL.md §5](../CHAT_PRINCIPAL.md), lecciones) |
| 4 | Frustración con datos viejos | La regla de "2 de los últimos 3" mira los últimos 3 mensajes aunque sean de hace meses: un alumno que dejó de escribir enojado sigue apareciendo. Va junto con la deserción | 🟡 |
| 5 | Tiempo de curaduría | No se muestra (ficha §4) | 🟡 |
| 6 | Entidad `Mensaje` | Sigue sin las columnas de V3 y V4: el dashboard usa SQL directo, como el resto | 🟡 |

## 7. Comandos que ejecutó Harrison

Desde la raíz del repositorio:

1. `docker compose up -d --build api-java panel`
2. La prueba en `http://127.0.0.1:8501` → **Dashboard**.
3. Los commits de la Parte A y de la Parte B, y el `push` (los da el chat de tarea al final).
