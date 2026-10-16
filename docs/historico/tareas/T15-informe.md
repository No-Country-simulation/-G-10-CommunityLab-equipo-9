# Informe de la tarea T15 — Dos PDF nuevos para el bot: preguntas frecuentes y programa del bootcamp

| Dato | Valor |
|---|---|
| Fecha | 2026-10-16 |
| Modelo de Claude usado | Opus 5.5 (la ficha recomendaba Sonnet 5.5) |
| Rama | `tarea/T15-pdf-preguntas-frecuentes` |
| Commits | `958a432` (PDF 12 y 13, generador y script de revisión), `96730c7` (índice con los dos PDF) y el de la documentación con este informe |

## 1. Resumen

Entraron al bot el PDF 12 (`12_Preguntas_Frecuentes_CommunityLab.pdf`, de Juan Sebastián Rodríguez), tal como está, y el PDF 13 (`13_Programa_del_Bootcamp_CommunityLab.pdf`), generado desde un Markdown con `fpdf2`. El índice nuevo tiene 80 fragmentos (PDF 12: 28 %; PDF 13: 6 %). 🧪 El script de revisión, que ahora revisa varios PDF y tiene la categoría "debilidad conocida", da `todo OK` en la IA real. El texto del PDF 13 tiene **una pregunta más** que la §4 de la ficha, y una pregunta del script cambió: las dos cosas las validó Harrison (sección 5).

## 2. Criterios de terminado

| Criterio | Estado | Evidencia |
|---|---|---|
| Los PDF 12 y 13 están en `pdfs/`, y el texto del 13 es el de la sección 4 | ✅ con un agregado validado | `958a432`: el PDF 12 entra con `git mv` (`rename … (100%)`). El 13 tiene el texto de la §4 **más** la pregunta "¿Qué contenido tiene el curso?" (decisión 1 de la sección 5). Prueba 1: el texto extraído es igual al `.md` |
| El índice nuevo está en git, y el script da `todo OK` con la categoría "debilidad conocida" explicada | ✅ | `96730c7`. Prueba 2 (sección 4.2), en la IA real y otra vez contra el índice de git |
| La prueba con Gemini y la prueba real dan lo esperado | ⚠️ Gemini: sí, salvo "¿Qué módulos tiene el bootcamp?", que no se pudo medir (Gemini respondió 503 y 504). La prueba real: pendiente | Secciones 4.3 y 7 |
| DEC-163, DEC-164, DEC-152 en ✅, ARQUITECTURA (§1 y §11), ESTADO y OPERACION al día | ✅ | Sección 3 |
| El informe está completo, y no se tocó nada fuera del alcance | ✅ | No se tocó código del Agente FAQ, del bot ni de la IA, ni `TOP_N_RERANK`, los umbrales o los documentos `00_…` a `11_…`. No se tocó el texto del PDF 12. No se leyó el `.env` |

## 3. Archivos cambiados

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `agents/agent_faq/data/pdfs/12_Preguntas_Frecuentes_CommunityLab.pdf` | Llega desde `pdfs_en_revision/` con `git mv`, sin cambios (misma huella sha256) | Punto 1 de la ficha |
| `agents/agent_faq/data/pdfs/13_Programa_del_Bootcamp_CommunityLab.pdf` (nuevo) | 2 páginas, Helvetica, con encabezado y pie de la §4 | Punto 2 |
| `scripts/pdf_programa/13_Programa_del_Bootcamp_CommunityLab.md` (nuevo) | El texto del PDF 13 | La fuente: para cambiar el PDF se cambia este archivo |
| `scripts/pdf_programa/generar.py` (nuevo) | Genera el PDF con `fpdf2==2.8.3` en un contenedor desechable. Antes de generar, falla si hay caracteres fuera de latin-1. Usa una fecha fija: el mismo texto da el mismo PDF, byte a byte | Punto 2 |
| `agents/agent_faq/data/vectorstore/faiss_pdfs/` | Índice nuevo: 80 fragmentos (antes, 53 sin el PDF 12, o 75 con él) | Punto 3 |
| `scripts/revisar_buscador_faq.py` | `PDFS_NUEVOS` (12 y 13), con un tope de 35 % para cada uno y el total. Cada pregunta "nuevo" dice qué PDF debe ganar. Suma "¿Cuánto dura un período académico?" y las 4 del PDF 13. Agrega la categoría `debilidad`, con su motivo. La pregunta del computador pasa a "para empezar" | Puntos 4 y 5 |
| `agents/agent_faq/data/pdfs_en_revision/README.md` | Una sección "Estado": el PDF 12 salió de la carpeta y entró, con su resultado; el manual se queda | Punto 6 |
| `docs/DECISIONES.md` | DEC-163 y DEC-164 nuevas; DEC-152 ✅ | Punto 7 |
| `docs/ARQUITECTURA.md` | §1 (los documentos incluyen preguntas frecuentes y el programa), §8 (el script revisa los PDF 12 y 13), §11 (créditos de los dos PDF) y §12 (límite del reordenador) | Punto 8 |
| `docs/ESTADO.md` | §3, punto 6 ✅; dos mejoras 🟡 (Política de IA con "ChatGPT" y "clases grabadas" como respondida); §5, las filas de T13 y T15 | Punto 9 |
| `docs/OPERACION.md` | §14: cómo sumar un PDF al script, el tope por PDF, la "debilidad conocida" y cómo regenerar el PDF 13 | Punto 10 |

