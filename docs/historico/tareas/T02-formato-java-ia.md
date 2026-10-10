# T02 · Formato Java ↔ IA: la IA acepta el contrato v1 y devuelve etiquetas

| Dato | Valor |
|---|---|
| Fase del plan | 3 · Clasificar y responder ([análisis §9](../ANALISIS_INGENIERIA_PROPUESTA_3.md#9-prioridades-y-orden)) |
| Objetivos | OE2 (etiquetas) y OE4 (respuesta en vivo) |
| Hallazgos que resuelve | C3, C4 y F4 del análisis, y la parte de F8 que le toca a la IA |
| Tamaño | M |
| Modelo de Claude recomendado | **Opus 5.5**: define un contrato que después usa Java (T04) |
| Depende de | Nada. T01 ya está fusionada |
| Rama | `tarea/T02-formato-java-ia` |

## 1. Objetivo

Que la IA reciba los mensajes **en el formato del contrato v1** (el mismo que guarda Java en la "caja") y devuelva, **por cada mensaje**, sus etiquetas: intención, confianza, sentimiento y tema, con un estado `OK` o `ERROR`. En modo `tiempoReal` también devuelve la respuesta del Agente FAQ a las dudas.

El resultado es un **contrato Java ↔ IA v1** documentado, con un JSON Schema, que en T04 Java implementa sin tener que adivinar.

## 2. Contexto que hay que leer

| Qué | Dónde |
|---|---|
| Los hallazgos C3, C4, F4, F5 y F8, y las decisiones D3 (el bot responde solo con respaldo) y D4 (tiempos 20 / 30 / 40 s) | [Análisis](../ANALISIS_INGENIERIA_PROPUESTA_3.md) |
| El contrato v1. Ojo: el JSON usa **camelCase** (`textoOriginal`), porque `contract.py` tiene `alias_generator=to_camel` | [CONTRACT.md](../../../ingestion/discord/docs/CONTRACT.md) y [contract.py](../../../ingestion/discord/contract.py) |
| Las tablas donde Java va a guardar el resultado: columnas `intencion`, `confianza`, `sentimiento`, `tema`, `estado_clasificacion` (`PENDIENTE` / `OK` / `ERROR`) | `backend-java/src/main/resources/db/migration/V1__modelo_inicial.sql` |
| El código de la IA de hoy | `agents/orquestador/` (`api.py`, `contratos.py`, `adaptador.py`, `orquestador.py`, `nodos/`, `clasificadores/`) |

## 3. Alcance: qué entra

1. **Una puerta nueva, `POST /v1/procesar`,** que recibe un lote del contrato v1.
   - **Una sola definición del contrato:** la IA usa `ingestion/discord/contract.py` o su JSON Schema, **sin copiarlos a mano**. Si hace falta que `agents/Dockerfile` incluya ese archivo, está permitido.
   - La puerta vieja, `/procesar`, **se mantiene igual**, porque el bot todavía la usa. Se quita cuando el bot pase por Java (C2, otra tarea).
2. **Qué mensajes se procesan:**

   | Mensaje | Qué se hace |
   |---|---|
   | `autor.tipo = persona` (incluye `esSimulado = true`) y con texto | Se clasifica |
   | `botPropio`, `otroBot`, `tipo = avisoSistema` o sin texto | No se gasta el LLM: se devuelve `intencion = OTRO`, `estado = OK` y el motivo |

3. **Una sola llamada al LLM por mensaje**, con salida estructurada, que devuelve:
   - **intención:** `TESTIMONIO` / `PREGUNTA_FAQ` / `COMENTARIO` / `OTRO`, más la confianza (0 a 1) y la razón;
   - **sentimiento:** `MUY_POSITIVO` / `POSITIVO` / `NEUTRO` / `NEGATIVO` / `MUY_NEGATIVO`;
   - **tema:** de una **lista cerrada**, para que el dashboard pueda contar. Lista propuesta: `inscripciones`, `becas_pagos`, `evaluaciones`, `contenido_curso`, `plataforma_acceso`, `proyectos`, `empleo`, `comunidad`, `otro`.

   Ajusta la lista con los 39 mensajes simulados y los temas de los PDFs. **Cualquier cambio se valida con Harrison.**
4. **F4 · Un error no es ruido:** si el LLM falla después de sus reintentos, se devuelve `estado = ERROR`, **sin** intención inventada, con el motivo. Nunca se convierte en `OTRO`.
5. **Respuesta en vivo:** solo en modo `tiempoReal` y para `PREGUNTA_FAQ`, se incluye la respuesta del Agente FAQ: texto, si encontró respaldo (D3) y fuentes. En modo `historial` **no** se generan respuestas, para no gastar.
6. **Sin Agente-Mod:** la puerta nueva no invoca al Agente-Mod (no existe; es la fase 4). Un `TESTIMONIO` solo se etiqueta.
7. **Tiempo máximo del LLM: 20 s por llamada** (D4, F8), configurable por variable de entorno.
8. **LangGraph sigue siendo el orquestador**: es un requisito del brief. Puedes ajustar el grafo o crear uno para esta puerta.
9. **D2:** la puerta nueva **no sube paquetes a OCI**; los activos los sube Java. El log de ejecución puede seguir yendo a OCI si está configurado.
10. **Contrato Java ↔ IA v1 documentado**, en `docs/contratos/JAVA_IA_v1.md`, con:
    - un ejemplo de entrada y uno de salida;
    - la tabla de campos;
    - qué hace Java con cada `estado`;
    - un JSON Schema generado desde los modelos de pydantic.

    Usa el mismo estilo de nombres que el contrato v1 (camelCase).

**Forma de la respuesta propuesta** (se puede ajustar justificándolo):
```json
{
  "versionContratoIa": "1.0",
  "loteId": "…",
  "resultados": [
    {
      "discordId": "…",
      "estado": "OK",
      "intencion": "PREGUNTA_FAQ",
      "confianza": 0.93,
      "sentimiento": "NEUTRO",
      "tema": "inscripciones",
      "razon": "…",
      "respuesta": { "texto": "…", "encontrada": true, "fuentes": ["01_Reglamento_Academico_V3.pdf (Pág. 3)"] }
    }
  ],
  "metricas": { "duracionMs": 0, "tokensIn": 0, "tokensOut": 0 }
}
```

## 4. Fuera de alcance

- Código Java: es T04.
- Cambiar el bot o quitar `/procesar`: es C2, otra tarea.
- El Agente-Mod (fase 4) y la FAQ semanal.
- Cambiar el contrato v1 de la ingesta.
- Autenticación entre Java y la IA (S2): va con T04.

## 5. Pruebas exigidas

Sin gastar llamadas reales al LLM: con un modelo falso o con el clasificador de palabras clave.

| # | Caso | Resultado esperado |
|---|---|---|
| 1 | Lote válido del contrato v1 (con los mensajes de prueba de la ingesta) | Un resultado por mensaje, con `discordId` |
| 2 | Lote que no cumple el contrato | Error 422 o 400 claro, sin detalles internos (S7) |
| 3 | Mensaje de `botPropio`, `avisoSistema` o sin texto | `OTRO` y `OK` con su motivo, **sin llamar al LLM** |
| 4 | El LLM falla | `estado = ERROR`, sin intención (F4) |
| 5 | `PREGUNTA_FAQ` en `tiempoReal` | Trae `respuesta` |
| 6 | `PREGUNTA_FAQ` en `historial` | **No** trae `respuesta` |
| 7 | El JSON Schema generado coincide con los modelos | El schema se regenera y se compara en la prueba |
| 8 | Las pruebas que ya existían | Siguen pasando: `python -m pytest agents/orquestador/tests -q` |

**Prueba real, una sola vez y la corre Harrison:** con `docker compose up -d --build ia`, enviar a `/v1/procesar` un lote pequeño (3 o 4 mensajes de prueba, uno por intención) y pegar la salida en el informe.

## 6. Criterios de terminado

- [ ] `/v1/procesar` acepta el contrato v1 y devuelve un resultado por mensaje, con intención, sentimiento, tema y estado.
- [ ] `ERROR` es distinto de `OTRO` (F4).
- [ ] La respuesta del FAQ aparece solo en `tiempoReal`.
- [ ] El LLM tiene un tiempo máximo de 20 s.
- [ ] `/procesar` (el del bot) sigue funcionando igual.
- [ ] `docs/contratos/JAVA_IA_v1.md` y su JSON Schema están escritos.
- [ ] Las pruebas pasan (🧪 con la salida en el informe) y la prueba real con Docker está hecha.
- [ ] El informe `docs/tareas/T02-informe.md` está completo, y no se tocó nada fuera del alcance.

## 7. Comandos de git para Harrison

**Al empezar**, desde `C:\Users\LENOVO\Documents\Cursos\No Country\Hackaton ONE 10\insightedu-lab`:
```
git switch feature/integracion-arquitectura-3
git pull
git switch -c tarea/T02-formato-java-ia
```

**Al terminar:** el chat de tarea da los comandos de commit, y después:
```
git push -u origin tarea/T02-formato-java-ia
```

Luego le dices al chat principal **"T02 terminó"**. No se fusiona hasta que la auditoría lo apruebe.

## 8. Cómo abrir el chat de esta tarea

1. En VS Code, abrir un chat nuevo de Claude Code **en esta misma carpeta**.
2. Elegir el modelo **Opus 5.5** con `/model`.
3. Primer mensaje: *"Eres el chat de la tarea T02. Lee CLAUDE.md y docs/tareas/T02-formato-java-ia.md y empieza."*
