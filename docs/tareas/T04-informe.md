# Informe de la tarea T04 — Java envía los mensajes a la IA y guarda las etiquetas

| Dato | Valor |
|---|---|
| Fecha | 2026-10-04 |
| Modelo de Claude usado | Opus 5.5 (`claude-opus-5-5`) |
| Rama | `tarea/T04-clasificacion-java-ia` |
| Commits | Uno: `feat(backend,ia): clasificacion en segundo plano de los PENDIENTE y API key entre Java y la IA (T04)` (ver `git log`) |

## 1. Resumen

Java clasifica solo los mensajes `PENDIENTE`: cada 30 s reserva una tanda de 5, se la envía a la IA (`POST /v1/procesar`) como un lote del contrato v1 y guarda intención, confianza, sentimiento, tema y método. Lo hace con reintentos, un máximo de 3 intentos y sin guardar resultados viejos si el mensaje cambió en el medio. La IA exige la API key de Java (S2), y la puerta de lotes quita el carácter NUL y guarda `servidor_id`. Pasan 51 pruebas de Java, 29 de la IA y 36 de la ingesta. **La prueba real clasificó los 39 mensajes del servidor, todos en `OK` al primer intento.**

## 2. Criterios de terminado

| Criterio | Estado | Evidencia |
|---|---|---|
| La V2 está aplicada, con los `CHECK`, las columnas nuevas y el índice parcial | ✅ | 🧪 `flyway_schema_history`: versión 2 `clasificacion` aplicada en la base principal y en `insightedu_test`. Prueba `laV2RechazaTemaOSentimientoFueraDeLaLista` |
| Los `PENDIENTE` se clasifican solos, en tandas chicas, sin que dos ejecuciones tomen los mismos mensajes | ✅ | 🧪 `masPendientesQueLaTandaSeProcesanEnVariasVueltas`, `dosReservasAlMismoTiempoNoTomanLosMismosMensajes` y `unMensajeReservadoNoSeTomaHastaQueVenzaLaReserva`. Prueba real: 8 tandas (7 de 5 y 1 de 4) |
| `ERROR`, los reintentos y el máximo funcionan; un fallo de la IA no pierde ni marca mal ningún mensaje | ✅ | 🧪 Casos 2, 3 y 4 y las pruebas del 422. Al quitar a propósito la comparación de `actualizado_en`, falla la prueba del caso 4 |
| La IA exige la API key en `/v1/procesar`, y Java la envía | ✅ | 🧪 6 pruebas de S2 en Python y `NlpDataClientTest` (cabecera `X-Api-Key`). Prueba real: 0 rechazos 401 en el registro de `ia` |
| Las pruebas de Java y Python pasan, y la prueba real muestra la base clasificada | ✅ | Sección 4 |
| Informe completo; no se tocó nada fuera del alcance | ✅ | No se tocó el bot, `/procesar`, el contrato v1, `contract.py` ni `transform.py`. El contrato Java ↔ IA solo recibió el agregado validado (sección 5) |

## 3. Archivos cambiados

