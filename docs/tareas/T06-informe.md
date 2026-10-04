# Informe de la tarea T06 — Agente-Mod: borradores de LinkedIn y casos de éxito con la voz de CommunityLab

| Dato | Valor |
|---|---|
| Fecha | 2026-10-04 |
| Modelo de Claude usado | Opus 5.5 (`claude-opus-5-5`) |
| Rama | `tarea/T06-agente-mod` |
| Commits | Dos, uno por parte (ver `git log`): `feat(ia): Agente-Mod y POST /v1/generar con la guia de voz (T06 parte A)` y `feat(backend): generacion de borradores en segundo plano y migracion V4 (T06 parte B)` |

## 1. Resumen

Cada logro de una persona (`TESTIMONIO`, `OK`) se convierte solo, sin que nadie lo pida, en un post de LinkedIn y un caso de éxito `PENDIENTE`, o en `NO_PUBLICABLE` con su motivo. El **Agente-Mod** (`agents/agent_mod/`) hace una llamada a Gemini con la **guía de voz aprobada por Harrison** y recibe solo el primer nombre del alumno. Java lo llama cada minuto por una puerta nueva, `POST /v1/generar`, con el mismo patrón de reserva y guardas de T04, y la migración `V4`. Pasan 54 pruebas de la IA, 96 de Java, 22 del bot y 36 de la ingesta. **Prueba real:** 12 logros procesados sin errores (5 generados y 7 no publicables, entre ellos "por fin entendí recursividad"), con 0 borradores con el nombre completo. A Harrison le gustó el tono.

## 2. Criterios de terminado

| Criterio | Estado | Evidencia |
|---|---|---|
| Existe el Agente-Mod, con la guía de voz aprobada por Harrison, y `/v1/generar` protegida con la clave | ✅ | `agents/agent_mod/agente_mod.py` y `guia_de_voz.md` (👤 "Apruebo la guía", 2026-10-04). 🧪 `test_sin_clave_es_401_y_no_llama_al_llm` |
| Cada logro publicable tiene sus dos borradores `PENDIENTE`, los no publicables tienen su motivo, y un fallo no deja nada a medias ni duplicado | ✅ | 🧪 `GeneracionTest` (14 pruebas). Prueba real: 5 × 2 borradores y 7 motivos (sección 4.4) |
| Ningún borrador lleva el nombre completo del alumno, y el LLM no lo recibe | ✅ | 🧪 `test_el_llm_recibe_solo_el_primer_nombre_y_ningun_dato_personal` y `test_si_el_alumno_escribio_su_nombre_completo_no_llega_al_borrador`. Prueba real: `con_nombre_completo = 0` |
| `JAVA_IA_v1.md` y su JSON Schema documentan `/v1/generar`, y `/v1/procesar` no cambió | ✅ | `JAVA_IA_v1.md` §9. El schema solo agrega: `git diff --stat` dio 799 líneas nuevas y 0 borradas |
| Las pruebas de Java y Python pasan, y la prueba real muestra los borradores en la base | ✅ | Secciones 4.1 a 4.4 |
| Informe completo; no se tocó nada fuera del alcance | ✅ | No se tocó el clasificador, el bot, el contrato v1, `/v1/procesar` ni V1, V2 o V3. Sin puertas de Java para los borradores (T07) |

## 3. Archivos cambiados

Rutas Java relativas a `backend-java/src/main/java/com/insightedulab/backend_java/`.

