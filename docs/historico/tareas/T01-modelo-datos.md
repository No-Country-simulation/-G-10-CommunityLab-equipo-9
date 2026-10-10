# T01 · Modelo de datos nuevo con Flyway

| Dato | Valor |
|---|---|
| Fase del plan | 2 · Datos y captura ([análisis §9](../ANALISIS_INGENIERIA_PROPUESTA_3.md#9-prioridades-y-orden)) |
| Objetivos | OE1, y es la base de OE2, OE3, OE5, OE6 y OE7 |
| Tamaño | M |
| Modelo de Claude recomendado | **Opus 5.5**: define la base sobre la que se construye todo lo demás |
| Depende de | Nada |
| Rama | `tarea/T01-modelo-datos` |

## 1. Objetivo

Reemplazar el modelo de datos de la API Java, que hoy guarda **un paquete por lote** con un solo post, por el modelo de la [sección 5 del análisis](../ANALISIS_INGENIERIA_PROPUESTA_3.md#5-datos). El modelo nuevo tiene tres tablas:

- **lotes recibidos**;
- **una fila por mensaje**, con las etiquetas de la IA;
- **borradores**, con su estado de aprobación.

Las tablas se crean con **migraciones Flyway** (archivos SQL versionados), no con Hibernate.

## 2. Contexto que hay que leer

| Qué | Dónde |
|---|---|
| El modelo propuesto, los índices y las migraciones | Análisis §5. Es la base aprobada; los nombres de columnas se pueden ajustar para que coincidan con el contrato |
| Duplicados, etiquetas que no se deben pisar y escrituras al mismo tiempo | Análisis F1, F2 y F3 |
| Nombres y valores del contrato v1 | [CONTRACT.md](../../../ingestion/discord/docs/CONTRACT.md) y [contract.py](../../../ingestion/discord/contract.py). Por ejemplo: tipo de autor `persona` / `botPropio` / `otroBot`; `es_simulado`; rol `miembro` / `mentor` / `staff`; modo `historial` / `tiempoReal`; `version_contrato` `"1.0"` |
| La "caja" de la opción C (el mensaje completo del contrato en `jsonb`) | [INGESTION_GUIDE.md §11](../ingesta/INGESTION_GUIDE.md) |
| El código actual | `backend-java/src/main/java/com/insightedulab/backend_java/` (`model/`, `repository/`, `service/CommunityService.java`, `controller/CommunityController.java`, `dto/`) |

## 3. Alcance: qué entra

1. **Flyway:** agregar `flyway-core` y `flyway-database-postgresql`, con las versiones que fija Spring Boot. Cambiar a `spring.jpa.hibernate.ddl-auto=validate`.
2. **`V1__modelo_inicial.sql`**, con tres tablas:

   | Tabla | Columnas mínimas |
   |---|---|
   | `lotes_recibidos` | `lote_id` (único), `modo`, `version_contrato`, `recibido_en`, `total`, `nuevos`, `actualizados` |
   | `mensajes` | `discord_id` (**único**), `canal_id`, `autor_id`, `autor_tipo`, `autor_rol`, `es_simulado`, `fecha` (`timestamptz`), `responde_a`, `texto` (puede estar vacío), `contrato` (`jsonb`: la caja completa), `version_contrato`, `primera_vez_visto`, `actualizado_en`. Etiquetas de la IA: `intencion`, `confianza`, `sentimiento`, `tema`, `estado_clasificacion` (`PENDIENTE` / `OK` / `ERROR`), `clasificado_en` |
   | `borradores` | `id`, `mensaje_id` (clave foránea), `tipo` (`POST_LINKEDIN` / `CASO_EXITO` / `FAQ` / `RESPUESTA_BOT`), `texto_ia`, `texto_final`, `estado` (`PENDIENTE` / `APROBADO` / `RECHAZADO`), `consentimiento_confirmado`, `aprobado_por`, `aprobado_en`, `tiempo_curaduria_seg`, `tokens_in`, `tokens_out`, `estado_oci`, `ruta_oci`, `creado_en` |

   Los valores cerrados se controlan con `CHECK`. Índices: `mensajes(autor_id, fecha)`, `mensajes(fecha)`, `mensajes(intencion)` y `borradores(estado)`.
3. **Entidades JPA y repositorios** para las tres tablas. El `jsonb` se mapea con `@JdbcTypeCode(SqlTypes.JSON)`.
4. **Upsert de mensajes** ("actualizar o insertar"), con `INSERT … ON CONFLICT (discord_id) DO UPDATE`:
   - actualiza **solo** los campos del mensaje: texto, caja, `actualizado_en`, etc.;
   - **nunca pisa las etiquetas de la IA** (F2);
   - si el texto cambió, vuelve a poner `estado_clasificacion = PENDIENTE`, para que se clasifique de nuevo;
   - indica si el mensaje fue **nuevo** o **actualizado**, para llenar `lotes_recibidos.nuevos` y `actualizados`.
5. **Quitar el modelo viejo:** `PackageResult`, `Interaction`, sus repositorios y lo que depende de ellos (`CommunityService`, `CommunityController` y sus DTOs).
   - Las puertas HTTP nuevas se hacen en T03 (lotes) y en las fases 5 y 6 (panel y OCI). El código viejo queda en el historial de git y en la rama de backend.
   - Se mantienen `NlpDataClient`, `RestClientConfig` y `CorsConfig`. La aplicación tiene que arrancar y `/actuator/health` responder `UP`.
6. **Pruebas** de la sección 5.

## 4. Fuera de alcance

- Puertas HTTP nuevas y API key (T03), llamada a la IA (T04), OCI (fase 6) y panel.
- Cambiar el contrato v1 o el código de la ingesta.
- Tocar `agents/`, `panel/`, `ingestion/` o `compose.yml`. Si hace falta algo mínimo para las pruebas, consultarlo antes con Harrison.

## 5. Pruebas exigidas

Con **PostgreSQL real**, porque `jsonb` y `ON CONFLICT` no existen en las bases de prueba en memoria como H2.

**Infraestructura sugerida** (el chat puede ajustarla y explicar por qué):
- una base `insightedu_test` dentro del contenedor `postgres` de compose;
- Maven corriendo en un contenedor conectado a la red `insightedu_default`;
- las credenciales con `--env-file .env`, así el chat nunca lee el `.env`.

Comandos de referencia para Harrison, desde la raíz del repositorio:
```
docker compose up -d postgres
docker compose exec postgres sh -c 'createdb -U "$POSTGRES_USER" insightedu_test'
docker run --rm --network insightedu_default --env-file .env -e POSTGRES_HOST=postgres -e POSTGRES_DB=insightedu_test -v "${PWD}\backend-java:/app" -v insightedu-maven:/root/.m2 -w /app maven:3.9-eclipse-temurin-21 mvn -q test
```

**Casos que tienen que estar cubiertos:**

| # | Caso | Resultado esperado |
|---|---|---|
| 1 | Flyway aplica V1 en una base vacía | La aplicación arranca con `validate` |
| 2 | Mensaje nuevo | 1 fila, marcada como "nuevo" |
| 3 | Mismo `discord_id` con más reacciones | Sigue habiendo 1 fila, marcada como "actualizado", con la caja nueva |
| 4 | Mensaje con etiquetas y luego reenviado | Etiquetas intactas (F2) |
| 5 | Reenvío con el texto cambiado | `estado_clasificacion` vuelve a `PENDIENTE` |
| 6 | Valor fuera de la lista (por ejemplo, un estado de borrador inventado) | Lo rechaza el `CHECK` |

⚠️ **Detalle conocido:** la base principal del compose ya tiene tablas viejas, que Hibernate creó con `update`. Flyway no migra un esquema que ya tiene tablas sin su historial. Para la base principal, dale a Harrison el comando para recrearla (es solo de prueba, no hay datos reales) y explícale qué hace.

## 6. Criterios de terminado

- [ ] V1 crea las 3 tablas con sus restricciones e índices, y Flyway la aplica en una base vacía.
- [ ] `ddl-auto=validate`, y la aplicación arranca en Docker con `/actuator/health` en `UP`.
- [ ] El upsert cumple los casos 2 a 5.
- [ ] El modelo viejo está eliminado y todo compila.
- [ ] Las pruebas pasan con `mvn test` en el contenedor (🧪 con la salida en el informe).
- [ ] El informe `docs/tareas/T01-informe.md` está completo.
- [ ] No se tocó nada fuera del alcance.

## 7. Comandos de git para Harrison

**Al empezar**, desde la carpeta raíz `C:\Users\LENOVO\Documents\Cursos\No Country\Hackaton ONE 10\insightedu-lab`:
```
git switch feature/integracion-arquitectura-3
git pull
git switch -c tarea/T01-modelo-datos
```

**Al terminar:** el chat de tarea da los comandos de commit, y después:
```
git push -u origin tarea/T01-modelo-datos
```

Luego Harrison le lleva el informe al **chat principal**. **No se fusiona hasta que la auditoría lo apruebe.**

## 8. Cómo abrir el chat de esta tarea

1. En VS Code, abrir un chat nuevo de Claude Code **en esta misma carpeta**.
2. Elegir el modelo **Opus 5.5** con el comando `/model`.
3. Primer mensaje: *"Eres el chat de la tarea T01. Lee CLAUDE.md y docs/tareas/T01-modelo-datos.md y empieza."*
