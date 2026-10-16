# T15 · Dos PDF nuevos para el bot: preguntas frecuentes y programa del bootcamp

> Esta ficha **sí es la orden de trabajo vigente** de T15, aunque viva en `docs/historico/tareas/`. Para todo lo demás manda [AGENTS.md](../../../AGENTS.md).

| Dato | Valor |
|---|---|
| Objetivo | **OE4** (el bot responde dudas con los PDF). Cierra ESTADO §3, punto 6, y DEC-152 |
| Tamaño | S: dos PDF, el índice del buscador, el script de revisión y la documentación. **No cambia código del bot, ni contratos, ni la arquitectura** |
| Modelo de Claude recomendado | **Sonnet 5.5** |
| Depende de | DEC-152 y el PDF de Juan Sebastián Rodríguez (`3c8768a`, 2026-10-15) |
| Rama | `tarea/T15-pdf-preguntas-frecuentes` (ya creada desde `main`; esta ficha es su primer commit) |
| Decisiones previas 👤 | Las de la sección 1.1, validadas por Harrison el 2026-10-16 |

## 1. Objetivo

Que el bot responda dos tipos de dudas que hoy deriva a un mentor:
- las **generales** (clases grabadas, estudiar trabajando, qué computador hace falta, qué es una API…), con el PDF que escribió Juan Sebastián: `12_Preguntas_Frecuentes_CommunityLab.pdf`;
- las del **contenido del programa** ("¿qué contenido tiene el curso?", "¿hay una ruta de ciencia de datos?"), con un PDF nuevo y corto: `13_Programa_del_Bootcamp_CommunityLab.pdf`, con el texto de la sección 4.

🔎 **Por qué hace falta el PDF 13:** los documentos oficiales (`00_…` a `11_…`) fijan el marco (dos períodos al año, inducción, semanas, asignaturas, créditos), pero **ninguno dice qué se estudia**. Tampoco el brief. En la prueba en vivo, "¿Qué contenido tiene el curso?" se derivó, y "¿Qué cursos ofrecen para ciencia de datos?" se respondió con definiciones generales.

### 1.1 Decisiones previas 👤 (2026-10-16)

| # | Decisión | Detalle |
|---|---|---|
| 1 | **Integrar el PDF 12 tal como está** | Con 3 fragmentos, como hoy (`TOP_N_RERANK` no cambia). El balance medido (sección 2): gana 4 respuestas, deja de dar una respuesta engañosa (LinkedIn) y pierde una (ChatGPT, que pasa a derivarse a un mentor). Derivar nunca da información falsa (D3) |
| 2 | **Crear el PDF 13**, de 2 o 3 páginas | Con el texto de la sección 4, sin cambiarle el contenido. No habla de notas, becas, inscripción ni fechas, para no tapar a los documentos oficiales |
| 3 | El manual original se queda | `Manual_Maestro_Servicio_Cliente_Universidad_Programacion.pdf` sigue en `pdfs_en_revision/`, donde la IA no lo lee. Es de Juan Sebastián: no se borra |
| 4 | Créditos | El PDF 12 es de Juan Sebastián Rodríguez. El PDF 13 lo redactaron Harrison Tutalcha y el orquestador (asistencia de IA) |

La tarea suma a [DECISIONES.md](../../DECISIONES.md):
- **DEC-163:** entran los PDF 12 y 13, con su balance medido (decisiones 1 y 2);
- **DEC-164:** el script de revisión tiene una categoría **"debilidad conocida"** (punto 5 de la sección 3);
- **DEC-152** pasa a ✅, con el resultado.

## 2. Lo que ya se probó (2026-10-15 y 16, por el orquestador y Harrison)

Todas las pruebas aisladas se hicieron en contenedores desechables de la imagen `ia`, con una **copia** de los PDF en una carpeta temporal: no tocaron la IA del bot, el índice del repositorio, la base ni Discord.

**2.1 · El script, sin Gemini** (`revisar_buscador_faq.py`). Con el PDF 12, el índice tiene 75 fragmentos, 22 del PDF 12 (**29 %**, dentro del tope de 35 %). Las 4 preguntas "nuevas" las gana el PDF 12, y becas, inicio de clases, apelaciones y extensión siguen ganándolas los oficiales. Hay **3 fallas**: nota final, ChatGPT y LinkedIn. Pero **ya eran débiles antes**: sin el PDF 12, los oficiales las ganaban con puntajes negativos (−7,3, −6,4 y −4,9), o sea con fragmentos que casi no tienen relación. Para ChatGPT, además, ganaba el Reglamento de Comunicaciones: la Política de IA (`04_…`) se lee bien (4 fragmentos), pero no dice "ChatGPT", y el buscador no la relaciona.

