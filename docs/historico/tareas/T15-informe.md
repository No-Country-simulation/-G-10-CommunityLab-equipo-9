# Informe de la tarea T15 — Dos PDF nuevos para el bot: preguntas frecuentes y programa del bootcamp

| Dato | Valor |
|---|---|
| Fecha | 2026-10-16 |
| Modelo de Claude usado | Opus 5.5 (la ficha recomendaba Sonnet 5.5) |
| Rama | `tarea/T15-pdf-preguntas-frecuentes` |
| Commits | `958a432` (PDF 12 y 13, generador y script de revisión), `96730c7` (índice con los dos PDF), `774d29e` (documentación de T15), `28c7f3e` (Parte D: respaldo de Gemini y tiempos) y el del cierre de este informe |

## 1. Resumen

Entraron al bot el PDF 12 (`12_Preguntas_Frecuentes_CommunityLab.pdf`, de Juan Sebastián Rodríguez), tal como está, y el PDF 13 (`13_Programa_del_Bootcamp_CommunityLab.pdf`), generado desde un Markdown con `fpdf2`. El índice nuevo tiene 80 fragmentos (PDF 12: 28 %; PDF 13: 6 %). 🧪 El script de revisión, que ahora revisa varios PDF y tiene la categoría "debilidad conocida", da `todo OK` en la IA real. El texto del PDF 13 tiene **una pregunta más** que la §4 de la ficha, y una pregunta del script cambió: las dos cosas las validó Harrison (sección 5).

Durante la prueba real, Gemini estuvo saturado todo el día (503 y 504 en casi todos los modelos de la cuenta gratuita), y el bot derivaba dudas que el buscador encontraba bien. Con la autorización de Harrison se agregó la **Parte D** (sección 8), fuera del alcance original: un **modelo de respaldo** (DEC-165) y **tiempos en vivo de 40/45/55 s** (DEC-166). 🧪 Con eso, y con la clave original otra vez, el bot respondió 3 de 3 dudas, en 29 a 33 s: con el tope viejo de 25 s se habrían derivado. **Lo que el orquestador tiene que tener presente está en la sección 9.**

## 2. Criterios de terminado