### Parte A · La IA

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `agents/agent_mod/agente_mod.py` | Nuevo: `AgenteMod` (una llamada con salida estructurada `RedaccionLLM`: `publicable`, `motivo`, `post_linkedin` y `caso_exito`), `construir_entrada` (solo el primer nombre, el canal, el texto, el total de reacciones y el rol y el texto de cada respuesta, con las menciones `<@123>` cambiadas por `@alguien`), `sin_nombre_completo` (última defensa) y `construir_agente_mod` | §3.1, DEC-53, DEC-81 y F4 |
| `agents/agent_mod/guia_de_voz.md` | Nuevo: tono, qué hacer siempre y nunca, qué logros se publican, y largo, emojis, hashtags y estructura de cada borrador. Basada en el Reglamento de Comunicaciones (§3: nombres completos; §4: Código de Honor) | §3.2, DEC-84. 👤 Aprobada por Harrison |
| `agents/agent_mod/__init__.py` | Nuevo (paquete) | — |
| `agents/orquestador/api.py` | `POST /v1/generar` (función `def`, como `/v1/procesar`, para no bloquear el servidor); el agente se crea una sola vez. El control de `X-Api-Key` de `/v1/…` ya lo cubre | §3.3 |
| `agents/orquestador/contrato_ia.py` | `PedidoGenerar` (máximo 20 respuestas) y `RespuestaGenerar` (con validación: un `ERROR` no lleva decisión ni textos, y un publicable lleva los dos). El schema suma la clave `generar` | §3.3 y §3.4 |
| `agents/orquestador/config.py` | `MOD_MODEL_NAME` (vacío = el del clasificador), `MOD_TIMEOUT_S` (25) y `MOD_TEMPERATURE` (0,7) | DEC-85 y D4 |
| `agents/orquestador/clasificadores/llm_models.py` | `build_llm(modelo, temperatura, timeout_s)`: sin argumentos funciona igual que antes | DEC-85 y D5 |
| `agents/orquestador/config_http.py` | `ENDPOINT_GENERAR_V1` | — |
| `agents/orquestador/tests/test_v1_generar.py` | Nuevo: 16 pruebas | §5 |
| `docs/contratos/JAVA_IA_v1.md` | Cabecera con el cambio de T06, §2 y §8 actualizados, y **§9 nueva** con la puerta, el pedido, qué ve el LLM, ejemplos, campos y qué hace Java | §3.4 |
| `docs/contratos/JAVA_IA_v1.schema.json` | Regenerado con `python -m agents.orquestador.contrato_ia` (solo agrega) | §3.4 |

### Parte B · Java

| Archivo | Qué cambió | Por qué |
|---|---|---|
| `backend-java/src/main/resources/db/migration/V4__generacion.sql` | Nuevo: `generacion_estado` (`CHECK`: `GENERADO`, `NO_PUBLICABLE` o `ERROR`), `generacion_motivo`, `generacion_intentos`, `generado_en` y `generacion_reservada_hasta`. Índice parcial `idx_mensajes_por_generar` e índice **único parcial** `uq_borradores_pendiente_por_tipo (mensaje_id, tipo) WHERE estado = 'PENDIENTE'` | §3.5 |
| `generacion/GeneracionService.java` | Nuevo: reserva la tanda y, por cada logro, arma el pedido (la caja y hasta 20 respuestas), llama a la IA sin transacción y guarda. Los dos borradores y `GENERADO` van en **una** transacción, con la guarda | §3.6 |
| `generacion/GeneracionRepository.java` | Nuevo: el SQL. Reserva con `FOR UPDATE SKIP LOCKED`; guarda `actualizado_en`, `TESTIMONIO`, `OK` y `generacion_estado IS NULL` | §3.6 |
| `generacion/GeneracionProgramada.java`, `GeneracionProperties.java`, `GeneracionConfig.java` | Nuevos: `@Scheduled` cada 60 s (con su propio `@EnableScheduling`, para que corra aunque la clasificación esté apagada), tanda 3, 3 intentos, reserva de 180 s y 20 respuestas. Registro solo con números | §3.6 y §3.7 |
| `client/NlpDataClient.java` | `generar(pedido, idCorrelacion)`. El envío se comparte con `procesar` (mismas cabeceras, tiempos y excepciones) | §3.6 |
| `client/RespuestaGenerar.java` | Nuevo | §3.6 |
| `application.properties` | `generacion.*` y `GENERACION_HABILITADA` | §3.6 |
| `test/…/GeneracionTest.java` | Nuevo: 14 pruebas | §5 |
| `test/…/NlpDataClientTest.java` | +2 pruebas de `generar()` con `MockRestServiceServer` | §5 |
| `test/…/BackendJavaApplicationTests`, `ClasificacionTest`, `EnVivoApiTest`, `LotesApiTest` y `ModeloDatosTest` | Solo la propiedad que apaga la generación (o la retrasa, en `BackendJavaApplicationTests`) | Sin esto, la tarea nueva podía tomar los logros `OK` que crean esas pruebas y llamar a la IA simulada |
| `compose.yml`, `.env.example` | `GENERACION_HABILITADA` para `api-java` y `MOD_MODEL_NAME` para `ia` | §3.8 |
| `docs/OPERACION.md` | Las dos variables y §8 nueva: cómo funciona, consultas de solo lectura (estados, borradores y la comprobación del nombre completo), cómo apagarla y cómo reintentar los `ERROR` | §3.8 |

