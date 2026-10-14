# Informe de la tarea T12 — Dashboard por rol, con tema claro y oscuro

| Dato | Valor |
|---|---|
| Fecha | 2026-10-14 |
| Modelo de Claude usado | Opus 5.5 |
| Rama | `tarea/T12-dashboard` |
| Commits | Pendientes: uno por parte (A: Java y contrato; B: panel; C: documentación). Los ejecuta Harrison (§7) |

## 1. Resumen

Java tiene dos puertas nuevas de solo lectura (`/dashboard/comunidad` y `/dashboard/contenido`), el filtro `rol` en sentimiento y temas, `servidorId` y `canalId` en las dudas y la frustración acotada al período (DEC-157); todo solo agrega y sin migración. La página **Dashboard** se rehízo con dos vistas por rol, la franja de valor, gráficos de Altair y tema claro y oscuro. **Falta la prueba real de Harrison** (§2 y §6): ver las dos vistas en el navegador, el cambio de tema y "Abrir en Discord".

## 2. Criterios de terminado

| Criterio | Estado | Evidencia |
|---|---|---|
| Las dos vistas muestran los KPI de la sección 2, en el orden de la decisión 3, con la n visible y el supuesto de P1 escrito | ✅ en pruebas · ⏳ falta verlo en el navegador | `test_comunidad_muestra_las_tarjetas_con_su_n` comprueba el orden franja → 4 tarjetas; `test_p1_muestra_el_supuesto…` la frase exacta; los textos con `n = …` en las dos vistas |
| Las puertas nuevas solo agregan, solo abren con la clave `panel` y están en `PANEL_JAVA_v1.md` con ejemplos | ✅ | `DashboardApiTest`: 401 sin clave, 403 con `bot` e `ingesta` y con rutas disfrazadas, segunda capa del controlador. `sinRolEsIgualQueAntes…`: sin `rol` la respuesta es idéntica a `rol=todos`. Contrato §7.1 a §7.4 |
| El tema claro y oscuro funciona desde el menú de Streamlit, y los gráficos se leen en los dos | ⚠️ parcial | `test_la_paleta_cambia_con_el_tema` (con `st.context.theme` simulado). 🔎 `viewer` deja el selector de tema (§5). **No probado en el navegador** |
| Las pruebas de Java y de Python pasan, y la prueba real coincide con los valores de hoy | ⚠️ parcial | Java 243/0/0 y panel 64 passed (§4). Valores comparados con SQL de solo lectura sobre la base real (§4.3). La prueba real de la ficha §5 la corre Harrison |
| DEC-153 a DEC-157, ARQUITECTURA, OPERACION y ESTADO al día | ✅ | `docs/DECISIONES.md` (más DEC-121 y DEC-124), ARQUITECTURA §4.7, OPERACION §11, ESTADO (OE5 y mejoras) |
| El informe está completo y no se tocó nada fuera del alcance | ✅ | Este archivo. Lo único extra: una línea del README §8.4 que describía el dashboard viejo (§3) |

## 3. Archivos cambiados

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `backend-java/.../dashboard/VistasDashboard.java` | Formas `Comunidad`, `Contenido` y sus partes; `servidorId` y `canalId` en `DudaSinResponder` | Parte A, puntos 2 a 4 |
| `backend-java/.../dashboard/DashboardRepository.java` | Filtro `soloAlumnos` en sentimiento y temas; frustración solo con el período; 8 consultas nuevas (alumnos, bot, derivadas por tema, pendientes, revisión, embudo, aprobados por semana, logro → aprobación, activos en OCI) | Parte A, puntos 1 a 5 |
| `backend-java/.../dashboard/DashboardService.java` | `rol` validado (`todos` o `alumnos`, si no 422); `comunidad()` y `contenido()`, con los tres tipos y las semanas en 0 | Parte A |
| `backend-java/.../controller/DashboardController.java` | `rol` en sentimiento y temas; `GET /comunidad` y `GET /contenido`, con la segunda revisión del cliente | Parte A, punto 6 |
| `backend-java/.../DashboardApiTest.java` | 9 pruebas nuevas y 5 ampliadas (casos 1 a 7 de la ficha) | Ficha §5 |
| `docs/contratos/PANEL_JAVA_v1.md` | Nota de T12, `rol`, reglas nuevas, las dos puertas, los campos de las dudas y 4 ejemplos | Parte A, punto 7 |
| `panel/paginas/dashboard.py` | Rehecha: vista Comunidad / Contenido, atajos 7-30-90 y "Elegir fechas", ajustes en un expander, franja P1 y P4, tarjetas, gráficos de Altair, listas, "Abrir en Discord", P5 en la barra lateral, sin "Sin clasificar" | Parte B, puntos 8 y 9 |
| `panel/cliente_java.py` | `rol` (solo se envía si es `alumnos`), `dashboard_comunidad` y `dashboard_contenido` | Parte B, punto 11 |
| `panel/ui.py` | `tema_oscuro()` con `st.context.theme` | Parte B, punto 10 |
| `panel/.streamlit/config.toml` | `[theme.light]`, `[theme.dark]` y `toolbarMode = "viewer"` | Parte B, punto 10 (DEC-156) |
| `panel/tests/test_dashboard.py` y `test_cliente.py` | 18 pruebas de la página (reemplazan las 6 de T08) y 1 del cliente | Ficha §5 |
| `compose.yml` y `.env.example` | `PANEL_MINUTOS_POR_HISTORIA`, 30 por defecto | Parte B, punto 11 |
| `docs/DECISIONES.md`, `ARQUITECTURA.md`, `OPERACION.md`, `ESTADO.md` | DEC-153 a DEC-157, DEC-121 y DEC-124 actualizadas; §4.7; §11 (cómo leerlo, el supuesto de P1 y cómo cambiar el tema); OE5 y mejoras | Parte C |
| `README.md` | §8.4: una línea que describía el dashboard de T08 | Quedaba falsa |