| Criterio | Estado | Evidencia |
|---|---|---|
| Los PDF 12 y 13 están en `pdfs/`, y el texto del 13 es el de la sección 4 | ✅ con un agregado validado | `958a432`: el PDF 12 entra con `git mv` (`rename … (100%)`). El 13 tiene el texto de la §4 **más** la pregunta "¿Qué contenido tiene el curso?" (decisión 1 de la sección 5). Prueba 1: el texto extraído es igual al `.md` |
| El índice nuevo está en git, y el script da `todo OK` con la categoría "debilidad conocida" explicada | ✅ | `96730c7`. Prueba 2 (sección 4.2), en la IA real y otra vez contra el índice de git |
| La prueba con Gemini y la prueba real dan lo esperado | ⚠️ Parcial. Gemini (prueba 3): sí, salvo "¿Qué módulos…?", sin medir por 503/504. Prueba real: "clases grabadas" (10:39) y "contenido del curso" (11:44) respondieron con su PDF; con la Parte D y la clave original, 3 de 3 respondidas (11:58 a 12:00). Las otras derivaciones del día fueron por 503, 504 o el tope, nunca por el buscador | Secciones 4.3, 7 y 8 |
| DEC-163, DEC-164, DEC-152 en ✅, ARQUITECTURA (§1 y §11), ESTADO y OPERACION al día | ✅ | Sección 3 |
| El informe está completo, y no se tocó nada fuera del alcance | ⚠️ Fuera del alcance, **con autorización** | Partes A a C: no se tocó código. La **Parte D** sí cambia código de la IA, de Java y del bot, y los valores de dos contratos: la autorizó Harrison (sección 8). No se tocaron `TOP_N_RERANK`, los umbrales, la revisión anti-alucinación, los documentos `00_…` a `11_…` ni el texto del PDF 12. No se leyó el `.env`, y ninguna clave pasó por el chat |

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
| 👤 **3. No revertir los PDF 12 y 13** (Harrison lo consideró, porque las dudas se derivaban). 🧪 Comparación sin Gemini, índice viejo (53 fragmentos) contra nuevo (80): la misma búsqueda (~170 ms), el mismo texto para Gemini (2.200 a 3.200 caracteres, siempre 3 fragmentos) y las mismas 3 llamadas por duda. Con el índice viejo, "contenido", "ciencia de datos" y "horas" iban a reglamentos que no responden | Revertir (no ahorra tiempo ni tokens, y vuelve a derivar esas preguntas) | No |
| 👤 **4. DEC-165 · Modelo de respaldo de Gemini** (`GEMINI_MODELO_RESPALDO`) para el clasificador y el Agente FAQ, no para el Agente-Mod. Autorizada por Harrison | Cambiar solo de modelo (también se saturaba); cambiar de clave (no arregla un 503: la saturación es del modelo) | No cambia el contrato. Sobre D5: un proveedor, dos modelos |
| 👤 **5. DEC-166 · Tiempos 40/45/55 s**, configurables. Autorizada por Harrison | Dejar 25/30/40 (cada llamada tardaba hasta 17 s); subir solo el de la IA (chocaba con los 30 s de Java) | **Sí cambia los contratos**, pero solo la tabla de tiempos (`JAVA_IA_v1` §6, `BOT_JAVA_v1` §7): ningún campo. D4 se mantiene (espera con "escribiendo…") |
| 👤 **6. Un solo commit para la Parte D**, como pidió Harrison | Tres commits (respaldo, tiempos, reconstrucción) | No |
| 👤 **7. Configuración del `.env` de Harrison** (no está en git): `GEMINI_MODEL=gemini-flash-lite-latest`, `GEMINI_MODELO_RESPALDO=gemini-3.5-flash`, y de nuevo la **primera clave** de Gemini. 🔎 Los valores por defecto del repositorio no cambiaron (`gemini-3.5-flash-lite`, sin respaldo) | Cambiar el valor por defecto en `compose.yml` (queda para el orquestador, sección 9) | No |
| Reintentar ante un 503 mientras quede tiempo: **propuesto, no hecho**. 2 dudas se derivaron a los 9 y 17 s, con más de 20 s libres | No se hizo: Harrison pidió cerrar T15 cuando Gemini volvió a responder con la clave original | No |

## 6. Dudas, riesgos y pendientes

- **"¿Qué computador necesito para el bootcamp?"** lleva al PDF 13, y el bot la deriva a un mentor (🧪 prueba 3). No da información falsa, pero antes se respondía. Arreglarlo de verdad exige que el PDF 12 diga "bootcamp" en esa pregunta (es de Juan Sebastián) o cambiar el reordenador: las dos cosas están fuera de esta tarea.
- **"¿Qué módulos tiene el bootcamp?" no se probó con Gemini** (503 y 504). Se puede repetir cuando Gemini tenga menos demanda, o sumarla a la prueba real.
- **El reordenador es frágil con el español** (sección 4.1): el próximo PDF puede mover preguntas que hoy pasan. Para eso está el script; las preguntas que fallen sin respaldo de una medición no deben pasar a "debilidad conocida".
- **"¿Las clases quedan grabadas?"** se responde, pero la respuesta dice que se consulte a un mentor. En el dashboard cuenta como respondida (mejora 🟡 en ESTADO).
- **ChatGPT**: la mejora (que la Política de IA diga "ChatGPT") queda en ESTADO. Cambiar un documento oficial está fuera de esta tarea.
- **La Parte D se hizo fuera del alcance de la ficha**, con autorización de Harrison: el orquestador tiene que auditarla (sección 9).
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
12. `git add …` (la documentación y este informe) y `git commit -m "docs: T15 en DECISIONES (DEC-163, DEC-164, DEC-152), ARQUITECTURA, ESTADO, OPERACION e informe"` → `774d29e`
13. Cambió `GEMINI_API_KEY` en el `.env` (una clave de otra cuenta de Google) y `docker compose up -d ia`
14. `docker compose stop bot ia`, y después `docker compose up -d ia` y `docker compose up -d bot`
15. Cambió `GEMINI_MODEL=gemini-flash-lite-latest` en el `.env` y `docker compose up -d ia`
16. `git add -A` y `git commit -m "feat: modelo de respaldo de Gemini y tiempos en vivo de 40/45/55 s (DEC-165, DEC-166), con contratos y documentacion"` → `28c7f3e`
17. Agregó `GEMINI_MODELO_RESPALDO=gemini-3.5-flash` en el `.env` y `docker compose up -d --build ia api-java bot`
18. Volvió a poner la **primera** `GEMINI_API_KEY` en el `.env` y recreó los servicios (11:57)
19. Las pruebas en `#dudas` de esta sección

