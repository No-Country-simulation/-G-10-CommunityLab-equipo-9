# PDF en revisión: el manual de servicio al cliente

> **Qué es esta carpeta:** documentos que todavía **no** usa el bot. La IA solo lee `agents/agent_faq/data/pdfs/*.pdf`; lo que está aquí no entra al índice de búsqueda.
> **Decisión:** DEC-152 · **Autor del manual:** Juan Sebastián Rodríguez · **Revisado:** 2026-10-14

## 1. Por qué está aquí y no en `pdfs/`

`Manual_Maestro_Servicio_Cliente_Universidad_Programacion.pdf` (22 páginas) es un buen banco de preguntas, pero se probó en el buscador del Agente FAQ y, **tal como está, hace que el bot responda peor**:

| Hallazgo | Detalle |
|---|---|
| Tapa a los documentos oficiales | Ocupa 64 de los 117 fragmentos del índice (55 %). En "¿Hay becas…?", "¿Puedo usar ChatGPT…?" y "¿Pueden publicar mi nombre en LinkedIn?", el primer lugar pasa a ser del manual (respuestas genéricas como "depende…") en lugar de la Política de Becas, la Política de IA o el Reglamento de Comunicaciones |
| Instrucciones para un chatbot dentro del contenido | Las secciones 1 y 21 a 28 explican cómo diseñar un chatbot (intenciones, plantillas, checklists). No son información para alumnos, pero el buscador las devuelve como respuesta (por ejemplo, la pág. 19) |
| Nombre de la institución | Dice "InsightEdu" (9 páginas). InsightEdu es el nombre de **nuestro sistema**; la institución es **CommunityLab** |
| Otro tipo de institución | Habla de universidad: carreras, semestres, homologación, títulos profesionales. CommunityLab es un **bootcamp** |

Lo bueno: responde preguntas que hoy el bot no puede responder y deriva a un mentor ("¿Las clases quedan grabadas?", "¿Puedo estudiar si trabajo?", preguntas técnicas como "¿Qué es una API?").

## 2. Qué hay que cambiar (instrucciones exactas)

El objetivo es un PDF **corto**, solo con lo que los documentos oficiales (`00_…` a `11_…`) **no** cubren.

**Nombre del archivo nuevo:** `12_Preguntas_Frecuentes_CommunityLab.pdf` (sigue la numeración de `pdfs/`).
**Título:** "Preguntas frecuentes de CommunityLab".

### 2.1 Quitar por completo

| Secciones del manual | Por qué |
|---|---|
| 1. Reglas de uso del manual | Son instrucciones para el agente, no respuestas |
| 21 a 28 (preguntas difíciles, catálogo de temas, plantillas de respuesta, checklist, arquitectura de conocimiento 26.1 a 26.9, la lista de 9 pasos, plantilla maestra y checklist del chatbot) | Lo mismo: explican cómo construir un chatbot. Si alguna pregunta de la sección 21 sirve para alumnos, pásala a la sección que corresponda con su respuesta |
| 3. Admisiones e inscripción | Habla de admisiones universitarias. Si CommunityLab necesita algo de inscripción, va según el Reglamento Académico |
| 4. Costos, matrícula y pagos | Lo responde la **Política de Becas** (`09_…`). Una respuesta genérica ("depende") la tapa |
| 17. Preguntas sobre materias y plan de estudios | Semestres, créditos y asignaturas: es de universidad |
| Cualquier pregunta sobre becas, evaluación y notas, apelaciones, uso de IA, publicación de nombres o fotos, calendario y circunstancias excepcionales | Ya están en los documentos oficiales `00_…` a `11_…`. Si se repiten aquí, el buscador puede elegir la versión genérica |

### 2.2 Adaptar

| Qué | Cómo |
|---|---|
| "InsightEdu" | Cambiarlo por **"CommunityLab"** en todo el documento. Al final no debe aparecer ni una vez |
| "universidad", "carrera", "semestre", "matrícula" | Cambiarlos por **"bootcamp"**, **"programa"**, **"módulo"** e **"inscripción"**, o quitar la pregunta si deja de tener sentido |
| 2. Información general | Dejar 3 o 4 preguntas: qué es CommunityLab (un bootcamp de programación), si se puede empezar sin experiencia y si hacen falta matemáticas |
| Respuestas que dicen "depende" o "debe confirmarse con Admisiones" | Si un documento oficial tiene la respuesta, quitar la pregunta. Si no, dejar una respuesta concreta, o indicar que la duda va a un mentor en `#dudas` |

