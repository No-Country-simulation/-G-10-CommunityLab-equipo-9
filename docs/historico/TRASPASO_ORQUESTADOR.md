# Traspaso al chat orquestador (2026-10-15)

> Para el chat de Claude que toma el rol de **orquestador** de InsightEdu Lab: guía, escribe las fichas y revisa lo que entregan los chats de tarea. Lo escribió el orquestador anterior al llenarse su contexto.
> Se lee **después** de [AGENTS.md](../../AGENTS.md), [ESTADO.md](../ESTADO.md), [DECISIONES.md](../DECISIONES.md) y [ARQUITECTURA.md](../ARQUITECTURA.md). El método detallado (cómo escribir una ficha y cómo revisar) sigue en [CHAT_PRINCIPAL.md](CHAT_PRINCIPAL.md), con los cambios de la sección 2 de este documento.

## 1. Primeros pasos

1. Leer los documentos de arriba, este traspaso completo y [diseno/README.md](diseno/README.md).
2. Comprobar el estado con comandos de solo lectura: `git fetch`, `git status -sb`, `git log --oneline -5` y `docker compose ps`.
3. **Primera tarea:** escribir la ficha de **T13 (Borradores)** en la rama `tarea/T13-borradores`, que ya existe (sección 5).

## 2. Cómo se trabaja hoy

| Tema | Regla |
|---|---|
| Roles | **Orquestador:** escribe la ficha, plantea las decisiones a Harrison con una opción recomendada y revisa la entrega. **Chat de tarea:** ejecuta una ficha y entrega un informe. **Harrison:** decide y corre los comandos de git |
| Ramas | `main` es del equipo: nunca un commit directo. **Una rama y un PR por tarea** (`tarea/T13-…`), y la ficha es el primer commit de esa rama. Las ramas ajenas no se tocan (DEC-148). `main` no está protegida en GitHub y el equipo decidió no protegerla: no insistir |
| Git | El orquestador corre solo comandos de lectura. Los que cambian algo se los da a Harrison **uno por línea**, con la carpeta y lo que debería ver; un solo `-m` y **sin** `Co-Authored-By` |
| Respuestas | En español, con el formato **Dónde estamos · Qué necesito de ti · propuesta con su motivo · 📘 💻 🧪 🔎 · Próxima acción**. Harrison es ingeniero de datos (nivel training) y analista: explicar el UX/UI y la analítica con tablas y en simple |
| Fusionar un PR | ⚠️ `gh pr merge N --merge` **y comprobar que diga `Merged`** antes de borrar la rama. El 2026-10-15 se borró la rama de T12 antes de fusionar: GitHub cerró el PR #15 sin fusionarlo, y se recuperó desde `refs/pull/15/head` |
| Documentos temporales | Harrison prefiere documentos temporales (Claude Docs) para el trabajo de análisis que después se filtra, sin crear ramas para eso |

## 3. Estado al 2026-10-15

| Qué | Estado |
|---|---|
| `main` | `89a7cb0`. PR #11 (OE7, DEC-144 y DEC-148), #12 (de Juan Sebastián), #13 (LinkedIn), #14 (ESTADO) y #15 (T12) fusionados |
| LinkedIn | Integrado y **apagado por defecto** (DEC-149 a DEC-151). Se probó de verdad el 2026-10-13 en el perfil de Gabriel (borrador 14). Para la demo: [OPERACION.md §13](../OPERACION.md). Hubo dos tokens pegados en el chat: **nunca repetirlos** |
| Manual de servicio al cliente | En `agents/agent_faq/data/pdfs_en_revision/` (DEC-152): empeoraba el buscador. Juan Sebastián tiene las instrucciones para hacer un PDF corto, y `scripts/revisar_buscador_faq.py` lo prueba sin gastar Gemini. El índice `faiss_pdfs` **está en git** (`agents/*/data/` está en el `.gitignore`: usar `git add -f`) |
| T12 · Dashboard | ✅ Fusionada. Dos vistas (Comunidad para el CM y Contenido para Marketing), 23 KPI, franja de valor, tema claro y oscuro. DEC-153 a DEC-158. Java 243 pruebas y panel 63 |
| T10 · Despliegue | ⏸️ En pausa (DEC-141). La demo sería en una PC local |
| Datos | Los del servidor de pruebas, con alumnos simulados: unos 67 mensajes en 3 semanas. **Nunca** correr `simulate_students.py` |

## 4. Decisiones del panel (2026-10-14) que siguen vigentes