### Prueba real en `#dudas`

**Primer intento (2026-10-16, 10:31 a 10:33): no sirve como prueba.** Las 4 primeras preguntas se derivaron con el mensaje genérico, incluida "¿Las clases quedan grabadas?", que una hora antes se respondía con el PDF 12. 🧪 El registro de `ia` muestra la causa: 3 mensajes agotaron el tope de 25 s esperando a Gemini ("se agotó el tope de 25 s antes de la respuesta del Agente FAQ"), y en 1 Gemini respondió `503 UNAVAILABLE` ("high demand"). Gemini estaba saturado, igual que en la prueba 3. No se llegó a comparar con los PDF. El bot hizo lo que debe hacer ante un fallo del LLM: derivar (D3).

**Resultado por pregunta** (lo que se pudo atribuir con las capturas de Harrison):

| Pregunta | El bot | Documento |
|---|---|---|
| ¿Las clases quedan grabadas? (10:39) | ✅ Responde | PDF 12, pág. 1 |
| ¿Qué contenido tiene el curso? (11:44, con la Parte D) | ✅ Responde, con los 8 módulos por período (40 s) | PDF 13, pág. 1 |
| ¿Hay una ruta de ciencia de datos? (11:45) | Deriva: `503` en los dos modelos (17 s) | — |
| ¿Cuántas horas a la semana tengo que dedicarle? (11:47) | Deriva: `503` en los dos modelos (9,6 s) | — |
| 3 dudas de Harrison, de 11:58 a 12:00, con la clave original | ✅ **3 de 3 responden** (29, 31 y 33 s), sin ningún 503 ni 504 en la IA | No queda en el registro (no guarda textos) |
| ¿Hay becas…? y ¿Qué módulos tiene el bootcamp? | **No probadas** en vivo con Gemini funcionando | — |

**Todos los intentos del 2026-10-16**, con lo que dicen los registros de `ia`, Java y el bot (los registros no guardan el texto de las preguntas, por diseño):

| Hora | Clave y modelo | Qué pasó |
|---|---|---|
| 10:39 | Clave original, `gemini-3.5-flash-lite` | ✅ "¿Las clases quedan grabadas?" se respondió con el PDF 12, pág. 1 |
| 10:40 | Ídem | Las 5 preguntas en **un solo mensaje**: deriva (es lo esperado: no hay un fragmento que responda las 5) |
| 10:41 | Ídem | 2 mensajes: los dos agotaron el tope de 25 s (cada llamada tardó unos 10 s) |
| 11:09 | Clave de otra cuenta de Google, mismo modelo | Clasificar ✅ (7 s), responder ✅ (4 s), revisar ❌ `503` |
| 11:20 | Clave nueva, `gemini-flash-lite-latest` | Agotó el tope de 25 s |
| 11:24 | Ídem | Clasificar: `503`, reintento; agotó el tope (25,1 s en Java). Después, la respuesta también dio `503` |
| 11:44 a 11:48 | Ídem, **con la Parte D** (respaldo `gemini-3.5-flash`, tope 40 s) | "Contenido del curso" ✅ (40 s). "Ciencia de datos" y "horas": `503` en los dos modelos (17 y 9,6 s). Otra duda: `504` al clasificar y tope de 40 s |
| 11:58 a 12:00 | **Primera clave** otra vez, con la Parte D | ✅ 3 de 3 responden (29, 31 y 33 s), sin errores en la IA |

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
| Prueba real en `#dudas`, después de reconstruir | ✅ "Contenido del curso" respondió en 40 s (11:44); 2 dudas derivaron por 503 en los dos modelos. Con la clave original, 3 de 3 respondidas en 29 a 33 s (sección 7) |