## 4. Pruebas

| Comando ejecutado | Resultado (🧪) |
|---|---|
| Java, el de [OPERACION.md §5](../../OPERACION.md) (`mvn test` en Docker contra `insightedu_test`) | **243 pruebas, 0 fallas, 0 errores** (eran 225). `DashboardApiTest`: 44 |
| Panel, en la imagen `insightedu-panel` con `pytest` instalado (en el Python de Windows no hay Streamlit) | Antes: **51 passed**. Después: **64 passed** |
| `docker compose config --quiet` | Sin errores |

### 4.1 Comandos

```
docker run --rm --network insightedu_default --env-file .env -e POSTGRES_HOST=postgres -e POSTGRES_DB=insightedu_test -v "<repo>/backend-java:/app" -v insightedu-maven:/root/.m2 -w /app maven:3.9-eclipse-temurin-21 mvn -q test
docker run --rm --user root -v "<repo>:/repo" -w /repo --entrypoint sh insightedu-panel -c "pip install -q pytest; python -m pytest panel/tests -q"
```

### 4.2 Qué cubren las pruebas nuevas

| Caso de la ficha | Prueba |
|---|---|
| 1. Sentimiento y temas con y sin `rol` | `sinRolEsIgualQueAntesYConAlumnosSeQuitanLosMentores` |
| 2. `/comunidad` | `comunidadCuentaAlumnosActivosElBotYLasDerivadasPorTema` (con el borde de las 23:00 de Bogotá) y `comunidadSinDatosDaCerosYMedianaNula` |
| 3. `/contenido` | `contenidoMedianasAprobacionEmbudoSemanasYPendientes` (mediana par 25 e impar 7; semana de aprobación en hora de Bogotá; pendiente más antiguo; OCI) y `contenidoSinDatosDaCerosYMedianasNulas` |
| 4. Frustración | `dosNegativosViejosYUnoRecienteYaNoSonAlerta` |
| 5. Dudas con servidor y canal | `dudasSinResponderSegunLaReglaDeAtendida`, ampliada |
| 6. Claves | `sinClaveEs401`, `lasClavesDelBotYDeLaIngestaNoAbrenElDashboard`, `laClaveDelBotNoEntraConUnaRutaDisfrazada` y `segundaCapa…`, ampliadas |
| 7. Período inválido o de más de 366 días, `rol` desconocido | `unParametroInvalidoEs422`, ampliada |
| Panel | Cada vista pide solo lo suyo; P1 con 30 y con 45 minutos; la n en cada tarjeta; sin datos, avisos; `<script>` escapado; el enlace a Discord (y sin botón si falta el servidor); la paleta clara y la oscura; atajos, "Elegir fechas" y ajustes; P5 en la barra lateral; un dato que falla no tumba la página |

### 4.3 Valores de hoy contra la base real

Consultas de solo lectura con el período por defecto (2026-09-15 a 2026-10-14), con el mismo SQL de las puertas. Hoy entraron mensajes nuevos (el último, a las 22:24 UTC), así que algunos valores cambiaron desde la ficha.

