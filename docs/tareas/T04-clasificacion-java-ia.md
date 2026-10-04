# T04 · Java envía los mensajes a la IA y guarda las etiquetas

| Dato | Valor |
|---|---|
| Fase del plan | 3 · Clasificar y responder ([análisis §9](../ANALISIS_INGENIERIA_PROPUESTA_3.md#9-prioridades-y-orden)) |
| Objetivos | OE2 (cada mensaje etiquetado en la base) y OE8 (seguridad entre Java y la IA) |
| Hallazgos que resuelve | C3 (lado Java), S2, F4 (lado Java), F8 (lado Java) y observaciones de T02 ([README](README.md)) |
| Tamaño | M |
| Modelo de Claude recomendado | **Opus 5.5**: procesamiento en segundo plano, concurrencia y cambios en Java y en Python |
| Depende de | T01 ✅, T02 ✅ y T03 ✅. T03 dejó la API key de los clientes (`seguridad.api-keys.*`, `ApiKeyFilter`), el formato común de error (`ErrorApi`, `ManejadorErrores`) y el id de correlación: **reutilizarlos** |
| Rama | `tarea/T04-clasificacion-java-ia` |

## 1. Objetivo

Que todo mensaje que llega a la base con `estado_clasificacion = PENDIENTE` se envíe a la IA (`POST /v1/procesar`, [contrato Java ↔ IA v1](../contratos/JAVA_IA_v1.md)) y quede guardado con su intención, confianza, sentimiento, tema y estado.

Se hace **en segundo plano y en tandas chicas**, sin que un fallo de la IA pierda mensajes. El flujo **en vivo** (bot → Java → IA → bot) **no** está en esta tarea: es C2, en otra ficha.

## 2. Contexto que hay que leer

| Qué | Dónde |
|---|---|
| El contrato Java ↔ IA: entrada (un `Lote` del contrato v1), salida, estados `OK` / `ERROR`, campo `metodo` y listas cerradas (§4.3) | [docs/contratos/JAVA_IA_v1.md](../contratos/JAVA_IA_v1.md) y su JSON Schema |
| Observaciones de T02: los lotes de historial no entran en 30 s si van todos juntos, y las listas de sentimiento y tema pasan a `CHECK` | [README de tareas](README.md) |
| Tablas, upsert y la caja (`Map<String, Object>`) | `backend-java/` (T01) |
| La puerta de lotes, la API key y el formato común de error | `backend-java/` (T03) y [T03-informe.md](T03-informe.md) |
| S2, F4, F8 y D4 (tiempos 20 / 30 / 40 s) | [Análisis](../ANALISIS_INGENIERIA_PROPUESTA_3.md) |
| Lo que hay hoy en el cliente: conexión configurada, sin método | `backend-java/.../client/NlpDataClient.java`, `config/RestClientConfig.java` |

## 3. Alcance: qué entra

1. **Migración `V2__…`** (nunca editar la V1):
   - `CHECK` de `sentimiento` y de `tema`, con las listas de `JAVA_IA_v1.md` §4.3;
   - columnas nuevas en `mensajes`: `intentos_clasificacion` (entero, 0 por defecto), `metodo_clasificacion` (`llm` / `palabrasClave` / `regla`) y `servidor_id`, que hace falta para armar el `Lote` que espera la IA;
   - un índice parcial para buscar rápido los pendientes (`WHERE estado_clasificacion = 'PENDIENTE'`);
   - que la puerta de lotes de T03 guarde `servidor_id`.
2. **`NlpDataClient`:** un método que hace `POST /v1/procesar`
   - con las cabeceras `X-Api-Key` (variable `API_KEY_IA`) y `X-Id-Correlacion`;
   - con conexión de 5 s y lectura de **30 s** (D4);
   - que lee la respuesta con tipos.

   Los errores de la IA se distinguen: 422 es un error de nuestro lado y se registra; 500 o tiempo agotado es un fallo pasajero.
3. **Clasificación en segundo plano:** una tarea programada (`@Scheduled`, configurable, por ejemplo cada 30 s) que:
   - toma hasta **N mensajes `PENDIENTE`** (configurable, por ejemplo 5) con `SELECT … FOR UPDATE SKIP LOCKED`, para que dos ejecuciones no tomen los mismos;
   - arma un `Lote` del contrato v1 con sus cajas: `modo = historial`, `loteId` propio (por ejemplo, `clasif-<uuid>`), `servidorId` y `generadoEn`;
   - llama a la IA y guarda cada resultado:

   | Respuesta de la IA | Qué se guarda |
   |---|---|
   | `OK` | `intencion`, `confianza`, `sentimiento`, `tema`, `metodo_clasificacion` y `clasificado_en`; estado `OK` |
   | `ERROR` en un mensaje | Suma un intento. Al llegar al máximo (configurable, por ejemplo 3), estado `ERROR`; si no, sigue en `PENDIENTE` |
   | Falla toda la llamada (500, tiempo agotado, IA caída) | **Nada cambia de estado**: se reintenta en la siguiente ejecución, con los intentos sumados |
   | 422 | Se registra como error de programación, con los intentos sumados |

   **No se pisa un mensaje que cambió mientras tanto:** si el lote de la hora actualizó su texto después de que se envió a la IA, el resultado viejo no se guarda. Se compara `actualizado_en`.
4. **S2 · API key en la IA:**
   - `/v1/procesar` exige `X-Api-Key` (variable `API_KEY_IA`), comparada en tiempo constante;
   - `/health` queda sin clave;
   - **`/procesar` (el del bot) no se toca** hasta C2;
   - la clave se genera sin mostrarla y se escribe en `.env`, igual que en T03; `compose.yml` la pasa a `ia` y a `api-java`;
   - se agrega a `.env.example`.
5. **Registros:** cada ejecución registra cuántos mensajes tomó, cuántos quedaron en `OK`, en `ERROR` y en reintento, y cuánto tardó. **Sin el texto de los mensajes** (S11).
6. **Carácter NUL** (observación de T03): al recibir un lote en `POST /api/v1/lotes`, se quita `\u0000` del texto y de los textos de la caja, para que un solo mensaje no haga fallar todo el lote con 500. Agregar una prueba. Es la opción recomendada 🔎, pendiente del 👤 OK de Harrison; la otra opción es rechazar el lote con 422.

## 4. Fuera de alcance

- El flujo en vivo (C2): el bot pasa por Java, y el tope total por pedido en la IA para `tiempoReal`. Eso es otra ficha.
- El Agente-Mod (fase 4), el panel, el dashboard y OCI.
- Cambiar el contrato v1 o el contrato Java ↔ IA v1. Si hace falta, se consulta.
- **No ejecutar `simulate_students.py`.**

## 5. Pruebas exigidas

**Java**, con PostgreSQL real (`insightedu_test`) y la IA **simulada** (por ejemplo, con `MockRestServiceServer` o WireMock):

| # | Caso | Resultado esperado |
|---|---|---|
| 1 | 3 pendientes; la IA responde `OK` | Los 3 quedan `OK`, con sus etiquetas y su método |
| 2 | La IA responde `ERROR` en 1 de 3 | Ese suma un intento y sigue `PENDIENTE`; al tercer error, queda `ERROR` |
| 3 | La IA responde 500 o se agota el tiempo | Ninguno cambia de estado; los intentos suman |
| 4 | Un mensaje cambió de texto mientras se clasificaba | No se guarda el resultado viejo |
| 5 | Mensajes ya en `OK` o en `ERROR` | No se vuelven a enviar |
| 6 | Más pendientes que el tamaño de la tanda | Se procesan en varias ejecuciones |
| 7 | La V2 rechaza un `tema` o un `sentimiento` fuera de la lista | Lo rechaza el `CHECK` |
| 8 | Las pruebas de T01 y T03 | Siguen pasando |

**Python:** `/v1/procesar` sin clave o con una clave incorrecta da 401; con la clave correcta funciona; `/health` funciona sin clave; `/procesar` no cambia. Las 23 pruebas de la IA y las 34 de la ingesta siguen pasando.

**Prueba real, la corre Harrison** (gasta unas 40 llamadas a Gemini, alrededor de 20 000 tokens):
1. `docker compose up -d --build`.
2. Enviar el historial con `send_batch.py`, que es el camino de T03.
3. Esperar un par de minutos.
4. Consulta de solo lectura: `select estado_clasificacion, intencion, count(*) from mensajes group by 1, 2`.
5. Pegar la salida en el informe.

## 6. Criterios de terminado

- [ ] La V2 está aplicada, con los `CHECK`, las columnas nuevas y el índice parcial.
- [ ] Los `PENDIENTE` se clasifican solos, en tandas chicas, sin que dos ejecuciones tomen los mismos mensajes.
- [ ] `ERROR`, los reintentos y el máximo de intentos funcionan; un fallo de la IA no pierde ni marca mal ningún mensaje.
- [ ] La IA exige la API key en `/v1/procesar`, y Java la envía.
- [ ] Las pruebas de Java y Python pasan, y la prueba real muestra la base clasificada (🧪 con la salida en el informe).
- [ ] El informe `docs/tareas/T04-informe.md` está completo, y no se tocó nada fuera del alcance.

## 7. Comandos de git para Harrison

**Al empezar**, desde `C:\Users\LENOVO\Documents\Cursos\No Country\Hackaton ONE 10\insightedu-lab`:
```
git switch feature/integracion-arquitectura-3
git pull
git switch -c tarea/T04-clasificacion-java-ia
```

**Al terminar:** el chat de tarea da los comandos de commit, y después:
```
git push -u origin tarea/T04-clasificacion-java-ia
```

Luego le dices al chat principal **"T04 terminó"**.

## 8. Cómo abrir el chat de esta tarea

1. En VS Code, abrir un chat nuevo de Claude Code **en esta misma carpeta**.
2. Elegir el modelo **Opus 5.5** con `/model`.
3. Primer mensaje: *"Eres el chat de la tarea T04. Lee CLAUDE.md y docs/tareas/T04-clasificacion-java-ia.md y empieza."*