## 4. Pruebas

Todas las pruebas aisladas se hicieron en contenedores desechables (de `python:3.12-slim` o de la imagen `ia`). Los PDF se montaron en solo lectura, y el índice temporal se creó en memoria. No tocaron la IA del bot, la base ni Discord.

| # | Comando ejecutado | Resultado (🧪) |
|---|---|---|
| 1 | `PyPDFLoader` (el lector del Agente FAQ) sobre el PDF 13, comparado palabra por palabra con el `.md` | ✅ 527 palabras iguales. Caracteres especiales: `·¿áéíñóú`. Sin palabras pegadas |
| 2 | `docker compose exec -e PYTHONIOENCODING=utf-8 ia python /tmp/revisar_buscador_faq.py` (Harrison, con la IA rehecha) | ✅ `Resultado: todo OK`. Se repitió contra el índice ya guardado en git, con el mismo resultado |
| 3 | Las preguntas del script, más "¿Qué computador necesito para el bootcamp?", con Gemini (`BuscadorTool.ejecutar`, la misma regla de `grafo_v1.py:90`), en un contenedor de un solo uso (`docker compose run --rm --no-deps ia`) | ⚠️ 16 de 17 dan lo esperado; "¿Qué módulos…?" sin medir (sección 4.3) |
| 4 | `python -m pytest agents/orquestador/tests -q` (en un contenedor desechable de la imagen `ia`, con `pytest`) | ✅ `79 passed` |

### 4.1 Prueba 1 y el ensayo, antes de rehacer la IA

Con el texto de la §4 tal cual, el ensayo del script dio **2 fallas**:

| Pregunta | Ganó | Motivo (🔎 deducido de los puntajes) |
|---|---|---|
| ¿Qué contenido tiene el curso? | PDF 12, pág. 1 (−5,36) | El PDF 13 no tenía "contenido" ni "curso" cerca de los módulos: su primer fragmento ni siquiera estaba entre los 8 candidatos de FAISS |
| ¿Qué computador necesito **para el bootcamp**? | PDF 13 (los 3 primeros lugares) | El PDF 13 repite "bootcamp", y el PDF 12 dice "para programar". El primer fragmento del PDF 12 quedó 4.º (2,00), fuera de los 3 que lee Gemini |

Variantes medidas (fuera del repositorio, sin Gemini):

| Variante | Fallas |
|---|---|
| Texto de la §4 | 2 (contenido y computador) |
| A: pregunta-resumen "¿Qué contenido tiene el curso?" al comienzo | 2 (computador y "¿Cuánto dura un período académico?", que pasó a ganarla el PDF 13 con 7,65) |
| B: A + encabezado sin "bootcamp" | 4 |
| C: pregunta-resumen en "Otras dudas" | 2 (computador y "ruta de ciencia de datos") |
| **D: pregunta-resumen después de "¿Cómo está organizado el bootcamp?"** | **1 (computador)** |

La falla del computador sale en las 5 variantes. "¿Qué computador necesito para empezar?" (el mensaje 264 de la prueba en vivo) y "…para programar?" sí las gana el PDF 12, con 2,47 y 6,72. 🔎 El reordenador (`ms-marco-MiniLM-L-6-v2`) está entrenado en inglés, y un cambio pequeño mueve mucho los puntajes.

