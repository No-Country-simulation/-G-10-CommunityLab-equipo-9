# Informe de la tarea T01 — Modelo de datos nuevo con Flyway

| Dato | Valor |
|---|---|
| Fecha | 2026-10-03 |
| Modelo de Claude usado | Opus 5.5 (`claude-opus-5-5`) |
| Rama | `tarea/T01-modelo-datos` |
| Commits | Uno: `feat(backend): modelo de datos nuevo con Flyway y upsert de mensajes (T01)` (ver `git log`) |

## 1. Resumen

La API Java ya no usa el modelo "un paquete por lote": ahora tiene `lotes_recibidos`, `mensajes` (una fila por mensaje, con la caja jsonb y las etiquetas de la IA) y `borradores`, creadas por la migración Flyway `V1`, con `ddl-auto=validate`. El upsert por `discord_id` no duplica, no pisa las etiquetas de la IA y vuelve a `PENDIENTE` si el texto cambió. **11 pruebas pasan** contra PostgreSQL 17 real. Se borró el modelo viejo con su puerta HTTP: hasta T03, `send_batch.py` no tiene a dónde enviar.

## 2. Criterios de terminado

| Criterio | Estado | Evidencia |
|---|---|---|
| V1 crea las 3 tablas con sus restricciones e índices, y Flyway la aplica en una base vacía | ✅ | 🧪 Base `insightedu_test` recién creada: *"Migrating schema "public" to version "1 - modelo inicial""* · *"Successfully applied 1 migration"*. Prueba `flywayAplicoV1ConTablasEIndices` |
| `ddl-auto=validate`, y la aplicación arranca en Docker con `/actuator/health` en `UP` | ✅ | 🧪 Base principal recreada (sección 7). Registro de `api-java`: *"Current version of schema "public": << Empty Schema >>"* → *"Successfully applied 1 migration … now at version v1"* → *"Started BackendJavaApplication in 3.647 seconds"*. `docker compose ps`: `api-java … (healthy)`. `curl.exe http://127.0.0.1:8008/actuator/health` → `{"status":"UP"}`. En la base `insightedu` quedan las tablas `borradores`, `flyway_schema_history`, `lotes_recibidos` y `mensajes`, y la versión 1 marcada como aplicada con éxito |
| El upsert cumple los casos 2 a 5 | ✅ | 🧪 `mensajeNuevoCreaUnaFila`, `reenvioConMasReaccionesActualizaLaCaja`, `reenvioNoPisaLasEtiquetasDeLaIa`, `textoCambiadoVuelveAPendiente` |
| El modelo viejo está eliminado y todo compila | ✅ | 🧪 `mvn test` compila sin errores. 💻 `git status`: 15 archivos viejos borrados |
| Las pruebas pasan con `mvn test` en el contenedor | ✅ | 🧪 `Tests run: 11, Failures: 0, Errors: 0, Skipped: 0` · `BUILD SUCCESS` (sección 4) |
| El informe `docs/tareas/T01-informe.md` está completo | ✅ | Este archivo. El hash del commit se ve con `git log` en la rama |
| No se tocó nada fuera del alcance | ✅ | 💻 `git status`: solo cambian `backend-java/` y este informe. No se tocó `agents/`, `panel/`, `ingestion/` ni `compose.yml` |

## 3. Archivos cambiados