**Lo que no se puede garantizar:** si Google rechaza a la cuenta gratuita en todos los modelos a la vez, el bot deriva (D3). Para la demo se recomienda una clave con facturación (ESTADO §3, punto 7).

## 9. Para el orquestador: lo que hay que tener presente

| # | Tema | Qué saber | Qué hacer |
|---|---|---|---|
| 1 | **La Parte D está fuera del alcance de la ficha** | La autorizó Harrison el 2026-10-16 para la demo. Toca código de la IA (`llm_models.py` de las dos piezas, `config.py`, `etiquetador.py`), de Java (`RestClientConfig`, `application.properties`) y del bot (`TIEMPO_JAVA_S`). Las pruebas pasan: IA 86, bot 22, Java 256 | Auditar la sección 8 y el commit `28c7f3e` |
| 2 | **Cambian dos contratos, solo en sus tiempos** | `JAVA_IA_v1` §6 y `BOT_JAVA_v1` §7: 40/45/55 s en lugar de 25/30/40. Ningún campo, orden ni error cambió. Cada contrato tiene su nota del cambio | Avisar al equipo de Java y del bot; nada que migrar |
| 3 | **El orden de los tiempos es una regla** | Tope de la IA (`TIEMPO_REAL_TOPE_S`) < Java → IA (`IA_TIEMPO_LECTURA_S`) < bot → Java (`TIEMPO_JAVA_S`). Si alguien sube uno solo, Java o el bot cortan antes de que llegue la respuesta | Revisarlo en cualquier PR que toque esas variables (`.env.example` lo explica) |
| 4 | **Gemini gratis no es confiable para la demo** | El 2026-10-16, Google rechazó con 503 casi todos los modelos de la cuenta gratuita durante horas, incluso con claves de otras cuentas. Con Gemini respondiendo, una duda tarda **29 a 40 s** (3 llamadas) | Decidir antes de la demo: clave **con facturación** (centavos por duda, con prioridad en Google) o ensayo el mismo día. ESTADO §3, punto 7, y OPERACION §15 |
| 5 | **El `.env` de Harrison no es igual al valor por defecto del repositorio** | Su `.env`: `GEMINI_MODEL=gemini-flash-lite-latest` y `GEMINI_MODELO_RESPALDO=gemini-3.5-flash`. El repositorio sigue con `gemini-3.5-flash-lite` y sin respaldo. `-latest` es un alias: Google puede cambiar el modelo que hay detrás | Decidir si `compose.yml` y `.env.example` adoptan un respaldo por defecto, y elegir el modelo de la demo midiendo (OPERACION §15) |
| 6 | **El respaldo no cubre al Agente-Mod** | Los borradores y la FAQ semanal usan un solo modelo: si falla, Java reintenta en la vuelta siguiente | Nada, salvo que se quiera extenderlo |
| 7 | **Mejora propuesta y no hecha: reintentar ante un 503 mientras quede tiempo** | 2 dudas se derivaron a los 9 y 17 s, con más de 20 s libres. Un 503 no se cobra | Evaluarla si la demo sigue con la cuenta gratuita |
| 8 | **Los PDF 12 y 13 no causan gasto ni demora** | Medido sin Gemini: misma búsqueda (~170 ms), mismo tamaño de texto para Gemini, mismas 3 llamadas por duda (decisión 3 de la sección 5) | Si alguien propone revertirlos por lentitud, mostrar esta medición |
| 9 | **Falta probar en vivo** | "¿Hay becas…?" y "¿Qué módulos tiene el bootcamp?" no se probaron en vivo con Gemini funcionando; tampoco "computador para el bootcamp" | Sumarlas al ensayo de la demo |
| 10 | **Consumo de Gemini durante T15** | Unos 68 intentos en la prueba 3, unos 15 en mediciones de modelos y diagnóstico (casi todos con muy pocos tokens), y las pruebas en vivo de Harrison. Una duda completa usa unos 2.400 tokens de entrada y 320 de salida | — |