## 4. Pruebas

| Comando ejecutado | Resultado (🧪) |
|---|---|
| `python -m pytest agents/orquestador/tests -q` | **54 passed**: las 38 de antes + 16 nuevas |
| Java, en Docker contra `insightedu_test` (OPERACION.md §5) | **96 pruebas, 0 fallas**: las 80 de antes + 14 de `GeneracionTest` + 2 de `NlpDataClientTest` |
| `python -m pytest agents/bot_discord/tests -q` | **22 passed** (sin cambios) |
| `python -m pytest -q` (desde `ingestion/discord`) | **36 passed** (sin cambios) |
| `docker compose config --quiet` | Sin errores |

### 4.1 IA (16 nuevas, `test_v1_generar.py`)

| # de la ficha | Pruebas |
|---|---|
| 1 · Publicable | `test_un_logro_publicable_trae_los_dos_textos` (y la respuesta cumple el schema) |
| 2 · Logro menor | `test_un_logro_menor_no_es_publicable_y_no_trae_textos`, `test_si_el_llm_dice_no_publicable_pero_igual_escribe_se_descartan_los_textos` |
| 3 · El LLM falla o tarda | `test_si_el_llm_falla_es_error_sin_textos` (sin el detalle del proveedor), `test_si_el_llm_no_responde_a_tiempo_es_error_y_no_espera`, `test_publicable_con_un_texto_vacio_es_error_y_no_un_borrador_a_medias`, `test_sin_llm_configurado_es_error` |
| 4 · Lo que recibe el LLM | `test_el_llm_recibe_solo_el_primer_nombre_y_ningun_dato_personal` (ni "Camila Rojas", ni el usuario, ni el nombre del mentor, ni IDs; sí el texto exacto, el rol y las reacciones), `test_si_el_alumno_escribio_su_nombre_completo_no_llega_al_borrador`, `test_el_primer_nombre_y_las_menciones`, `test_sin_nombre_respeta_las_palabras_enteras` |
| 5 · La guía llega desde el archivo | `test_la_guia_de_voz_llega_al_llm_desde_el_archivo` (y otro archivo cambia la voz) |
| 6 · 401 y 422 | `test_sin_clave_es_401_y_no_llama_al_llm`, `test_un_cuerpo_invalido_es_422_sin_repetir_los_datos`, `test_mas_de_20_respuestas_es_422` |
| Contrato | `test_el_json_schema_documenta_generar_y_procesar_no_cambio`. Además, la prueba de T02 que compara el schema publicado con los modelos sigue pasando |

### 4.2 Java (14 de `GeneracionTest` + 2 de `NlpDataClientTest`)