Rutas Java relativas a `backend-java/src/main/java/com/insightedulab/backend_java/`.

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `backend-java/pom.xml` | + `flyway-core` y `flyway-database-postgresql`, sin versión: usa la que fija Spring Boot 3.4 | Alcance 1 |
| `backend-java/src/main/resources/application.properties` | `ddl-auto=update` → `validate` | Alcance 1: las tablas las crea Flyway; Hibernate solo comprueba que coincidan |
| `backend-java/src/main/resources/db/migration/V1__modelo_inicial.sql` | Nuevo: 3 tablas, `CHECK`, 4 índices de la ficha más 1 en `borradores(mensaje_id)` | Alcance 2 |
| `model/LoteRecibido.java`, `Mensaje.java`, `Borrador.java` | Nuevas entidades. La caja se mapea con `@JdbcTypeCode(SqlTypes.JSON)` como `Map<String, Object>` | Alcance 3 |
| `model/enums/` (7 enums) | `AutorTipo`, `AutorRol`, `ModoLote` (nombres del contrato) · `Intencion`, `EstadoClasificacion`, `TipoBorrador`, `EstadoBorrador` | Alcance 3 |
| `repository/MensajeRepository`, `BorradorRepository`, `LoteRecibidoRepository` | Repositorios JPA | Alcance 3 |
| `repository/MensajeUpsertRepository.java` | Nuevo: `INSERT … ON CONFLICT (discord_id) DO UPDATE`, que devuelve `NUEVO`, `ACTUALIZADO` o `SIN_CAMBIOS` | Alcance 4 (F1, F2, F3) |
| `controller/`, `service/`, `dto/` (9 archivos), `model/Interaction`, `model/PackageResult`, 2 enums y 2 repositorios viejos | Borrados | Alcance 5 |
| `backend-java/src/test/java/.../ModeloDatosTest.java` | Nuevo: 10 pruebas | Alcance 6 |

## 4. Pruebas

| Comando ejecutado | Resultado (🧪) |
|---|---|
| `docker compose exec -T postgres sh -c 'dropdb … insightedu_test && createdb … insightedu_test'` | Base de pruebas vacía |
| `docker run --rm --network insightedu_default --env-file .env -e POSTGRES_HOST=postgres -e POSTGRES_DB=insightedu_test -v "<raíz>/backend-java:/app" -v insightedu-maven:/root/.m2 -w /app maven:3.9-eclipse-temurin-21 mvn test` | 11 pruebas, 0 fallos, `BUILD SUCCESS` |

```
FlywayExecutor : Database: jdbc:postgresql://postgres:5432/insightedu_test (PostgreSQL 17.11)
DbValidate     : Successfully validated 1 migration
DbMigrate      : Migrating schema "public" to version "1 - modelo inicial"
DbMigrate      : Successfully applied 1 migration to schema "public", now at version v1
Tests run: 1,  Failures: 0, Errors: 0, Skipped: 0 -- in BackendJavaApplicationTests
Tests run: 10, Failures: 0, Errors: 0, Skipped: 0 -- in ModeloDatosTest
Tests run: 11, Failures: 0, Errors: 0, Skipped: 0
BUILD SUCCESS
```

Las pruebas y los casos de la ficha:

| # | Caso de la ficha | Prueba |
|---|---|---|
| 1 | Flyway aplica V1 y la aplicación arranca con `validate` | `flywayAplicoV1ConTablasEIndices`, `contextLoads` |
| 2 | Mensaje nuevo | `mensajeNuevoCreaUnaFila` |
| 3 | Más reacciones → 1 fila, "actualizado", caja nueva | `reenvioConMasReaccionesActualizaLaCaja` |
| 4 | Etiquetas intactas (F2) | `reenvioNoPisaLasEtiquetasDeLaIa` |
| 5 | Texto cambiado → `PENDIENTE` | `textoCambiadoVuelveAPendiente` |
| 6 | `CHECK` rechaza valores inventados | `checkRechazaEstadoDeBorradorInventado`, `checkRechazaTipoDeAutorFueraDelContrato`, `checkExigeMensajeSalvoEnFaq` |
| extra | Reenvío idéntico → `SIN_CAMBIOS` | `reenvioIdenticoNoReescribeLaFila` |
| extra | Las entidades JPA guardan y leen en las tablas de V1 | `entidadesSeGuardanConJpa` |

**Freno de seguridad:** `ModeloDatosTest` vacía las tablas antes de cada prueba, así que solo corre si la base se llama `*_test`. Si alguien se olvida de `-e POSTGRES_DB=insightedu_test`, la prueba falla sin borrar nada.

## 5. Decisiones que se tomaron

Todas validadas por Harrison el 2026-10-03 ("ok a todo").