| KPI | Ficha | Hoy (🧪) | Nota |
|---|---|---|---|
| C6 alumnos activos | 2 de 9 · 9 de 9 | 2 de 9 · 9 de 9 | = |
| C5 base | 18 dudas de alumnos | 18 | = |
| C4 bot | 4 de 10 · 6 s · 6 derivadas · 17 por lote | 4 de 11 · **3,2 s (mediana)** · 7 derivadas · 17 por lote | Una derivada nueva. La ficha daba el promedio; ver §5 |
| M5 revisión | Post 62 s (n = 9) · caso 5 s (n = 7) · FAQ 1.000 s (n = 1) | Igual | = |
| M4 aprobación | 94 % (16 de 17) | 16 de 17 | = |
| M6 + M7 embudo | 16 → 9 → 9 | **18 → 11 → 9** | Dos logros nuevos de hoy, publicables, con su post pendiente |
| M1 por revisar | 3 (2 casos y 1 FAQ) | **7** (4 casos, 2 posts y 1 FAQ) | Los borradores de esos logros |
| P4 | 9 (de 64 mensajes y 16 logros) | 11 (de 67 y 18) | Ídem |
| P1 | ≈ 4,4 h | ≈ 4,3 h ((30 − 1,03) × 9 / 60) | La ficha redondeó la revisión a 1 min |

No se comprobó en la pantalla: es la prueba real de Harrison (ficha §5).

## 5. Decisiones que se tomaron

| Decisión | Alternativas descartadas | ¿Cambia el contrato, la arquitectura o D1 a D7? |
|---|---|---|
| La reacción del bot va como **mediana** (`segundosMediana`), no como promedio | `segundosPromedio`, como decía la Parte A punto 2 de la ficha. Se eligió la mediana por la decisión 5 de la ficha ("mediana para los tiempos"). **Revisar** si el chat principal prefiere el promedio | Agrega un campo al contrato (solo agrega) |
| `alumnos.dudas` en `/comunidad`: las dudas de alumnos del período | Pedirlo a otra puerta: ninguna lo daba separado por rol, y la tarjeta C5 ("14 **de 18**") lo necesita | Agrega un campo |
| `toolbarMode = "viewer"` | `minimal`: 🔎 en el código del menú de Streamlit 1.65, sin opciones externas el menú no se dibuja, y con él desaparece el selector de tema | No |
| La vista Comunidad pide el sentimiento 3 veces (alumnos, toda la comunidad y el período anterior) | Una puerta nueva que diera el índice ya calculado: más contrato para algo que el panel suma en una línea | No |
| El clima va por día con 7 días y por semana con 30 o 90 | Un control "Ver por": la ficha no lo pide y suma un control | No |
| `rol` solo viaja si es `alumnos` | Enviar siempre `rol=todos`: así el pedido de siempre queda idéntico | No |
| El texto aprobado se copia con el ícono de `st.code` | Un botón propio: Streamlit no trae uno, y haría falta HTML | No |
| Sin migración `V9` | Un índice nuevo: las consultas usan los índices de `fecha`, `estado` y `mensaje_id`, y las tablas son chicas. T13 queda libre para su `V9` | No |
| Se quitaron "Ver por" y "Excluir el tema «otro»" de la página | Conservarlos: la ficha define los controles (vista, período, ajustes) y el tope de 4 tarjetas. Las puertas siguen aceptando esos parámetros | No |

## 6. Dudas, riesgos y pendientes

1. **Prueba real pendiente** (ficha §5): `docker compose up -d --build api-java panel`, revisar las dos vistas, cambiar a oscuro desde ⋮ → Settings y probar "Abrir en Discord". No se vio la página en un navegador.
2. **`st.context.theme` al cambiar de tema:** 📘 la documentación de Streamlit avisa que el tipo de tema puede ser incorrecto mientras cambia. Si al pasar a oscuro los gráficos siguen con la paleta clara, recargar la página (F5) debería arreglarlo. Revisarlo en la prueba real.
3. **El borde de las tarjetas** lo fija `ui.ESTILOS` en `#374151` (el diseño de DEC-109): en el tema claro se ve más oscuro que el resto. No se cambió para no tocar el diseño del equipo.
4. **Deserción:** cuenta a todos los alumnos que escribieron alguna vez (contra hoy), y el total de alumnos se cuenta hasta el fin del período. Con un período en el pasado, "7 de 9" podría mezclar dos momentos. Con los atajos (que terminan hoy) coinciden.
5. **Mediana del bot** (§5): confirmar o volver al promedio.

## 7. Comandos que ejecutó Harrison

Pendientes, en `C:\Users\LENOVO\Documents\Cursos\No Country\Hackaton ONE 10\insightedu-lab` y en la rama `tarea/T12-dashboard`: un commit por parte (A, B y C), `git push` y la prueba real. Al terminar, completar aquí los hashes de los commits.