| # de la ficha | Pruebas |
|---|---|
| 1 · Genera | `unLogroPublicableTieneSusDosBorradoresPendientes` (tokens en el post; el caso, con 0), `elPedidoLlevaElLogroTalCualSinRespuestas` |
| 2 · No publicable | `unLogroNoPublicableTieneMotivoYCeroBorradores` |
| 3 · La IA falla | `siLaIaFallaSumaIntentosHastaQuedarEnError` (sin reserva y sin borradores; `ERROR` es definitivo), `unErrorDelLlmUn422YUnaRespuestaIncoherenteCuentanComoIntento` |
| 4 · A la vez | `dosReservasAlMismoTiempoNoTomanLosMismosLogros`, `unLogroReservadoPorOtraEjecucionNoSeToma` |
| 5 · Cambió | `siElMensajeCambioMientrasLaIaRedactabaNoSeGuardaNada`, `siLoReclasificaronMientrasLaIaRedactabaNoSeGuardaNada` |
| 6 · No se envían | `comentariosDudasBotsYPendientesNoSeEnvian` (comentario, duda, `botPropio`, `otroBot`, `PENDIENTE` y `ERROR`) |
| 7 · Sin duplicados | `correrLaTareaOtraVezNoDuplicaBorradores`, `laV4ImpideDosBorradoresPendientesDelMismoTipo`, `siYaHabiaUnBorradorPendienteNoQuedaNadaAMedias` (la transacción se deshace entera) |
| 8 · Con respuestas | `lasRespuestasDePersonasViajanEnElPedidoConTope` (20 de 22; sin las de bots ni las de otros mensajes) |
| HTTP | `generarEnviaElPedidoConLaClaveYLeeLaRespuesta`, `generarCon500Y422LanzaLasMismasExcepciones` |
| 9 · Las 80 de antes | Pasan |

Las 14 de `GeneracionTest` pasaron en la primera corrida.

### 4.3 Comprobaciones antes de la prueba real

- La consulta de OPERACION.md §8 que busca el nombre completo se probó contra la base principal: dio `0`, porque todavía no había borradores.
- 🧪 Había **10 logros** de personas ya clasificados, que la tarea iba a procesar al encender Java.

### 4.4 Prueba real (la corrió Harrison, 2026-10-04)

`docker compose up -d --build` (no había otro bot). Después, en `#logros`, Harrison escribió un logro propio ("Me contraron como data engineering!!! Gracias por su apoyo") y "por fin entendí recursividad".

**Registro de `api-java`** (solo números):

```
Migrating schema "public" to version "4 - generacion"
Successfully applied 1 migration to schema "public", now at version v4
Generación: tomados 3, generados 1, no publicables 2, ERROR 0, reintento 0, cambiaron 0 · 21679 ms
En vivo 1556365825735131249: orden REACCIONAR · 3929 ms
En vivo 1556366004064358535: orden REACCIONAR · 18879 ms
Generación: tomados 3, generados 1, no publicables 2, ERROR 0, reintento 0, cambiaron 0 · 26803 ms
Generación: tomados 3, generados 2, no publicables 1, ERROR 0, reintento 0, cambiaron 0 · 6884 ms
Generación: tomados 3, generados 1, no publicables 2, ERROR 0, reintento 0, cambiaron 0 · 5143 ms
```

**Estados de generación** (12 logros, todos al primer intento):

| `discord_id` | Simulado | Estado | Motivo (recortado) |
|---|---|---|---|
| 1554205332463558739 | sí | `GENERADO` | …la alumna terminó un curso, lo cual califica como un logro publicable |
| 1554205341070397571 | sí | `NO_PUBLICABLE` | …es un avance pequeño del día a día |
| 1554205348519477461 | sí | `NO_PUBLICABLE` | …avance pequeño del día a día y la resolución de un ejercicio |
| 1554205355767103681 | sí | `NO_PUBLICABLE` | …avance pequeño del día a día… |
| 1554205363442557000 | sí | `NO_PUBLICABLE` | …no un logro mayor como una contratación o certificación… |
| 1554205370975649814 | sí | `GENERADO` | …conseguir una entrevista de trabajo es un logro relevante según la guía de voz |
| 1554205378047254630 | sí | `NO_PUBLICABLE` | …avance pequeño del día a día y un ejercicio del bootcamp |
| 1554205393054466139 | sí | `GENERADO` | …consiguió una contratación tras completar el bootcamp |
| 1554205400432115765 | sí | `GENERADO` | …un proyecto terminado o publicado |
| 1556321890585419808 | no | `NO_PUBLICABLE` | …aprobar un ejercicio o challenge del día a día es considerado un avance pequeño… |
| 1556365825735131249 (el logro de Harrison) | no | `GENERADO` | …conseguir una contratación es un logro destacado según la guía de voz |
| 1556366004064358535 ("por fin entendí recursividad") | no | `NO_PUBLICABLE` | …avance pequeño del día a día y no un logro mayor… |