Rutas Java relativas a `backend-java/src/main/java/com/insightedulab/backend_java/`.

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `backend-java/src/main/resources/db/migration/V2__clasificacion.sql` | Nuevo: `CHECK` de `sentimiento` y `tema`; columnas `intentos_clasificacion`, `metodo_clasificacion`, `servidor_id` y `reservado_hasta`; índice parcial `idx_mensajes_pendientes (fecha, id) WHERE PENDIENTE` | §3.1 |
| `clasificacion/ClasificacionService.java` | Nuevo: reserva la tanda, arma un `Lote` por servidor, llama a la IA y guarda cada resultado (OK, ERROR, 422 o fallo de la llamada) | §3.3 |
| `clasificacion/ClasificacionRepository.java` | Nuevo: el SQL, una sentencia por paso, sin transacción abierta mientras se espera a la IA. Reserva con `FOR UPDATE SKIP LOCKED` más `reservado_hasta`; escrituras con `AND actualizado_en = :foto` | §3.3 y decisión 1 |
| `clasificacion/ClasificacionProgramada.java`, `ClasificacionConfig.java`, `ClasificacionProperties.java` | Nuevos: la tarea `@Scheduled` (`fixedDelay` de 30 s) y las propiedades `clasificacion.*`. Registra cada tanda sin textos (S11) | §3.3 y §3.5 |
| `client/NlpDataClient.java` | `procesar(lote, idCorrelacion)`: 200 → `RespuestaIa`; 422 → `IaRechazoException`; otro error, tiempo agotado o IA caída → `IaNoDisponibleException` | §3.2 |
| `client/RespuestaIa.java`, `IaRechazoException.java`, `IaNoDisponibleException.java` | Nuevos | §3.2 |
| `config/RestClientConfig.java` | Conexión 5 s / lectura 30 s (D4); cabecera `X-Api-Key` desde `ia.api-key` | §3.2 |
| `model/Mensaje.java`, `model/enums/MetodoClasificacion.java` | Las 4 columnas nuevas en la entidad | §3.1 |
| `repository/MensajeUpsertRepository.java` | + `servidor_id` (un envío sin servidor no borra el anterior); si cambia el texto, los intentos vuelven a 0 | §3.1 y decisión 6 |
| `service/LoteService.java` | Guarda `servidor_id`; **quita `\u0000`** de todos los textos del lote y de la caja | §3.1 y §3.6 |
| `backend-java/src/main/resources/application.properties` | + `ia.api-key` y `clasificacion.*` | §3.2 y §3.3 |
| `backend-java/src/test/.../ClasificacionTest.java` | Nuevo: 15 pruebas | §5 |
| `backend-java/src/test/.../NlpDataClientTest.java` | Nuevo: 6 pruebas, con `MockRestServiceServer` | §5 |
| `backend-java/src/test/.../LotesApiTest.java` | La falla a mitad de lote ahora se provoca con un espía de Mockito, porque el NUL ya no hace fallar nada. + Pruebas del NUL y de `servidor_id`. Tarea programada apagada | §3.6 |
| `backend-java/src/test/.../ModeloDatosTest.java`, `BackendJavaApplicationTests.java` | Tarea programada apagada en el primero; en el segundo se comprueba que se crea | Que no tome los mensajes de las pruebas |
| `agents/orquestador/api.py` | *Middleware* que exige `X-Api-Key` en `/v1/…`, con comparación en tiempo constante; `/health` y `/procesar` igual | §3.4 (S2) |
| `agents/orquestador/config.py` | + `API_KEY_IA` | §3.4 |
| `agents/orquestador/contrato_ia.py`, `docs/contratos/JAVA_IA_v1.schema.json` | + `NO_AUTORIZADO` en `ErrorApi.codigo` (schema regenerado: +1 línea) | Decisión 5 |
| `agents/orquestador/tests/test_v1_procesar.py` | Las pruebas envían la clave; + 6 pruebas de S2 | §5 |
| `docs/contratos/JAVA_IA_v1.md` | §1 cabeceras, §5 qué hace Java (intentos, 422), §6 tiempos, §7 `NO_AUTORIZADO`; nota de cambio al principio | Decisión 5 |
| `scripts/generar_api_key.py` | + `--cliente ia` (escribe `API_KEY_IA` en el `.env` de la raíz) | §3.4 |
| `compose.yml`, `.env.example`, `docs/OPERACION.md` | `API_KEY_IA` para `ia` y para `api-java` | §3.4 |

## 4. Pruebas

| Comando ejecutado | Resultado (🧪) |
|---|---|
| `docker run … maven:3.9-eclipse-temurin-21 mvn test` (base `insightedu_test`) | `Tests run: 51, Failures: 0, Errors: 0` · `BUILD SUCCESS` (Clasificacion 15, NlpDataClient 6, LotesApi 19, ModeloDatos 10, arranque 1) |
| Lo mismo con `-Dtest=ClasificacionTest`, quitando a propósito `AND actualizado_en = :actualizadoEn` de `GUARDAR_OK` (y restaurándolo) | `Failures: 1`: `siElMensajeCambioMientrasTantoNoSeGuardaElResultadoViejo`. La prueba detecta la falta de protección |
| `python -m pytest agents/orquestador/tests -q` | `29 passed` (23 de antes y 6 de S2) |
| `python -m pytest -q` (desde `ingestion/discord`) | `36 passed` |
| `generar_api_key.py --cliente ia` con un `.env` falso | Agrega `API_KEY_IA` al final, conserva `\r\n`, no toca las otras líneas, no muestra la clave y no pisa sin `--reemplazar` |

Casos de la ficha y sus pruebas:

| # | Caso | Prueba |
|---|---|---|
| 1 | 3 pendientes; la IA responde `OK` | `tresPendientesQuedanOkConSusEtiquetas`, `elLoteQueRecibeLaIaEsElContratoV1ConLasCajas`, `unResultadoPorReglaSeGuardaSinSentimientoNiTema` |
| 2 | `ERROR` en 1 de 3; al tercero queda `ERROR` | `unErrorDeLaIaSumaIntentosHastaQuedarEnError` |
| 3 | 500 o tiempo agotado | `siLaIaNoRespondeNingunoCambiaDeEstadoYSumanIntentos` (4 vueltas: siguen `PENDIENTE`, intentos 1 a 4) y, en el cliente, `un500…`, `unTiempoAgotado…` y `unaClaveRechazada…` |
| 4 | Un mensaje cambió mientras se clasificaba | `siElMensajeCambioMientrasTantoNoSeGuardaElResultadoViejo` (el resultado viejo se descarta y se clasifica el texto nuevo en la vuelta siguiente) |
| 5 | Mensajes en `OK` o `ERROR` | `losMensajesOkOErrorNoSeVuelvenAEnviar` |
| 6 | Más pendientes que la tanda | `masPendientesQueLaTandaSeProcesanEnVariasVueltas` (7 → 5 + 2) |
| 7 | La V2 rechaza tema o sentimiento | `laV2RechazaTemaOSentimientoFueraDeLaLista`, `unaEtiquetaFueraDeLaListaCuentaComoErrorDeLaIa` |
| 8 | T01 y T03 siguen pasando | `ModeloDatosTest` 10/10 y `LotesApiTest` 19/19 (17 de T03, más NUL y `servidor_id`) |
| extra | 422 | `un422PenalizaSoloAlMensajeQueLaIaSenala`, `un422SinIndicarElMensajePenalizaATodos` |
| extra | Mensajes anteriores a V2 | `losMensajesSinServidorNoSeTomanYSeCuentan` |
| extra | Carácter NUL | `elCaracterNulSeQuitaDelTextoYDeLaCaja` |
| Python | S2 | `test_sin_clave_es_401_y_no_llama_al_llm`, `test_con_clave_incorrecta_es_401`, `test_sin_clave_configurada_en_la_ia_se_rechaza_todo`, `test_la_clave_se_revisa_antes_que_el_cuerpo`, `test_health_no_pide_clave`, `test_el_json_schema_incluye_el_error_no_autorizado`; `/procesar` sigue igual (`test_procesar_viejo_sigue_respondiendo_con_su_formato`) |

**Prueba real (Harrison y el chat de tarea, 2026-10-04, Gemini real)**

```
generar_api_key.py --cliente ia        ✅ Clave nueva escrita en .env (API_KEY_IA)
docker compose up -d --build           api-java, ia y postgres (healthy)
Flyway (registro de api-java)          Migrating schema "public" to version "2 - clasificacion" · Successfully applied
Clasificación (al arrancar)            WARN 39 mensajes PENDIENTE no tienen servidor_id (llegaron antes de V2)
send_batch.py                          ✅ total 39 (nuevos 0, actualizados 39, sin cambios 0)   ← se completó servidor_id
Clasificación (registro de api-java)   tomados 5, OK 5, ERROR 0, reintento 0, cambiaron 0 · 5097 ms
                                       … 7 tandas de 5 y 1 de 4, todas OK, entre 3,2 y 5,3 s cada una
```

Consulta de solo lectura en la base principal (la corrió el chat de tarea):

```
 estado | metodo | intencion    | count        tema                 | count     sentimiento  | count
 OK     | llm    | COMENTARIO   |     9        contenido_curso      |    10     NEUTRO       |    13
 OK     | llm    | OTRO         |     3        comunidad            |     7     MUY_POSITIVO |    11
 OK     | llm    | PREGUNTA_FAQ |    16        herramientas_entorno |     7     POSITIVO     |     7
 OK     | llm    | TESTIMONIO   |     9        evaluaciones         |     5     NEGATIVO     |     4
 OK     | regla  | OTRO         |     2        proyectos            |     3     MUY_NEGATIVO |     2
                                               empleo / otro        | 2 / 2     (vacío)      |     2
                                               calendario_clases    |     1
                                               (vacío)              |     2
 intentos: mínimo 1 y máximo 1 · con reserva: 0 · sin clasificado_en: 0
```

Los 2 mensajes con `metodo = regla` son los 2 sin texto: no gastaron el LLM y quedaron sin sentimiento ni tema, como dice el contrato. En el registro de `ia` no hay ningún rechazo por clave.

## 5. Decisiones que se tomaron

👤 Las 7 fueron validadas por Harrison el 2026-10-04 ("ok a todo"). También validó quitar el carácter NUL al recibir, en vez de rechazar el lote.

