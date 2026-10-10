# Histórico: cómo se construyó InsightEdu Lab

> ⚠️ **Nada de esta carpeta es una instrucción vigente.** Aquí está la traza de cómo se diseñó e integró el proyecto: propuestas, planes, fichas de trabajo, informes y documentos de etapas anteriores. Algunos datos ya cambiaron.
> **Cómo funciona hoy:** [ARQUITECTURA.md](../ARQUITECTURA.md). **Qué falta:** [ESTADO.md](../ESTADO.md). **Por qué se decidió cada cosa:** [DECISIONES.md](../DECISIONES.md).

## Para qué sirve

Para entender **por qué** algo es como es, o para recuperar el contexto de una decisión. Por ejemplo:
- [DECISIONES.md](../DECISIONES.md) cita hallazgos con códigos como **S1**, **F4** o **C2**: vienen del análisis de esta carpeta;
- su columna "Detalle en" enlaza a las fichas y los informes de cada tarea.

## Qué hay

| Documento | Qué es | Fecha |
|---|---|---|
| [propuesta-3/Propuesta_3_Arquitectura_InsightEdu.pdf](propuesta-3/Propuesta_3_Arquitectura_InsightEdu.pdf) | La **propuesta de arquitectura 3** que el equipo aprobó: las necesidades N1 a N7, las piezas y qué faltaba en cada una. Hoy la reemplaza [ARQUITECTURA.md](../ARQUITECTURA.md) | 2026-10-02 |
| [ANALISIS_INGENIERIA_PROPUESTA_3.md](ANALISIS_INGENIERIA_PROPUESTA_3.md) | El **plan de la integración**: objetivos OE1 a OE9, hallazgos (S\* seguridad, F\* fallos, C\* contratos, Q\* calidad, O\* operación), decisiones D1 a D8, fases y registro de avance | 2026-10-03 en adelante |
| [tareas/](tareas/) | Las **fichas** (qué se pidió) y los **informes** (qué se hizo, cómo se probó y qué se decidió) de cada tarea de la integración, de **T01 a T09**. **T10** (despliegue y demo) quedó solo como ficha, sin ejecutar: ver [ESTADO.md](../ESTADO.md) | 2026-10-03 a 2026-10-05 |
| [CHAT_PRINCIPAL.md](CHAT_PRINCIPAL.md) y [CLAUDE_integracion.md](CLAUDE_integracion.md) | El **método de trabajo** de la integración: un asistente de IA que escribía las fichas y revisaba cada tarea, y otro por cada tarea | 2026-10-03 a 2026-10-09 |
| [entregas/AVANCE_CLIENTE.md](entregas/AVANCE_CLIENTE.md) | Informe de avance para el cliente | 2026-10-05 |
| [componentes/](componentes/) | Los README originales del orquestador y del Agente FAQ, escritos por el equipo de IA antes de la integración | Antes del 2026-10-02 |
| [ingesta/](ingesta/) | Documentos de la ingesta: la guía para el equipo (con la "opción C", reemplazada por D8), la primera propuesta de arquitectura, el alcance y el catálogo de eventos | 2026-09-28 a 2026-10-02 |
| [equipos/README_original_equipos.md](equipos/README_original_equipos.md) | El README original del repositorio, con la documentación de cada equipo (orquestador, backend y Docker) | Antes del 2026-10-02 |

## Cómo leer los documentos de esta carpeta

- Las fechas y los estados son **de ese momento**: por ejemplo, el PDF marca piezas como "FALTA" que hoy existen.
- Las rutas de rama que mencionan (`tarea/T0x-…`, `feature/integracion-arquitectura-3`) ya no existen: todo está en `main`. Sus últimos commits están en [ESTADO.md](../ESTADO.md) §5.
- Los nombres de personas y los pasos con comandos de git correspondían al método de trabajo de entonces.