| Decisión | Alternativas descartadas | ¿Cambia el contrato, la arquitectura o D1 a D7? |
|---|---|---|
| `CHECK` solo en los valores ya definidos: `modo`, `autor_tipo`, `autor_rol`, `estado_clasificacion`, `intencion`, `tipo` y `estado` del borrador, y `confianza` entre 0 y 1. `sentimiento`, `tema` y `estado_oci` quedan como texto libre | Inventar ahora sus listas y corregirlas después | No. Cuando la fase 3 (IA) y la fase 6 (OCI) definan sus valores, se agregan en una migración `V2` |
| `borradores.mensaje_id` es obligatorio salvo en el tipo `FAQ` (`CHECK`) | Obligatorio siempre (no sirve para la FAQ semanal) o siempre opcional (permite borradores sin origen) | No |
| El upsert devuelve `NUEVO` / `ACTUALIZADO` / `SIN_CAMBIOS`. Si llega idéntico, no se reescribe la fila | Contar todo reenvío como "actualizado" | No. `lotes_recibidos` no cambia: sin cambios = `total − nuevos − actualizados` |
| Enums con los nombres exactos del contrato (`persona`, `botPropio`, `historial`…) | MAYÚSCULAS con un conversor | No: se respeta el contrato tal cual |
| Nuevo vs. actualizado con `RETURNING (xmax = 0)` | `MERGE … RETURNING merge_action()` de PostgreSQL 17 | No. 🔎 `MERGE` no protege contra dos escrituras simultáneas como `ON CONFLICT` (F3), y la ficha pide `ON CONFLICT` |
| Índice extra en `borradores(mensaje_id)` | Solo los 4 de la ficha | No. 🔎 PostgreSQL no indexa solo las claves foráneas, y el panel va a buscar los borradores de cada mensaje |
| `@Column(name = "responde_a")` explícito | — | No. 🧪 Spring convertía `respondeA` en `respondea` (no pone `_` ante una mayúscula final), y `validate` falló hasta corregirlo |

## 6. Dudas, riesgos y pendientes

1. **La ingesta no tiene a dónde enviar hasta T03.** `ingestion/discord/send_batch.py` y `.env.example` apuntan a `POST /api/v1/community/process`, que se borró con `CommunityController`, como pide el alcance 5. T03 debe crear la puerta nueva y decidir si mantiene esa ruta.
2. **La caja se recibe como `Map<String, Object>`.** T03 decide si el DTO de entrada la lee como `Map` o como `JsonNode`. `MensajeUpsertRepository.DatosMensaje` espera un `Map`.
3. **`lotes_recibidos` y `mensajes` no están vinculados**: un mensaje puede llegar en muchos lotes. Si el panel necesita saber "en qué lote llegó", hace falta una tabla intermedia (`V2`).
4. **`docs/OPERACION.md`** no menciona Flyway ni la base `insightedu_test`. Queda para el chat principal, porque no estaba en el alcance.
5. 🔎 Los adjuntos traen una URL que cambia en cada extracción (`?ex=…`). Por eso, un mensaje con adjunto siempre va a dar `ACTUALIZADO`, nunca `SIN_CAMBIOS`. No es un error, pero infla el número de `actualizados`.

## 7. Comandos que ejecutó Harrison

Desde la raíz del repositorio, en este orden:

| # | Comando | Resultado (🧪) |
|---|---|---|
| 1 | `git switch -c tarea/T01-modelo-datos` (y los anteriores de la ficha §7) | Rama creada antes de empezar |
| 2 | `docker compose stop api-java` | Detenido |
| 3 | `docker compose exec postgres sh -c 'dropdb --force -U "$POSTGRES_USER" "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'` | Base principal vacía (tenía solo tablas viejas de prueba) |
| 4 | `docker compose up -d --build api-java` | Imagen compilada en 180 s, contenedor recreado |
| 5 | `docker compose ps` | `api-java … Up 38 seconds (healthy)` |
| 6 | `curl.exe http://127.0.0.1:8008/actuator/health` | `{"status":"UP"}` |
| 7 | `git add backend-java docs/tareas/T01-informe.md` y `git commit` | Commit de la tarea |

El chat de tarea creó la base `insightedu_test` (`createdb`) y corrió `mvn test` en un contenedor, con permiso de Harrison.