**2.2 · Qué responde de verdad el bot (con Gemini).** El puntaje del buscador solo elige los 3 fragmentos que lee Gemini; después, Gemini responde o deriva, y una segunda revisión descarta lo inventado.

| Pregunta | Hoy (solo oficiales) | Con el PDF 12 |
|---|---|---|
| Becas, inicio de clases, apelaciones, extensión por enfermedad | Responde | Responde, igual |
| ¿Cómo se calcula la nota final? | Deriva | Deriva |
| ¿Puedo usar ChatGPT para mis entregas? | Responde bien (Código de Honor, Reglamento de Comunicaciones, pág. 2) | ❌ Deriva |
| ¿Pueden publicar mi nombre en LinkedIn? | Responde **mal**: cita la regla de doxxing, que es sobre datos de otros | Deriva, y explica que el reglamento no lo cubre |
| Clases grabadas, estudiar trabajando, computador, API | Deriva | ✅ Responde (medido con 5 fragmentos; ver 2.3) |

**2.3 · Lo que no sirvió.**
- Pasar de 3 a 5 fragmentos (`TOP_N_RERANK`) dio los mismos resultados.
- Quitar del PDF 12 las págs. 6 (IA), 8 (empleo) o 5 (Git) tampoco: para ChatGPT, el primer lugar sigue siendo la pág. 1 ("Empezar en CommunityLab"). Esa página junta seis preguntas generales y se parece un poco a cualquier duda sobre el bootcamp, pero tiene 3 de las 4 respuestas que se buscan.

En total se gastaron unas 46 llamadas a Gemini.

**2.4 · Prueba en vivo en Discord** (Harrison, 2026-10-15, con el PDF 12 en la IA del bot y el índice rehecho):

| Mensaje | Pregunta | El bot | Documento |
|---|---|---|---|
| 258 | ¿Cuándo inician las clases? | Responde | Calendario Académico |
| 259 | ¿Qué contenido tiene el curso? | **Deriva** | — |
| 260 | ¿Cuál es el contenido del bootcamp? | Responde, pero solo con "es un bootcamp de programación" | PDF 12, pág. 1 |
| 261 | ¿Cuáles son las reglas de la comunidad? | Responde | Reglamento de Comunicaciones |
| 262 | ¿Qué cursos ofrecen para ciencia de datos? | Responde, con definiciones generales y no con cursos | PDF 12, pág. 6 |
| 263 | Nunca he programado, ¿puedo empezar desde cero? | Responde | PDF 12, pág. 1 |
| 264 | ¿Qué computador necesito para empezar? | Responde | PDF 12, pág. 1 |

Harrison también revisó el panel: todo funciona.

**Estado en el que queda la PC de Harrison** (al empezar esta tarea): en la rama, `agents/agent_faq/data/pdfs/12_…pdf` está copiado y `faiss_pdfs/` figura como borrado en `git status`. La IA del bot tiene un índice con el PDF 12. La tarea lo rehace con los dos PDF.

## 3. Alcance: qué entra

1. **PDF 12:** pasa a `agents/agent_faq/data/pdfs/` (`git mv` desde `pdfs_en_revision/`, para que conste que es el mismo archivo).
2. **PDF 13:** generarlo con el texto de la sección 4, **sin cambiar el contenido**:
   - fuente del texto: `scripts/pdf_programa/13_Programa_del_Bootcamp_CommunityLab.md`;
   - generador: `scripts/pdf_programa/generar.py`, con una librería de PDF de versión fija (por ejemplo, `fpdf2`), corrido en un contenedor desechable de Python, sin instalar nada en Windows;
   - formato parecido al PDF 12: el título, una línea de introducción, títulos de sección y cada pregunta en negrita con su respuesta debajo. Sin tablas;
   - 🔎 tildes, `¿` y `·` tienen que verse y **extraerse bien** con `pypdf` (el lector del Agente FAQ). Comprobarlo antes de seguir. Con una fuente que no sea Unicode, evita los caracteres fuera de latin-1 (raya larga, emojis);
   - guardarlo como `agents/agent_faq/data/pdfs/13_Programa_del_Bootcamp_CommunityLab.pdf`.