**Borradores:** 10, todos `PENDIENTE` (5 `POST_LINKEDIN` y 5 `CASO_EXITO`). Los tokens están en el post (de 1369 a 1403 de entrada y de 253 a 340 de salida), y el caso lleva 0. **Comprobación del nombre completo** (OPERACION.md §8): `con_nombre_completo = 0`.

**Los borradores del logro de Harrison**, tal como quedaron:

```
===== POST_LINKEDIN =====
Cada nueva contratación en tecnología es una gran noticia que celebramos en equipo. 🎉 Hoy queremos compartir que Harrison dio un gran paso y consiguió un nuevo empleo. Sus compañeros y mentores lo celebraron con mucho orgullo. En sus palabras: "Me contraron como data engineering!!! Gracias por su apoyo". Este tipo de historias nos recuerdan que el esfuerzo y la constancia siempre dan frutos. Cada camino en la tecnología es único, y ver este avance nos inspira a seguir construyendo comunidad y apoyando a quienes están empezando. 💪 #CommunityLab #Empleabilidad #TechLatam
===== CASO_EXITO =====
**Situación:** Harrison es parte de nuestra comunidad en CommunityLab y se preparaba para dar el salto profesional.
**Desafío:** Enfrentó el proceso de búsqueda laboral con constancia hasta alcanzar su objetivo.
**Logro:** Fue contratado como data engineering, demostrando que el esfuerzo da frutos.
**En sus palabras:** "Me contraron como data engineering!!! Gracias por su apoyo"
**Cierre:** Su historia nos enseña que con perseverancia y el respaldo de la comunidad es posible cumplir las metas profesionales y abrirse paso en el sector tecnológico.
```

✅ Solo el primer nombre. ✅ La cita es literal, incluso con el error de tipeo. ✅ No inventó empresa, cifras ni fechas. ✅ 2 emojis y 3 hashtags de la lista. ✅ El caso tiene los 5 títulos de la guía.

👤 **Evaluación de Harrison:** *"sí me gustó el tono"*. Las dos observaciones del chat de tarea (sección 6, puntos 1 y 2) **no las considera fallas** y eligió no cambiarlas (opción C).

## 5. Decisiones que se tomaron

| # | Decisión | Alternativas descartadas | ¿Cambia el contrato, la arquitectura o D1 a D7? |
|---|---|---|---|
| 1 | 👤 La guía de voz, aprobada por Harrison tal como la redactó el chat (DEC-84) | — | No |
| 2 | El Agente-Mod envía al LLM **una entrada armada** (primer nombre, canal, texto, total de reacciones y rol y texto de cada respuesta), **no la caja**. Las menciones `<@id>` se cambian por `@alguien` | Enviar la caja y pedirle al LLM que ignore los datos personales: depende de que el LLM obedezca | No (DEC-81, defensa en el código) |
| 3 | **Última defensa en la salida:** si un borrador trae el nombre completo o el usuario del autor (por ejemplo, porque el alumno los escribió), se reemplazan por el primer nombre, solo como palabra entera | Rechazar el borrador como `ERROR` | No |
| 4 | Una sola llamada al LLM, **sin reintento**, con 25 s de tope (`MOD_TIMEOUT_S`): cabe en los 30 s de Java. Si falla, Java la repite en la siguiente vuelta | Reintentar dentro de la IA (podía pasar de 30 s) | No |
| 5 | `publicable = true` sin los dos textos es `ERROR` (F4), no un borrador a medias. `publicable = false` descarta cualquier texto que traiga | — | No |
| 6 | Temperatura 0,7 para redactar (`MOD_TEMPERATURE`) | 0, como el clasificador: textos más repetitivos | No |
| 7 | En el pedido viajan solo las respuestas **de personas** al logro (las de bots no aportan), como máximo 20 y de la más antigua a la más nueva | Todas las filas con `responde_a` | No |
| 8 | Los tokens de la única llamada van en el `POST_LINKEDIN` y el `CASO_EXITO` lleva 0: así la suma de la tabla es exacta | Repetirlos en las dos filas (se contarían dos veces) | No |
| 9 | Como pide la ficha, **cualquier** fallo (también la IA caída) suma un intento y, al tercero, `ERROR` definitivo. OPERACION.md §8 tiene el `UPDATE` para reintentar | Como en T04, que una IA caída no cuente para `ERROR` | No (ver riesgo 3) |
| 10 | La tarea tiene su propio `@EnableScheduling`: corre aunque la clasificación esté apagada | — | No |
| 11 | Intervalo de 60 s, tanda de 3, reserva de 180 s (3 × 30 s de espera máxima, con margen) y primera vuelta a los 45 s | — | No |