### 2.3 Conservar (adaptadas)

5 (modalidades y experiencia de estudio), 6 (programación desde cero), 7 a 15 (Python, Java, JavaScript, bases de datos, Git, IA y ciencia de datos, ciberseguridad, arquitectura, DevOps), 16 (empleabilidad), 18 (soporte académico, sin repetir el Manual del Estudiante), 19 (tecnología y herramientas), 20 (orientación) y 24 (glosario).

### 2.4 Formato

- Una pregunta en **negrita** y su respuesta debajo, en un párrafo.
- Sin tablas ni listas de intenciones.
- Que sea corto: la prueba exige que el PDF ocupe **como máximo el 35 % del índice**. 🔎 Con los documentos oficiales actuales, eso es más o menos **8 a 10 páginas**.

## 3. Cómo probarlo (sin gastar Gemini)

Desde la raíz del repositorio, en PowerShell, con Docker encendido (`docker compose up -d`):

| Paso | Comando o acción | Qué debería pasar |
|---|---|---|
| 1 | Guardar el PDF corregido como `agents/agent_faq/data/pdfs/12_Preguntas_Frecuentes_CommunityLab.pdf` y dejar este manual en esta carpeta | — |
| 2 | `Remove-Item -Recurse -Force agents\agent_faq\data\vectorstore\faiss_pdfs` | Borra el índice viejo. La IA lo vuelve a armar al arrancar, ya con el PDF nuevo |
| 3 | `docker compose up -d --no-deps --build ia` | Reconstruye la IA. Esperar a que `docker compose ps` muestre `ia` como `(healthy)` (1 o 2 minutos) |
| 4 | `docker compose cp scripts/revisar_buscador_faq.py ia:/tmp/revisar_buscador_faq.py` | Copia el script de revisión dentro de la IA |
| 5 | `docker compose exec -e PYTHONIOENCODING=utf-8 ia python /tmp/revisar_buscador_faq.py` | Debe terminar con **`Resultado: todo OK`** |
| 6 | `python -m pytest agents/orquestador/tests -q` | Las pruebas de la IA siguen pasando |

**Qué revisa el script** (`scripts/revisar_buscador_faq.py`):

| Tipo | Preguntas | Debe cumplir |
|---|---|---|
| `oficial` | Becas, inicio de clases, nota final, uso de ChatGPT, apelaciones, extensión por enfermedad y publicación del nombre en LinkedIn | El primer resultado es un documento oficial (`00_…` a `11_…`) |
| `nuevo` | Clases grabadas, estudiar trabajando, qué computador hace falta y qué es una API | El primer resultado es `12_Preguntas_Frecuentes_CommunityLab.pdf` |
| Tamaño | — | El PDF nuevo ocupa como máximo el 35 % de los fragmentos del índice |

Si algo falla, el script muestra los 3 documentos que encontró para cada pregunta: eso dice qué sección del PDF hay que quitar o reforzar.

**Resultado con el manual original (2026-10-14):** 7 fallas. Las 3 preguntas oficiales de becas, ChatGPT y LinkedIn las ganaba el manual, y las 4 de "nuevo" fallaban porque ese PDF todavía no existía.

## 4. Cuando todo dé OK

1. El índice se guarda en git (`agents/agent_faq/data/vectorstore/faiss_pdfs/`). Para llevar el índice nuevo al repositorio, copiarlo desde la IA:
   `docker compose cp ia:/app/agents/agent_faq/data/vectorstore/faiss_pdfs agents/agent_faq/data/vectorstore/`
2. Mover este manual fuera del bot de forma definitiva (o borrarlo, ya que queda en el historial de git) y actualizar DEC-152 en `docs/DECISIONES.md` con el resultado.
3. Abrir un Pull Request a `main` con el PDF nuevo, el índice y la salida del script.