3. **Índice:** rehacerlo con los dos PDF ([OPERACION.md §14](../../OPERACION.md)): borrar `faiss_pdfs/`, `docker compose up -d --no-deps --build ia`, esperar `(healthy)` y copiarlo al repositorio con `docker compose cp`. Se guarda con `git add -f`, porque el `.gitignore` ignora `agents/*/data/`. Los comandos que cambian la IA los corre Harrison.
4. **Script `scripts/revisar_buscador_faq.py`:**
   - acepta **varios PDF nuevos** (12 y 13), y revisa el tope de 35 % **por cada uno**, mostrando también el total;
   - suma estas preguntas para el PDF 13 (primer lugar esperado: `13_…`): "¿Qué contenido tiene el curso?", "¿Qué módulos tiene el bootcamp?", "¿Hay una ruta de ciencia de datos?" y "¿Cuántas horas a la semana tengo que dedicarle?";
   - suma la pregunta oficial "¿Cuándo empiezan las clases del próximo período?" (ya está) **y** "¿Cuánto dura un período académico?", que debe seguir ganándola el Calendario.
5. **Categoría "debilidad conocida" en el script:** nota final, ChatGPT y LinkedIn se muestran con su resultado y **un motivo escrito** (el de la sección 2.1), pero no cuentan como falla. Las otras preguntas oficiales siguen siendo obligatorias. Así el script vuelve a servir para el próximo PDF. **No se relaja ninguna otra regla.**
6. **`pdfs_en_revision/README.md`:** el estado (el PDF 12 salió de ahí y entró, con su resultado; el manual se queda en revisión).

### Parte C · La documentación