### 4.2 Prueba 2 en la IA real (salida resumida)

```
Índice: 80 fragmentos.
  12_Preguntas_Frecuentes_CommunityLab: 22 fragmentos (28 %)
  13_Programa_del_Bootcamp_CommunityLab: 5 fragmentos (6 %)
  Todos los PDF nuevos: 27 fragmentos (34 %)
OK     [oficial] ¿Hay becas…?                          09_Política_de_Becas pág. 1 (-0.80)
OK     [oficial] ¿Cuándo empiezan las clases…?         11_Calendario pág. 1 (2.65)
OK     [oficial] ¿Cuánto dura un período académico?    01_Reglamento_Academico pág. 1 (-0.09)
OK     [oficial] ¿Cómo apelo una calificación…?        07_Procedimiento_Apelaciones pág. 1 (4.50)
OK     [oficial] ¿Puedo pedir una extensión…?          02_Politica_de_Evaluacion pág. 1 (0.81)
DÉBIL  [debilidad conocida] ¿Cómo se calcula la nota final…?   13_Programa pág. 2 (-2.38)
DÉBIL  [debilidad conocida] ¿Puedo usar ChatGPT…?              12_Preguntas pág. 1 (1.13)
OK     [debilidad conocida] ¿Pueden publicar mi nombre en LinkedIn?   10_Reglamento_de_Comunicaciones pág. 1 (-4.92)
OK     [nuevo] ¿Las clases quedan grabadas?            12_Preguntas pág. 1 (6.38)
OK     [nuevo] ¿Puedo estudiar si trabajo?             12_Preguntas pág. 1 (6.75)
OK     [nuevo] ¿Qué computador necesito para empezar?  12_Preguntas pág. 1 (2.47)
OK     [nuevo] ¿Qué es una API?                        12_Preguntas pág. 4 (7.66)
OK     [nuevo] ¿Qué contenido tiene el curso?          13_Programa pág. 1 (7.09)
OK     [nuevo] ¿Qué módulos tiene el bootcamp?         13_Programa pág. 1 (7.26)
OK     [nuevo] ¿Hay una ruta de ciencia de datos?      13_Programa pág. 2 (7.50)
OK     [nuevo] ¿Cuántas horas a la semana…?            13_Programa pág. 1 (4.15)
Resultado: todo OK
```

### 4.3 Prueba 3, con Gemini

Cada pregunta pasa por `BuscadorTool.ejecutar`: los 3 fragmentos, la respuesta de Gemini y la revisión anti-invención. El bot **responde** solo si hay respaldo y no se pide revisión (`grafo_v1.py:90`). La prueba usa la clave de la IA desde `compose.yml`: el `.env` no se leyó. Las columnas "Solo oficiales" y "Con el PDF 12" son de la tabla 2.2 de la ficha.

| Pregunta | Solo oficiales | Con el PDF 12 | **Con los PDF 12 y 13** (🧪 hoy) |
|---|---|---|---|
| ¿Hay becas y cuáles son los requisitos…? | Responde | Responde | Responde · `09_Política_de_Becas` pág. 1 |
| ¿Cuándo empiezan las clases del próximo período? | Responde | Responde | Responde · `11_Calendario` pág. 1 (18 de enero y 19 de julio de 2027) |
| ¿Cuánto dura un período académico? (nueva) | — | — | Responde · `01_Reglamento_Academico` pág. 1, con las fechas de inicio y fin de cada período |
| ¿Cómo apelo una calificación…? | Responde | Responde | Responde · `07_Procedimiento_Apelaciones` pág. 1 |
| ¿Puedo pedir una extensión de plazo si me enfermo? | Responde | Responde | Responde · `02_Politica_de_Evaluacion` pág. 1 |
| ¿Cómo se calcula la nota final de un módulo? | Deriva | Deriva | Deriva (igual) |
| ¿Puedo usar ChatGPT para hacer mis entregas? | Responde bien | Deriva | Deriva (igual que con el PDF 12) |
| ¿Pueden publicar mi nombre en LinkedIn? | Responde **mal** | Deriva | Deriva (igual) |
| ¿Las clases quedan grabadas? | Deriva | Responde | Responde · PDF 12 pág. 1 ("pregunta a un mentor en `#dudas`") |
| ¿Puedo estudiar si trabajo? | Deriva | Responde | Responde · PDF 12 pág. 1 |
| ¿Qué computador necesito para empezar? | Deriva | Responde (*) | Responde · PDF 12 pág. 1 |
| ¿Qué es una API? | Deriva | Responde | Responde · PDF 12 pág. 4 |
| ¿Qué contenido tiene el curso? | Deriva (mensaje 259) | Deriva | ✅ **Responde** · PDF 13 pág. 1, con los 8 módulos por período |
| ¿Qué módulos tiene el bootcamp? | — | — | **No probado**: Gemini respondió 504 y después 503. El buscador elige el PDF 13 pág. 1 (7,26), el mismo fragmento de "contenido del curso" |
| ¿Hay una ruta de ciencia de datos? | Respondía con definiciones generales (mensaje 262) | — | ✅ **Responde** · PDF 13 pág. 2 ("no como programa aparte… el Módulo 7") |
| ¿Cuántas horas a la semana tengo que dedicarle? | — | — | ✅ Responde · PDF 13 pág. 1 (15 a 20 horas) |
| ¿Qué computador necesito **para el bootcamp**? | — | Responde (*) | Deriva (el buscador lleva al PDF 13) |