| Decisión | Alternativas descartadas | ¿Cambia el contrato, la arquitectura o D1 a D7? |
|---|---|---|
| **Reserva con `reservado_hasta`** (columna extra en V2): una sentencia toma la tanda con `SKIP LOCKED` y la marca por 2 min; la IA se llama sin transacción abierta | Dejar la transacción abierta los ~30 s de la IA (bloquea el upsert de la ingesta, y el caso 4 ni podría pasar) | No |
| `servidor_id` admite vacío; los mensajes sin servidor se saltan y se avisa en el registro; el reenvío lo completa | Recrear la base; inventar un servidor | No |
| 422: solo los mensajes señalados en `errores[].campo` suman intento y pasan a `ERROR` al máximo | Penalizar a toda la tanda; reintentar sin fin | No |
| Fallo de toda la llamada (401, 500, tiempo agotado, IA caída): suman un intento, siguen `PENDIENTE` y se libera la reserva | — (es lo que dice la ficha) | No |
| **`NO_AUTORIZADO` (401) en el contrato Java ↔ IA**; la clave se revisa en un *middleware*, antes que el cuerpo | Revisarla dentro de la ruta (un JSON roto daría 422 antes que 401) | ⚠️ **Agrega** un código de error al contrato Java ↔ IA. No cambia nada de lo que existía |
| Un cambio de texto vuelve los intentos a 0 | Conservar los intentos del texto viejo | No |
| `generar_api_key.py --cliente ia` | Escribir la clave a mano | No |
| El NUL se quita de **todos** los textos del lote (también de la caja y de los nombres) | Rechazar el lote con 422 | No |

## 6. Dudas, riesgos y pendientes

1. **Ritmo de clasificación.** Con la configuración actual (tandas de 5, 30 s de espera después de cada tanda), los 39 mensajes tardaron unos 5 minutos. 🔎 Para la demo alcanza. Si hiciera falta más rápido, se ajustan `clasificacion.tanda` e `intervalo-ms` sin tocar código, cuidando el límite de pedidos por minuto de Gemini (F15).
2. **Un fallo largo de la IA suma intentos sin pasar a `ERROR`**, como pide la ficha. Cuando vuelve, un mensaje que ya superó el máximo pasa a `ERROR` con el primer `ERROR` de la IA, sin otra oportunidad. 🔎 Es un caso raro; si molesta, se puede no contar los fallos de la llamada completa.
3. **Los mensajes `ERROR` no se reintentan solos.** El panel (fase 5) debería poder devolverlos a `PENDIENTE`.
4. **La razón de un `ERROR` solo queda en el registro**, no en la base (no hay columna). Si el panel quiere mostrarla, hace falta una columna en una `V3`.
5. **El mensaje que avisa de los mensajes sin `servidor_id`** se emite solo cuando cambia la cantidad, para no repetirse cada 30 s. En la prueba real apareció al arrancar y desapareció después del reenvío.
6. **El comando de la prueba real de T02** (`curl … /v1/procesar`, en `T02-informe.md`) ahora necesita `-H "X-Api-Key: …"`. Solo afecta si alguien lo repite a mano.
7. **PowerShell y la tilde:** `docker compose logs api-java | Select-String "Clasificación"` no encuentra nada porque PowerShell lee la salida con otra codificación. Sirve `Select-String "Clasificaci"`. 🔎 Conviene anotarlo en `OPERACION.md` (chat principal).
8. **Pendiente de antes, para otra ficha:** el tope total por pedido de la IA en `tiempoReal` (observación de T02) sigue fuera de alcance, junto con C2.

## 7. Comandos que ejecutó Harrison

Desde la raíz del repositorio, salvo donde se indica:

| # | Comando | Resultado (🧪) |
|---|---|---|
| 1 | `git switch -c tarea/T04-clasificacion-java-ia` (y los anteriores de la ficha §7) | Rama creada antes de empezar |
| 2 | `python scripts\generar_api_key.py --cliente ia` | `✅ Clave nueva escrita en .env (API_KEY_IA).` |
| 3 | `docker compose up -d --build` · `docker compose ps` | Imágenes reconstruidas; `ia` y `postgres` `healthy`, `api-java` arrancando |
| 4 | Desde `ingestion\discord`: `build_batch.py` y `send_batch.py` | `total 39 (nuevos 0, actualizados 39, sin cambios 0)` |
| 5 | `docker compose logs api-java \| Select-String "Clasificación"` y la consulta | Sin resultados por la tilde y la consulta cortada. El chat de tarea repitió las dos (sección 4) |
| 6 | `git add …` y `git commit` | Commit de la tarea |

El chat de tarea corrió las pruebas de Java y de Python, la prueba de la falla provocada a propósito, la prueba del script con un `.env` falso, el control en segundo plano que esperó el fin de la clasificación y las consultas de solo lectura.