## 6. Dudas, riesgos y pendientes

| # | Qué | Para quién |
|---|---|---|
| 1 | 🧪 En el post del logro de Harrison, la IA escribió *"Sus compañeros y mentores lo celebraron"*, aunque en ese momento el mensaje no tenía reacciones ni respuestas guardadas (`reacciones = []`, 0 respuestas). La guía dice que eso solo se menciona si las hay. 👤 Harrison no lo considera una falla: los compañeros pueden reaccionar después. **Mejora posible:** decirle al LLM "Reacciones: ninguna" cuando no hay | Mejora 🟡 (opción C de Harrison) |
| 2 | 🧪 Los textos salieron **más cortos** que la guía: posts de 63 a 92 palabras (pide 90 a 160) y casos de 60 a 114 (pide 150 a 250). 🔎 El modelo `flash-lite` tiende a escribir corto. 👤 Harrison: *"no me parece gran cosa"*. **Mejora posible:** exigir los largos en las instrucciones o usar otro modelo con `MOD_MODEL_NAME` | Mejora 🟡 (opción C) |
| 3 | Si la IA o Gemini están caídos más de 3 vueltas (unos 3 minutos), los logros pendientes quedan en `ERROR` y no se reintentan solos. OPERACION.md §8 explica cómo reintentarlos | Chat principal: ¿mantener lo de la ficha o hacer como en T04? |
| 4 | **Fuera de alcance (la ficha pide anotarlo):** si después se edita el mensaje del logro, sus borradores quedan como estaban (`GENERADO`) y no se regeneran. Si la edición cambia el texto, el mensaje vuelve a `PENDIENTE` y se reclasifica, pero `generacion_estado` sigue `GENERADO` | T07 (el panel podría ofrecer "volver a generar") |
| 5 | 🧪 "por fin entendí recursividad" se sigue clasificando `TESTIMONIO` (observación de T02). Ahora no hace daño: el Agente-Mod lo marca `NO_PUBLICABLE` | — |
| 6 | El `motivo` lo escribe la IA y puede mencionar al alumno por su primer nombre. Se guarda en `generacion_motivo`, pero **no** va al registro | — |
| 7 | `CLAUDE.md` §3 todavía dice que `agents/agent_mod/` "no existe todavía" | Chat principal |
| 8 | 🔎 Se recomienda registrar en `DECISIONES.md` las decisiones 2, 3, 7, 8 y 9 | Chat principal |

## 7. Comandos que ejecutó Harrison

1. 👤 Aprobó la guía de voz.
2. Desde la raíz: `docker compose up -d --build` y `docker compose ps`.
3. En Discord, `#logros`: su logro y "por fin entendí recursividad".
4. Las consultas de solo lectura de la sección 4.4 las corrió el chat de tarea.
5. Los dos commits y el `git push` (sección de cierre del chat).