(*) En la ficha, "computador" se midió con 5 fragmentos y con "para el bootcamp", que era la pregunta del script.

**Balance:** ninguna pregunta de la tabla 2.2 empeora, salvo el computador dicho "para el bootcamp", que pasa a derivarse: sin información falsa, y aceptado en la decisión 2 de la sección 5. Las 4 del PDF 12 responden con su PDF, y 3 de las 4 del PDF 13 también; la cuarta no se pudo medir.

**Costo:** hubo **68 intentos** de llamada a Gemini en 3 corridas. Muchos fueron rechazos 503 ("demanda alta") y un 504; con los reintentos automáticos, el total pasó la estimación de 35 a 50. Las 16 preguntas que terminaron usan como máximo 2 llamadas cada una (unas 30 llamadas útiles). 🔎 Un 503 lo rechaza Google antes de procesarlo, así que probablemente no se cobra (no se verificó en la cuenta).

## 5. Decisiones que se tomaron

| Decisión | Alternativas descartadas | ¿Cambia el contrato, la arquitectura o D1 a D7? |
|---|---|---|
| 👤 **1. El PDF 13 suma la pregunta "¿Qué contenido tiene el curso?"**, con los 8 módulos en una respuesta, después de "¿Cómo está organizado el bootcamp?" (variante D). Validada por Harrison el 2026-10-16 | Dejar el texto de la §4 tal cual (falla justo la pregunta del mensaje 259, que el PDF 13 debía arreglar); las variantes A, B y C (sección 4.1) | No |
| 👤 **2. La pregunta del computador en el script pasa a "¿Qué computador necesito para empezar?"**, la del mensaje 264. "…para el bootcamp?" queda medida en la prueba 3 y anotada en ARQUITECTURA §12. Validada por Harrison | Editar nosotros el PDF 12 (es de Juan Sebastián, y la ficha dice integrarlo tal como está); pedirle el cambio a él (Harrison prefirió no hacerlo); marcarla como "debilidad conocida" (no vale: no fallaba antes del PDF 13) | No |
| DEC-163: entran los PDF 12 y 13 | — (decisiones 1 y 2 de la ficha) | No |
| DEC-164: la categoría "debilidad conocida" | — (punto 5 de la ficha) | No |
| Generar el PDF 13 con Helvetica (fuente de fábrica, latin-1) y una fecha fija | Una fuente TTF Unicode (había que instalar fuentes en el contenedor, y el texto no necesita nada fuera de latin-1) | No |

## 6. Dudas, riesgos y pendientes

- **"¿Qué computador necesito para el bootcamp?"** lleva al PDF 13, y el bot la deriva a un mentor (🧪 prueba 3). No da información falsa, pero antes se respondía. Arreglarlo de verdad exige que el PDF 12 diga "bootcamp" en esa pregunta (es de Juan Sebastián) o cambiar el reordenador: las dos cosas están fuera de esta tarea.
- **"¿Qué módulos tiene el bootcamp?" no se probó con Gemini** (503 y 504). Se puede repetir cuando Gemini tenga menos demanda, o sumarla a la prueba real.
- **El reordenador es frágil con el español** (sección 4.1): el próximo PDF puede mover preguntas que hoy pasan. Para eso está el script; las preguntas que fallen sin respaldo de una medición no deben pasar a "debilidad conocida".
- **"¿Las clases quedan grabadas?"** se responde, pero la respuesta dice que se consulte a un mentor. En el dashboard cuenta como respondida (mejora 🟡 en ESTADO).
- **ChatGPT**: la mejora (que la Política de IA diga "ChatGPT") queda en ESTADO. Cambiar un documento oficial está fuera de esta tarea.
- **Gemini respondió 503 (demanda alta)** en 10 de las 17 preguntas del primer intento. Se repitieron con reintentos: 68 intentos en total, por encima de la estimación de 35 a 50 (detalle en la sección 4.3).