7. DECISIONES.md: DEC-163, DEC-164 y DEC-152 en ✅.
8. ARQUITECTURA.md: §1 (los documentos de CommunityLab ahora incluyen preguntas frecuentes y el programa) y §11 (una fila de créditos para los dos PDF, decisión 4).
9. ESTADO.md:
   - §3, punto 6, ✅;
   - dos mejoras 🟡 nuevas: que la Política de IA diga "ChatGPT" con todas sus letras, para que el buscador la encuentre, y que "¿las clases quedan grabadas?" cuenta como **respondida** en el dashboard aunque mande a un mentor;
   - §5: las filas de `tarea/T13-borradores` (`a224e58`, fusionada por el PR #17 y borrada el 2026-10-15) y de esta rama.
10. OPERACION.md §14: el script revisa varios PDF y tiene la categoría "debilidad conocida".

## 4. El texto del PDF 13 (validado por Harrison)

> **Archivo:** `13_Programa_del_Bootcamp_CommunityLab.pdf` · **Encabezado de página:** "COMMUNITYLAB · PROGRAMA DEL BOOTCAMP" · **Pie:** "Programa del bootcamp · Página N"

**Programa del bootcamp de CommunityLab**

Qué se estudia en el bootcamp de Desarrollo de Software de CommunityLab, módulo por módulo. Las fechas de cada período están en el Calendario Académico, y la forma de evaluar, en la Política de Evaluación.

**El programa**

**¿Qué programa ofrece CommunityLab?**
CommunityLab ofrece un bootcamp virtual de Desarrollo de Software. Prepara a personas que empiezan desde cero para trabajar como desarrolladoras junior, con una base en datos.

**¿Cuánto dura el bootcamp?**
Dura un año académico: dos períodos, el Período I y el Período II, con cuatro módulos en cada uno.

**¿Cómo está organizado el bootcamp?**
En ocho módulos, uno detrás de otro. Cada módulo es una asignatura del período y termina con un ejercicio práctico.

**¿Cuántas horas a la semana hay que dedicarle?**
Se sugieren entre 15 y 20 horas semanales, entre clases en vivo, ejercicios y proyectos.

**Período I · Fundamentos**

**Módulo 1 · ¿Qué se ve en Fundamentos de programación con Python?**
Lógica de programación, variables, condiciones, ciclos, funciones y listas, con ejercicios en Python. Es el punto de partida para quienes nunca programaron.

**Módulo 2 · ¿Qué se ve en Git y GitHub?**
Control de versiones: repositorios, commits, ramas, pull requests y trabajo en equipo sobre un mismo proyecto.

**Módulo 3 · ¿Qué se ve en Bases de datos y SQL?**
El modelo relacional, tablas, claves y consultas SQL para guardar y consultar información, con PostgreSQL.

**Módulo 4 · ¿Qué es el Proyecto integrador I?**
Un proyecto en equipo que une lo visto en el Período I: un programa en Python que guarda sus datos en una base de datos y se publica en GitHub.

**Período II · Desarrollo web y datos**

**Módulo 5 · ¿Qué se ve en Frontend?**
HTML, CSS y JavaScript para construir páginas web que se ven bien en el celular y en el computador.

**Módulo 6 · ¿Qué se ve en Backend y APIs con Java?**
Java y Spring Boot para crear APIs que conectan una página web con una base de datos.

**Módulo 7 · ¿Qué se ve en Introducción a datos e IA?**
Análisis de datos con Python y una primera mirada a machine learning, con ejemplos pequeños.

**Módulo 8 · ¿Qué es el Proyecto final y empleabilidad?**
Un proyecto completo en equipo, con frontend, backend y base de datos, que se presenta ante los mentores. Incluye la preparación para buscar trabajo: portafolio, hoja de vida y entrevistas técnicas.

**Otras dudas sobre el programa**

**¿Hay una ruta o un curso de ciencia de datos?**
No como programa aparte. El bootcamp es de Desarrollo de Software, y el Módulo 7 es una introducción a datos e IA para seguir aprendiendo después.

**¿Qué herramientas se usan en el bootcamp?**
Python, Git y GitHub, PostgreSQL, Visual Studio Code, Java con Spring Boot, HTML, CSS y JavaScript. La comunidad se reúne en Discord.

## 5. Fuera de alcance

- Cambiar el código del Agente FAQ, el bot, `TOP_N_RERANK`, el reordenador o los umbrales. Cambiar los documentos oficiales `00_…` a `11_…` (la mejora de "ChatGPT" en la Política de IA queda en ESTADO).
- Cambiar el texto del PDF 13 o del PDF 12. Si una prueba falla por el texto, se informa y lo decide Harrison.
- **No ejecutar `simulate_students.py`** ni encender un segundo bot. **Nunca** leer ni mostrar el `.env`.

## 6. Pruebas exigidas

| # | Prueba | Resultado esperado |
|---|---|---|
| 1 | El texto del PDF 13 extraído con `pypdf` | Igual al de la sección 4: tildes y signos bien, sin palabras pegadas |
| 2 | `revisar_buscador_faq.py` dentro de `ia`, con el índice nuevo | **`Resultado: todo OK`**: cada PDF nuevo con ≤ 35 % del índice; las oficiales obligatorias, con un oficial en el primer lugar; las del 12 y del 13, con su PDF primero; las 3 "debilidades conocidas", mostradas con su motivo |
| 3 | Las mismas preguntas con Gemini, en un contenedor aparte como en la sección 2 (avisar el costo antes: unas 35 llamadas) | Ninguna pregunta peor que en la tabla 2.2; las 4 del PDF 12 y las 4 del PDF 13 responden con su PDF |
| 4 | `python -m pytest agents/orquestador/tests -q` | Siguen pasando |

**Prueba real, la corre Harrison** (gasta unas 3 llamadas a Gemini por pregunta): con la IA rehecha, en `#dudas`, una pregunta a la vez: "¿Qué contenido tiene el curso?", "¿Hay una ruta de ciencia de datos?", "¿Cuántas horas a la semana tengo que dedicarle?", "¿Las clases quedan grabadas?" y "¿Hay becas y cuáles son los requisitos?". Las cinco deben responderse, cada una con su documento.

## 7. Criterios de terminado

- [ ] Los PDF 12 y 13 están en `pdfs/`, y el texto del 13 es el de la sección 4.
- [ ] El índice nuevo está en git, y el script da `todo OK` con la categoría "debilidad conocida" explicada.
- [ ] La prueba con Gemini y la prueba real dan lo esperado (🧪 en el informe, con las tablas).
- [ ] DEC-163, DEC-164, DEC-152 en ✅, ARQUITECTURA (§1 y §11), ESTADO y OPERACION al día.
- [ ] El informe `docs/historico/tareas/T15-informe.md` está completo ([plantilla](PLANTILLA_INFORME.md)), y no se tocó nada fuera del alcance.

## 8. Git

La rama `tarea/T15-pdf-preguntas-frecuentes` ya existe, y esta ficha es su primer commit. El chat de tarea **no** ejecuta comandos de git que cambian algo, ni los que reconstruyen la IA: se los da a Harrison **uno por línea**, con la carpeta y lo que debería ver. Commits con un solo `-m` y **sin** `Co-Authored-By` (DEC-65), comprobando cada uno con `git log --oneline -3`. Al final, `git push` y avisarle al orquestador **"T15 terminó"**.

## 9. Cómo abrir el chat de esta tarea

1. En VS Code, abrir un chat nuevo de Claude Code **en esta misma carpeta**, con la rama `tarea/T15-pdf-preguntas-frecuentes` activa.
2. Elegir **Sonnet 5.5** con `/model`.
3. Primer mensaje: *"Eres el chat de la tarea T15. Lee AGENTS.md y docs/historico/tareas/T15-pdf-preguntas-frecuentes.md completos, y empieza. Respóndeme en español y dame los comandos de git uno por línea."*

⚠️ **Nunca pegues el contenido de un `.env`, un token ni tu contraseña del panel en el chat.**