| Tema | Decisión |
|---|---|
| Usuarios | Marketing y el Community Manager |
| Caso de éxito | Se mantiene, **en la misma tarjeta que el post**, con un solo consentimiento |
| Ingesta | Opción A: automática cada hora, con el aviso "Datos al día" en la barra lateral (T14) |
| Orden | T12 ✅ → **T13 Borradores** → **T14 Ingesta**, una rama y un PR cada una |
| Mejoras de ESTADO §3 | En T12 ya entraron el tiempo de revisión y la frustración por período. **En T13:** mantener la sesión al recargar la página y un botón para reintentar la FAQ en `ERROR` |
| KPIs | La base es la "validación de mercado" del brief oficial. El catálogo temporal está en [este documento](https://claude.ai/code/artifact/941dd953-84c3-4100-9697-cfc67b6e0bb0); lo elegido ya está copiado en la ficha de T12. **M12, publicados en LinkedIn, va en T13** |
| P1 | Las horas ahorradas son una **estimación** (30 min por historia) y el panel lo dice |

## 5. Lo que queda

| Tarea | Qué | Puntos que no se pueden olvidar |
|---|---|---|
| **T13 · Borradores** (20 y 21 oct) | La pantalla de [diseno/borradores.dc.html](diseno/borradores.dc.html): cola de tarjetas por logro, pestañas post y caso de éxito con su destino, contador, un solo consentimiento, copiar, rechazar y aprobar | **Reutilizar los componentes de T12** ([diseno/README.md §3](diseno/README.md)), moviéndolos a un módulo común. **M12:** migración `V9` para guardar si cada post se publicó en LinkedIn, más una DEC que reemplaza a DEC-151 y la columna "En LinkedIn" del dashboard. La sesión al recargar. El reintento de la FAQ en `ERROR`. El título del panel en la barra lateral (informe de T12 §6.3). Capturas en claro y en oscuro antes de terminar |
| **T14 · Ingesta** (22 y 23 oct) | La ingesta como servicio de Docker que corre sola cada hora, y el aviso "Datos al día · hace N min" en la barra lateral, con una puerta de solo lectura en Java (la hora del último lote) | Cambia la arquitectura (la ingesta deja de ser manual): actualizar ARQUITECTURA. Se reutiliza en T10 si se retoma |
| **Ensayo de la demo** (24 y 25 oct) | Encender LinkedIn ([OPERACION.md §13](../OPERACION.md)), el guion y el ensayo | ESTADO §3, puntos 5 y 6 |

**Entrega final: 2026-10-26.**

## 6. Lecciones y trampas de esta etapa

| Tema | Lección |
|---|---|
| **El diseño** | Los chats de tarea **no ven** los artifacts privados de Harrison. El diseño va dentro del repositorio ([diseno/](diseno/)) y la ficha exige capturas. En T12 el primer diseño "no cumplía con lo acordado" y hubo que rehacerlo |
| Revisar una tarea | Leer el informe; `git diff --stat main...<rama>`; correr las pruebas en Docker; **revisar que los textos de alumnos no entren en `st.html`**; revisar que el contrato solo agregue (`git diff` del contrato, líneas que empiezan con `-`); `docker ps` para ver que no quedaron contenedores de prueba |
| Pruebas de Java | El comando de [OPERACION.md §5](../OPERACION.md), agregando `-e LINKEDIN_ACCESS_TOKEN=` por seguridad. Tardan unos 3 minutos: correrlas en segundo plano |
| Pruebas del panel | En la imagen del panel (Windows no tiene Streamlit): `docker run --rm --user root -v "<repo>:/repo" -w /repo --entrypoint sh insightedu-panel -c "pip install -q pytest; python -m pytest panel/tests -q"` |
| Datos pequeños | Con unos 67 mensajes, todo porcentaje e índice lleva su n (DEC-155) |
| Secretos | Si Harrison pega un token en el chat: no repetirlo, pedirle que lo ponga directo en el `.env` y revisar solo los nombres de las variables |
| Fin de línea | Los documentos usan CRLF. Editar con la herramienta Edit, sin mezclar fines de línea en un mismo archivo |
| Juan Sebastián | Subió commits directo a `main` el 2026-10-13. No insistir con proteger `main` |

## 7. Primer mensaje para el orquestador nuevo

*"Eres el chat orquestador de InsightEdu Lab: guía, orquestador y revisor. Lee completos AGENTS.md, docs/ESTADO.md, docs/DECISIONES.md, docs/ARQUITECTURA.md, docs/historico/TRASPASO_ORQUESTADOR.md y docs/historico/diseno/README.md. El método de trabajo está en docs/historico/CHAT_PRINCIPAL.md, con los cambios del traspaso. Estamos en la rama tarea/T13-borradores: tu primera tarea es escribir la ficha de T13. Respóndeme siempre en español y con el formato de siempre."*