## 7. Comandos que ejecutó Harrison

En PowerShell, desde la raíz del repositorio:

1. `Remove-Item agents\agent_faq\data\pdfs\12_Preguntas_Frecuentes_CommunityLab.pdf` (la copia, idéntica a la de `pdfs_en_revision/`)
2. `git mv agents/agent_faq/data/pdfs_en_revision/12_Preguntas_Frecuentes_CommunityLab.pdf agents/agent_faq/data/pdfs/`
3. `git add -f agents/agent_faq/data/pdfs/13_Programa_del_Bootcamp_CommunityLab.pdf`
4. `git add scripts/pdf_programa/generar.py scripts/pdf_programa/13_Programa_del_Bootcamp_CommunityLab.md scripts/revisar_buscador_faq.py`
5. `git commit -m "feat: PDF 12 y PDF 13 para el Agente FAQ, generador del PDF 13 y revision del buscador con varios PDF"` → `958a432`
6. `docker compose up -d --no-deps --build ia` → `ia` `(healthy)`
7. `docker compose cp scripts/revisar_buscador_faq.py ia:/tmp/revisar_buscador_faq.py`
8. `docker compose exec -e PYTHONIOENCODING=utf-8 ia python /tmp/revisar_buscador_faq.py` → `todo OK`
9. `docker compose cp ia:/app/agents/agent_faq/data/vectorstore/faiss_pdfs agents/agent_faq/data/vectorstore/`
10. `git add -f agents/agent_faq/data/vectorstore/faiss_pdfs`
11. `git commit -m "feat: indice del Agente FAQ con los PDF 12 y 13"` → `96730c7`

### Prueba real en `#dudas`

**Primer intento (2026-10-16, 10:31 a 10:33): no sirve como prueba.** Las 4 primeras preguntas se derivaron con el mensaje genérico, incluida "¿Las clases quedan grabadas?", que una hora antes se respondía con el PDF 12. 🧪 El registro de `ia` muestra la causa: 3 mensajes agotaron el tope de 25 s esperando a Gemini ("se agotó el tope de 25 s antes de la respuesta del Agente FAQ"), y en 1 Gemini respondió `503 UNAVAILABLE` ("high demand"). Gemini estaba saturado, igual que en la prueba 3. No se llegó a comparar con los PDF. El bot hizo lo que debe hacer ante un fallo del LLM: derivar (D3).

Segundo intento: pendiente, cuando Gemini tenga menos demanda. Una pregunta a la vez; se completa esta tabla.

| Pregunta | El bot | Documento |
|---|---|---|
| ¿Qué contenido tiene el curso? | | |
| ¿Hay una ruta de ciencia de datos? | | |
| ¿Cuántas horas a la semana tengo que dedicarle? | | |
| ¿Las clases quedan grabadas? | | |
| ¿Hay becas y cuáles son los requisitos? | | |
| ¿Qué módulos tiene el bootcamp? (agregada: no se pudo medir en la prueba 3) | | |

**Más intentos del 2026-10-16** (todos derivaron, y el registro de `ia`, Java y el bot dice por qué):

| Hora | Clave y modelo | Qué pasó |
|---|---|---|
| 10:39 | Clave original, `gemini-3.5-flash-lite` | ✅ "¿Las clases quedan grabadas?" se respondió con el PDF 12, pág. 1 |
| 10:40 | Ídem | Las 5 preguntas en **un solo mensaje**: deriva (es lo esperado: no hay un fragmento que responda las 5) |
| 10:41 | Ídem | 2 mensajes: los dos agotaron el tope de 25 s (cada llamada tardó unos 10 s) |
| 11:09 | Clave de otra cuenta de Google, mismo modelo | Clasificar ✅ (7 s), responder ✅ (4 s), revisar ❌ `503` |
| 11:20 | Clave nueva, `gemini-flash-lite-latest` | Agotó el tope de 25 s |
| 11:24 | Ídem | Clasificar: `503`, reintento; agotó el tope (25,1 s en Java). Después, la respuesta también dio `503` |

