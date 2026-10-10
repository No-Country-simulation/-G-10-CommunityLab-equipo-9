# T03 · Puerta de lotes en Java: recibir el contrato v1, upsert y API key

| Dato | Valor |
|---|---|
| Fase del plan | 2 · Datos y captura ([análisis §9](../ANALISIS_INGENIERIA_PROPUESTA_3.md#9-prioridades-y-orden)) |
| Objetivos | OE1 (captura por lotes sin duplicados) y OE8 (seguridad) |
| Hallazgos que resuelve | C1, S1, F13, la "prueba real de `send_batch.py`" y observaciones de T01 ([docs/tareas/README.md](README.md)) |
| Tamaño | M |
| Modelo de Claude recomendado | **Sonnet 5.5**: la ficha es acotada. Si se traba con la seguridad o las transacciones, cambiar a Opus 5.5 |
| Depende de | T01 (tablas y upsert) ✅ |
| Rama | `tarea/T03-puerta-lotes` |
| Decisión previa | **D8**: formato que recibe Java (sección 3.1). 👤 **Validada el 2026-10-03: opción (a), el contrato v1 tal cual** |

## 1. Objetivo

Que la ingesta por lotes vuelva a llegar a Java, ahora sobre el modelo de T01. El camino es:

> `build_batch.py` → `send_batch.py` → **`POST /api/v1/lotes`** (con API key) → upsert en `mensajes` + fila en `lotes_recibidos` → recibo

El resultado se comprueba con los mensajes reales del servidor de pruebas, **sin duplicados al reenviar**.

## 2. Contexto que hay que leer

| Qué | Dónde |
|---|---|
| Tablas y upsert (`MensajeUpsertRepository.upsert` devuelve `NUEVO` / `ACTUALIZADO` / `SIN_CAMBIOS`; la caja es un `Map<String, Object>`) | `backend-java/` (T01) y [T01-informe.md](T01-informe.md) |
| El contrato v1 en JSON (camelCase) y su schema | [CONTRACT.md](../../../ingestion/discord/docs/CONTRACT.md), [contract_v1.schema.json](../../../ingestion/discord/schema/contract_v1.schema.json) |
| Cómo envía hoy la ingesta: arma el formato "opción C", espera `status: "exitoso"` y guarda el marcador solo si Java confirma | `ingestion/discord/send_batch.py`, `tests/test_send.py` y [INGESTION_GUIDE.md §11](../ingesta/INGESTION_GUIDE.md) |
| S1 (API key) y F13 (errores) | [Análisis §3 y §4](../ANALISIS_INGENIERIA_PROPUESTA_3.md) |
| El formato común de error, ya usado por la IA: `{codigo, mensaje, errores[], idCorrelacion}` | [docs/contratos/JAVA_IA_v1.md](../../contratos/JAVA_IA_v1.md) |

## 3. Alcance: qué entra

### 3.1 Decisión D8: qué formato recibe Java 👤

| Opción | Qué es |
|---|---|
| **(a) Recomendada: el contrato v1 tal cual.** El cuerpo es el `Lote` que ya arma `build_batch.py`. Java saca las columnas de cada mensaje y guarda el mensaje completo como caja | Cumple la regla 1 de la propuesta 3 ("un solo formato de mensaje"). La IA ya recibe ese mismo formato (T02), así que Java le pasa las cajas sin convertir nada. `send_batch.py` se simplifica: se borra `a_formato_backend` |
| (b) Mantener la "opción C" (los campos viejos de backend más la caja) | Se diseñó para no esperar al equipo de backend. Desde T01 ese formato ya no existe en Java |

🔎 La opción C fue un puente para no depender de backend. Ahora controlamos los dos lados, así que la (a) quita una conversión y un formato. **Si Harrison elige (b), avisar al chat principal antes de empezar.**

### 3.2 La puerta `POST /api/v1/lotes` (con la opción a)

1. **Lectura del lote:** campos tipados para lo que va a columnas (`loteId`, `versionContrato`, `modo` y, por mensaje, `id`, `canal.id`, `autor.id`, `autor.tipo`, `autor.rol`, `esSimulado`, `fecha`, `respondeA`, `textoOriginal`). Además, **cada mensaje completo como `Map`**, que es la caja.
2. **Validación:**
   - `versionContrato` debe ser `"1.0"`;
   - los valores cerrados tienen que estar en las listas del contrato;
   - hay un tope de mensajes por lote (por ejemplo, 1000) y de tamaño del cuerpo.

   Si algo falla: **422**, con el formato común y **sin repetir los datos recibidos** (S7).
3. **Una sola transacción por lote:** todos los upsert y la fila de `lotes_recibidos` (`total`, `nuevos`, `actualizados`). Si algo falla, no queda nada a medias.
4. **Reenviar un lote es seguro (idempotencia):** si llega un `loteId` que ya existe, se responde **200 con el mismo recibo guardado**, sin volver a procesarlo.
   - **Por qué:** si la red se corta después de que Java guardó el lote, `send_batch.py` lo reintenta, y tiene que recibir un "ok" para avanzar su marcador.
5. **Recibo:** `{loteId, total, nuevos, actualizados, sinCambios, recibidoEn, yaRecibido}`.
6. **API key (S1):**
   - un filtro que exige la cabecera `X-Api-Key`; la clave de la ingesta va en la variable `API_KEY_INGESTA`, y se deja preparado para sumar las del bot y el panel;
   - la comparación se hace en tiempo constante;
   - sin clave o con una clave incorrecta: **401**, con el formato común;
   - `/actuator/health` queda **sin** clave;
   - la clave nunca se escribe en los registros.
7. **Manejo global de errores (F13):**
   - 400 o 422 si la entrada es inválida;
   - 404 si no existe;
   - 500 con un mensaje genérico, y el detalle solo en el registro;
   - todos con `idCorrelacion`, tomado de la cabecera `X-Id-Correlacion` si viene.
8. **Configuración:**
   - `compose.yml` pasa `API_KEY_INGESTA` a `api-java`, y se agrega a la plantilla `.env.example` de la raíz;
   - la clave se **genera al azar con un comando o script que la escribe en `.env` y en `ingestion/discord/.env` sin mostrarla**, igual que se hizo con `POSTGRES_PASSWORD`.
9. **La ingesta:** `send_batch.py`
   - envía el `Lote` tal cual a `BACKEND_INGEST_URL`, con la cabecera `X-Api-Key` (variable `BACKEND_API_KEY`);
   - acepta el recibo nuevo, incluido `yaRecibido`;
   - no cambia lo demás: el marcador sigue avanzando solo con la confirmación.

   También se actualizan `tests/test_send.py` y `ingestion/discord/.env.example` (`BACKEND_INGEST_URL=http://127.0.0.1:8008/api/v1/lotes`). Se borra `a_formato_backend`.

## 4. Fuera de alcance

- Llamar a la IA y guardar las etiquetas: es T04.
- El bot en vivo (C2).
- Las puertas del panel (fase 5) y OCI (fase 6).
- Cambiar el contrato v1, `contract.py`, `transform.py` o el upsert de T01.
- Las URL de los adjuntos que inflan los "actualizados" (observación de T01): **solo evaluarlo y anotarlo en el informe**, sin cambiar el upsert.
- **No ejecutar `simulate_students.py`.**

## 5. Pruebas exigidas

**Java**, con PostgreSQL real (base `insightedu_test`, [OPERACION.md §5](../../OPERACION.md)):

| # | Caso | Resultado esperado |
|---|---|---|
| 1 | Lote válido de 3 mensajes | 200 · `total 3, nuevos 3` · 3 filas en `mensajes` · 1 fila en `lotes_recibidos` |
| 2 | El **mismo** `loteId` otra vez | 200 · `yaRecibido true` · mismo recibo · sin filas nuevas |
| 3 | `loteId` nuevo con los mismos mensajes y uno con más reacciones | `actualizados 1, sinCambios 2` · siguen siendo 3 filas |
| 4 | Sin `X-Api-Key`, o con una clave incorrecta | 401 · formato común · nada guardado |
| 5 | `/actuator/health` sin clave | 200 |
| 6 | `versionContrato` distinta o un valor fuera de la lista | 422 · formato común · sin repetir la entrada |
| 7 | Un mensaje inválido en medio del lote | Nada guardado (transacción) |
| 8 | Las 11 pruebas de T01 | Siguen pasando |

**Python:** `test_send.py` actualizado, y las 34 pruebas de la ingesta (más las nuevas) pasan.

**Prueba real, la corre Harrison:**
1. `docker compose up -d --build api-java`.
2. Desde `ingestion/discord`, con su entorno: `python build_batch.py` y `python send_batch.py`.
3. Verificar con una consulta de **solo lectura**, por ejemplo: `docker compose exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select count(*) from mensajes"'`.
4. **Volver a enviar el mismo lote:** no debe duplicar.
5. Pegar las salidas en el informe.

## 6. Criterios de terminado

- [ ] D8 validada por Harrison y anotada en el informe.
- [ ] `POST /api/v1/lotes` guarda sin duplicar, en una sola transacción, y es idempotente por `loteId`.
- [ ] La API key es obligatoria (salvo en `/actuator/health`), se genera sin mostrarla y está en las dos plantillas `.env.example`.
- [ ] Hay manejo global de errores con el formato común.
- [ ] `send_batch.py` envía al Java real, con la clave, y el reenvío no duplica (🧪 prueba real).
- [ ] Las pruebas de Java y Python pasan (🧪 con la salida en el informe).
- [ ] El informe `docs/tareas/T03-informe.md` está completo, y no se tocó nada fuera del alcance.

## 7. Comandos de git para Harrison

**Al empezar**, desde `C:\Users\LENOVO\Documents\Cursos\No Country\Hackaton ONE 10\insightedu-lab`:
```
git switch feature/integracion-arquitectura-3
git pull
git switch -c tarea/T03-puerta-lotes
```

**Al terminar:** el chat de tarea da los comandos de commit, y después:
```
git push -u origin tarea/T03-puerta-lotes
```

Luego le dices al chat principal **"T03 terminó"**. No se fusiona hasta que la auditoría lo apruebe.

## 8. Cómo abrir el chat de esta tarea

1. En VS Code, abrir un chat nuevo de Claude Code **en esta misma carpeta**.
2. Elegir el modelo **Sonnet 5.5** con `/model`.
3. Primer mensaje: *"Eres el chat de la tarea T03. Lee CLAUDE.md y docs/tareas/T03-puerta-lotes.md y empieza. La decisión D8 es la opción (a)."* Si eliges la (b), cámbialo en el mensaje.
