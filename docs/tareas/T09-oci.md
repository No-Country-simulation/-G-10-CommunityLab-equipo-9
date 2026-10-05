# T09 · OCI: guardar los borradores generados y los aprobados en Oracle Cloud

| Dato | Valor |
|---|---|
| Fase del plan | 6 · OCI y despliegue ([análisis §9](../ANALISIS_INGENIERIA_PROPUESTA_3.md#9-prioridades-y-orden)) |
| Objetivos | **OE7** (guardar en OCI los activos generados y los aprobados). Es un requisito del brief: *"persistir todos los paquetes de activos generados en un Bucket Always Free"* |
| Hallazgos y decisiones que resuelve | N7, D2 (DEC-21: `generados/` y `aprobados/`), F10 (JSON con Jackson), F11 (solo lo aprobado va a `aprobados/`), S4 y DEC-41 (una PAR nueva) |
| Tamaño | S–M (una tarea en segundo plano en Java, una migración y documentación) |
| Modelo de Claude recomendado | **Sonnet 5.5**: es acotada y copia el patrón de las tareas en segundo plano de T04 y T06 |
| Depende de | T06, T06b y T07 ✅ (los borradores y su aprobación). Requisito de Harrison: **una URL PAR nueva** (sección 5) |
| Rama | `tarea/T09-oci` |
| Decisiones previas 👤 | Las de la sección 1.1, validadas por Harrison el 2026-10-04 |

## 1. Objetivo

Que cada borrador (post de LinkedIn, caso de éxito o FAQ) quede guardado como un archivo JSON en el bucket de OCI:
- **en `generados/`** cuando se crea;
- **en `aprobados/`** cuando una persona lo aprueba en el panel.

Una tarea en segundo plano lo sube con reintentos, así que **si OCI está caído, generar y aprobar siguen funcionando**.

💻 Hoy no existe código que suba a OCI: el `CommunityService` viejo se eliminó en T01, junto con sus fallas (F10 y F11). La tabla `borradores` ya tiene las columnas `estado_oci` y `ruta_oci` (V1).

### 1.1 Decisiones previas 👤 (2026-10-04)

| # | Pregunta | Decisión | Descartada |
|---|---|---|---|
| 1 | ¿Cuándo se sube? (DEC-127) | **En segundo plano, con reintentos** (una tarea programada que sube lo pendiente) | Subir en el momento de aprobar: si OCI falla, la aprobación falla |
| 2 | ¿Qué va en el archivo? (DEC-128) | **El borrador y sus datos:** id, tipo, texto de la IA, texto final, estado, fechas, quién aprobó, consentimiento, tiempo de curaduría, el motivo de la IA y, en la FAQ, la semana. **Sin datos de Discord del alumno** (ni `nombreUsuario`, ni IDs de Discord, ni el mensaje original completo). El primer nombre y la cita ya van dentro del texto | Agregar el mensaje original completo |
| 3 | ¿Qué URL PAR se usa? (DEC-129) | **Una nueva, creada por Harrison**: de **solo escritura** sobre el bucket y **con vencimiento** después de la entrega. La que estaba en el `.env` se la pasó un compañero, y no se sabe si es la que quedó en el historial público (S4): **no se usa** | Usar la del compañero |
| 4 | ¿Se suben los registros de la IA? (DEC-130) | **No** (🟡): la IA necesitaría sus propias credenciales de OCI, y el brief exige los activos | Incluirlos |

Decisiones del chat principal (Harrison no se opuso), **DEC-131**:
- los borradores **rechazados** no van a `aprobados/` (sí estuvieron en `generados/`);
- los borradores que **ya existen** (unos 13) se suben la primera vez que corra la tarea;
- el código viejo de OCI de la IA (`agents/orquestador/storage/`) no se toca.

## 2. Contexto que hay que leer

| Qué | Dónde |
|---|---|
| N7: Java sube los activos aprobados a OCI | [PDF de la propuesta 3](../referencias/Propuesta_3_Arquitectura_InsightEdu.pdf), §6 (N7) |
| D2, S4, F10 y F11 | [Análisis](../ANALISIS_INGENIERIA_PROPUESTA_3.md) §0, §3 y §4 |
| Cómo se sube con una PAR de bucket: 📘 `PUT https://objectstorage.<región>.oraclecloud.com<access-uri>/<nombre-del-objeto>`, con el archivo en el cuerpo | [Documentación de Oracle: PAR de bucket](https://docs.oracle.com/en-us/iaas/Content/Object/Tasks/usingpreauthenticatedrequests_topic-To_create_a_preauthenticated_request_for_all_objects_in_a_bucket.htm) |
| El patrón que hay que copiar: tarea programada, reserva, reintentos, registros sin textos | `backend-java/.../generacion/` ([T06-informe.md](T06-informe.md)) |
| La tabla `borradores` y sus estados | V1, V6 y `model/Borrador.java` |
| Las conexiones de las pruebas de Java (no abrir otro grupo de conexiones) | [CHAT_PRINCIPAL.md §5](../CHAT_PRINCIPAL.md), fila "Conexiones en las pruebas de Java" |

## 3. Alcance: qué entra

1. **Migración `V8__…`** (nunca editar de V1 a V7). Hace falta seguir **dos subidas por borrador**, la de `generados/` y la de `aprobados/`, cada una con su estado (por ejemplo, `PENDIENTE`, `SUBIDO` o `ERROR`), su ruta, sus intentos, su reserva y su fecha. La forma la elige el chat de tarea: columnas nuevas, o una tabla de subidas. Las columnas viejas `estado_oci` y `ruta_oci` se reutilizan o se documentan como reemplazadas.
2. **Tarea programada de subida** (`@Scheduled`, con intervalo, tanda y máximo de intentos configurables):
   - **`generados/`:** todo borrador que todavía no se subió ahí;
   - **`aprobados/`:** solo los borradores con `estado = APROBADO` (F11). Se sube la versión aprobada, con `texto_final`;
   - reserva con `SKIP LOCKED`, sube **sin transacción abierta** y guarda el resultado con una guarda;
   - si falla, suma un intento; al máximo, `ERROR`. Una PAR vacía **no** es un error de cada borrador: la tarea no hace nada y lo avisa en el registro una sola vez.
3. **El archivo JSON:**
   - se arma con **Jackson** a partir de un objeto (F10), nunca a mano con `String.format`;
   - el contenido es el de DEC-128;
   - el nombre del objeto es estable y legible, por ejemplo, `generados/POST_LINKEDIN/2026-10-04/borrador-12.json` y `aprobados/…`;
   - se envía con `Content-Type: application/json`.
4. **El cliente de OCI:**
   - `PUT` a la PAR más el nombre del objeto (📘), con tiempos máximos (por ejemplo, 5 s para conectar y 30 s para leer);
   - **la URL PAR nunca se escribe en el registro**, ni completa ni recortada, porque es una credencial: solo el nombre del objeto y el código HTTP;
   - se valida al arrancar que la PAR empiece con `https://objectstorage.` y termine en `/o/`, sin mostrarla.
5. **Panel (opcional y pequeño):** en el detalle de un borrador, mostrar si ya está en OCI (solo el estado, sin la ruta completa ni la PAR). Si toca `PANEL_JAVA_v1`, el cambio solo agrega.
6. **`docs/OPERACION.md`:** cómo crear la PAR (la guía de la sección 5), dónde pegarla, cómo comprobar en la consola de Oracle que llegaron los archivos y cómo reintentar los `ERROR`.

## 4. Fuera de alcance

- Los registros de la IA en OCI (DEC-130) y el código viejo `agents/orquestador/storage/`.
- Borrar o actualizar archivos en OCI: la PAR es de solo escritura. Si un borrador cambia después de subirlo a `generados/`, no se vuelve a subir.
- Leer desde OCI o publicar en LinkedIn.
- Revocar la PAR vieja del historial (DEC-41: riesgo aceptado).
- **No ejecutar `simulate_students.py`** ni encender un segundo bot.

## 5. Pruebas exigidas

**Java** (PostgreSQL real y un servidor OCI simulado, por ejemplo con `MockRestServiceServer`). **Reutilizar las propiedades de una prueba existente**, para no abrir otro grupo de conexiones:

| # | Caso | Resultado esperado |
|---|---|---|
| 1 | Un borrador nuevo | Se sube a `generados/` con `PUT`, JSON válido y el nombre esperado |
| 2 | Un borrador aprobado | Se sube también a `aprobados/`, con `texto_final` |
| 3 | Un borrador rechazado o pendiente | **No** va a `aprobados/` (F11) |
| 4 | Un texto con comillas, saltos de línea, emojis y `\` | El JSON sigue siendo válido (F10) |
| 5 | OCI responde 500 o no responde | Suma un intento y sigue pendiente; al máximo, `ERROR` |
| 6 | Dos ejecuciones a la vez | No suben dos veces lo mismo |
| 7 | Sin PAR configurada | No llama a nada, avisa una vez y no marca errores |
| 8 | El JSON | No contiene `nombreUsuario`, IDs de Discord ni el mensaje original |
| 9 | El registro | No contiene la URL PAR |
| 10 | Las 169 pruebas anteriores | Siguen pasando |

**Prueba real, la corre Harrison** (no gasta Gemini):

1. **Crear la PAR** (📘 documentación de Oracle):
   1. Entrar a la consola de OCI con una cuenta que tenga acceso al bucket.
   2. Ir a **Storage → Buckets** y abrir el bucket.
   3. En **Management** (o "Recursos"), buscar **Pre-authenticated requests** → **Create pre-authenticated request**.
   4. Completar: **Name**, por ejemplo `insightedu-t09`; **Target**: **Bucket**; **Access type**: **Permit object writes** (solo escritura); **Enable object listing**: **no** marcar; **Expiration**: por ejemplo, el 2026-11-30.
   5. Pulsar **Create** y **copiar la URL en ese momento**: 📘 *"The URL is displayed only at the time of creation… You can't access and retrieve it again"*.
2. Pegarla en el `.env` de la raíz, en `OCI_PAR_URL=`, reemplazando la del compañero. **No pegarla en el chat.**
3. `docker compose up -d --build api-java` y esperar un par de minutos.
4. En la consola de Oracle, abrir el bucket y comprobar que aparecen las carpetas `generados/` y `aprobados/` con los archivos. Abrir uno y revisar que no tenga datos de Discord.
5. Aprobar un borrador nuevo en el panel y comprobar que aparece en `aprobados/`.
6. Consulta de solo lectura con los estados de subida. Se pega la salida en el informe (sin la PAR).

## 6. Criterios de terminado

- [ ] Cada borrador está en `generados/`, y cada aprobado también en `aprobados/`; los rechazados no.
- [ ] Los JSON se arman con Jackson, son válidos y no tienen datos de Discord del alumno.
- [ ] Un fallo de OCI no frena la generación ni la aprobación, y se reintenta hasta el máximo.
- [ ] La URL PAR no aparece en ningún registro ni en el informe.
- [ ] Las pruebas pasan y la prueba real muestra los archivos en el bucket (🧪 en el informe).
- [ ] El informe `docs/tareas/T09-informe.md` está completo, y no se tocó nada fuera del alcance.

## 7. Comandos de git para Harrison

**Al empezar**, desde `C:\Users\LENOVO\Documents\Cursos\No Country\Hackaton ONE 10\insightedu-lab`, **después de subir la ficha** y con `git status` en `working tree clean`:
```
git switch feature/integracion-arquitectura-3
git pull
git switch -c tarea/T09-oci
```

**Al terminar:** el chat de tarea da los comandos de commit (un solo `-m`, **sin** `Co-Authored-By`: DEC-65). Después:
```
git push -u origin tarea/T09-oci
```

Luego le dices al chat principal **"T09 terminó"**.

## 8. Cómo abrir el chat de esta tarea

1. En VS Code, abrir un chat nuevo de Claude Code **en esta misma carpeta**.
2. Elegir el modelo **Sonnet 5.5** con `/model`.
3. Primer mensaje: *"Eres el chat de la tarea T09. Lee CLAUDE.md y docs/tareas/T09-oci.md y empieza."*

⚠️ **Nunca pegues en el chat la URL PAR ni el contenido de un `.env`.** La PAR es una credencial: quien la tenga puede escribir en el bucket.