🧪 Medición aparte, con el mismo camino del bot, para "¿Qué contenido tiene el curso?" con `gemini-flash-lite-latest`: clasificar tardó 17,1 s (y en dos repeticiones, 5,9 y 8,9 s), responder 4,9 s y revisar 3,3 s. La respuesta salió bien del PDF 13, con fidelidad 1,0. Tokens de toda la duda: unos 2.400 de entrada y 320 de salida, sin "pensamiento". **El consumo no era el problema**: lo eran los 503 y la lentitud de Google.

## 8. Parte D · El bot resiste a Gemini lento o saturado (autorizada por Harrison, 2026-10-16)

Está **fuera del alcance original** de la ficha (§5 prohibía tocar el bot). Harrison lo autorizó para la demo ("no importa si la tarea 15 no lo permite, te doy permiso") y pidió hacerlo en un solo commit. **T15 no causó el problema**: no cambió ni una línea de código de la IA ni del bot, y una duda hace las mismas 1 a 3 llamadas que antes (sección 7).

| Cambio | Qué hace | Archivos |
|---|---|---|
| **DEC-165 · Modelo de respaldo** | `GEMINI_MODELO_RESPALDO` (opcional). Si el modelo principal falla (503 u otro error), el clasificador y el Agente FAQ (respuesta y revisión) repiten la misma llamada con este modelo (`with_fallbacks` de LangChain). Vacío o igual al principal = como antes. El Agente-Mod no lo usa | `agents/orquestador/config.py`, `clasificadores/llm_models.py` (`con_respaldo`, `build_llm(usar_respaldo=…)`), `clasificadores/etiquetador.py`, `agents/agent_faq/config.py`, `agent_faq/llm_models.py` |
| **DEC-166 · Tiempos** | Tope en vivo 25 → **40 s**; Java → IA 30 → **45 s**; bot → Java 40 → **55 s**. Los tres pasan a ser variables | `agents/orquestador/config.py`, `RestClientConfig.java` (`ia.tiempo-lectura-s`), `application.properties`, `bot_communitylab.py`, `compose.yml`, `.env.example` |
| Comentarios | Los "30 s" de las reservas y del cliente de la IA pasan a "45 s" (las reservas siguen alcanzando: 3 × 45 < 180 y 45 < 120) | `GeneracionProperties.java`, `ClasificacionProperties.java`, `NlpDataClient.java` |
| Pruebas | 7 pruebas nuevas del respaldo; la de Java comprueba 45 s > 40 s; la del bot, 55 s | `test_v1_procesar.py`, `NlpDataClientTest.java`, `test_bot.py` |
| Documentación | Contratos (solo la tabla de tiempos, con una nota del cambio), DEC-165, DEC-166, DEC-20 y DEC-54 al día, ARQUITECTURA §4 y §8, OPERACION §2 y §15 (nueva), ESTADO §3 punto 7 | `docs/` |

**No se tocó** la revisión anti-alucinación, los umbrales, los fragmentos, el texto de la derivación, los PDF ni el índice.

**Pruebas de la Parte D**

| Comando | Resultado (🧪) |
|---|---|
| `python -m pytest agents/orquestador/tests -q` (contenedor desechable de la imagen `ia`) | ✅ `86 passed` (79 + 7 nuevas) |
| `python -m pytest agents/bot_discord/tests -q` (contenedor desechable de la imagen `bot`) | ✅ `22 passed` |
| El Agente FAQ arranca con un respaldo configurado (clave falsa, sin llamar a Gemini) | ✅ `RunnableWithFallbacks modelo-principal -> ['modelo-respaldo']`, y la revisión también tiene respaldo |
| `mvn test` (OPERACION §5, contra `insightedu_test`) | ✅ 256 pruebas, 0 fallas, 0 errores (informes de Surefire), incluida `losTiemposSonLosDeD4` (45 s > 40 s) |
| Prueba real en `#dudas`, después de reconstruir | Pendiente |

**Lo que no se puede garantizar:** si Google rechaza a la cuenta gratuita en todos los modelos a la vez, el bot deriva (D3). Para la demo se recomienda una clave con facturación (ESTADO §3, punto 7).
