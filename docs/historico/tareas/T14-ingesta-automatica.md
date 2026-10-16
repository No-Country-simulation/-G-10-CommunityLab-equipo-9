# T14 · La ingesta corre sola cada hora, el panel avisa "Datos al día" y el bot resiste mejor a Gemini gratis

> Esta ficha **sí es la orden de trabajo vigente** de T14, aunque viva en `docs/historico/tareas/`. Para todo lo demás manda [AGENTS.md](../../../AGENTS.md).

| Dato | Valor |
|---|---|
| Objetivos | Cierra lo que falta de **OE1** (capturar por lotes cada hora, sin esfuerzo manual) y de **OE8** (todo con un comando: el sexto servicio). Refuerza **OE4** para la demo |
| Tamaño | M: un servicio nuevo de Docker, una puerta de solo lectura en Java, la barra lateral del panel, un reintento en la IA y dos ajustes chicos |
| Modelo de Claude recomendado | **Opus 5.5**: un servicio nuevo con secretos, un cambio de arquitectura (la ingesta deja de ser manual) y una puerta nueva del contrato |
| Depende de | T03 (la puerta de lotes y su clave), T13 (la barra lateral) y T15 (el respaldo de Gemini y los tiempos) |
| Rama | `tarea/T14-ingesta-automatica` (Harrison la crea desde `main`; esta ficha es su primer commit) |
| Diseño aprobado | El recuadro "Estado de los datos" de la barra lateral, en [diseno/borradores.dc.html](../diseno/borradores.dc.html) (líneas 32 a 39) y [diseno/README.md](../diseno/README.md) |
| Decisiones previas 👤 | Las de la sección 1.1, validadas por Harrison el 2026-10-16 |

## 1. Objetivo

Hoy la ingesta por lotes se corre **a mano** (`extract.py`, `build_batch.py` y `send_batch.py`). Es la que rescata los mensajes que el bot no vio: si el bot estuvo apagado, o si Java o la IA fallaron en vivo (DEC-67). Al terminar T14:

1. un servicio **`ingesta`** de Docker queda encendido con `docker compose up -d`, corre **al arrancar** y después **cada hora en punto**, y habla con Java **por la red interna**;
2. la barra lateral del panel muestra, en todas las páginas, **"Datos al día · Última actualización: hace N min · Próxima: 15:00 (cada hora, sola)"**, como en el prototipo;
3. el bot **reintenta** cuando Google responde 503 o 504, mientras le quede tiempo dentro de su tope;
4. dos ajustes chicos: el **modelo de respaldo por defecto** y los **íconos del dashboard**, que hoy no se ven.

### 1.1 Decisiones previas 👤 (2026-10-16)

| # | Decisión | Detalle |
|---|---|---|
| 1 | **Servicio con reloj propio**, no `cron` | El servicio `ingesta` queda encendido (`restart: unless-stopped`): corre una vez al arrancar y después cada hora en punto (hora de Bogotá). Funciona igual en la PC con Windows y en un servidor. **Reemplaza el `cron` de la ingesta en DEC-140** (el resto de DEC-140 sigue para T10) |
| 2 | **El aviso de la barra lateral, como el prototipo** | Verde, "Datos al día", si el último lote llegó hace menos de 2 horas; ámbar, "Datos atrasados", si llegó hace más, o "Todavía no hay lotes" si no hay ninguno. Debajo: "Última actualización: hace N min" y "Próxima: HH:00 (cada hora, sola)". En todas las páginas |
| 3 | **La demo usa la cuenta gratuita de Gemini** | Harrison no va a pagar una clave: no es producción, y hay modelos gratuitos. Las protecciones son el respaldo (DEC-165), los tiempos (DEC-166) y el reintento de la decisión 4. Si Google rechaza todos los modelos a la vez, el bot deriva (D3) |
| 4 | **Reintentar ante un 503 o un 504, mientras quede tiempo** | 🧪 El 2026-10-16, 2 dudas se derivaron a los 9 y 17 s por un 503, con más de 20 s libres del tope de 40 s. Un 503 no se procesa, así que probablemente no se cobra |
| 5 | **Modelo de respaldo por defecto** | `compose.yml` y `.env.example` traen `GEMINI_MODELO_RESPALDO=gemini-3.5-flash` por defecto, y `GEMINI_MODEL` sigue en `gemini-3.5-flash-lite` (estable). El `.env` de cada persona puede cambiarlos. El de Harrison hoy usa `gemini-flash-lite-latest`, un alias que Google puede cambiar sin avisar: lo decide él en el ensayo de la demo |
| 6 | **No hace falta avisar al equipo** de los tiempos de T15 | Ya está acordado |

La tarea suma a [DECISIONES.md](../../DECISIONES.md):
- **DEC-167:** el servicio `ingesta` con reloj propio (decisión 1). DEC-140 se actualiza: el `cron` de la ingesta queda reemplazado;
- **DEC-168:** el aviso "Datos al día" y su puerta de solo lectura (decisión 2);
- **DEC-169:** la demo con la cuenta gratuita de Gemini y el respaldo por defecto (decisiones 3 y 5);
- **DEC-170:** el reintento ante un 503 o un 504 (decisión 4).

## 2. Contexto: qué leer

| Qué | Dónde |
|---|---|
| Cómo funciona hoy la ingesta | [ARQUITECTURA.md §4.1](../../ARQUITECTURA.md), [ingestion/discord/README.md](../../../ingestion/discord/README.md), `extract.py` (los marcadores en `data/markers.json` y la ventana `INGEST_REREAD_DAYS`), `build_batch.py` y `send_batch.py` |
| Lo que ya se había diseñado para el servicio | [T10-despliegue-demo.md](T10-despliegue-demo.md), Parte A, punto 2 (Dockerfile, red interna, volumen para los marcadores) |
| La puerta de lotes y su clave | [CONTRACT.md](../../../ingestion/discord/docs/CONTRACT.md), `LoteController`, la tabla `lotes_recibidos` (V1: `recibido_en`, `modo`, `total`, `nuevos`, `actualizados`) |
| La barra lateral y sus piezas | `panel/app.py` (navegación propia, DEC-162) y `panel/estilo.py` (T13) |
| Los tiempos y el respaldo de Gemini | [T15-informe.md](T15-informe.md) §8 y §9, DEC-165 y DEC-166 |
| Los íconos que no se ven | [T13-informe.md](T13-informe.md) §6, punto 2: los `<svg>` dentro de `st.html` no se dibujan en Streamlit 1.65 |

## 3. Alcance: qué entra

### Parte A · El servicio `ingesta`

1. **`ingestion/discord/Dockerfile`**, construido desde la raíz como los demás. Copia solo lo que la ingesta necesita para extraer, armar y enviar. **No copia `simulate_students.py` ni `simulation/`** (AGENTS.md: nunca se ejecuta): compruébalo con un `ls` dentro de la imagen. El `.dockerignore` de la raíz ya deja fuera los `.env` y `ingestion/**/data/`.
2. **Un programador**, por ejemplo `ingestion/discord/programador.py`:
   - corre la ingesta (extraer → armar → enviar) **una vez al arrancar**, y después **cada hora en punto**, en hora de Bogotá;
   - nunca corre dos a la vez. Si una corrida falla (Discord o Java caídos), lo registra, espera a la hora siguiente y **no se cae**;
   - `--una-vez` corre una sola vez y termina (para probar y para la prueba real);
   - registra solo números y estados (canales leídos, mensajes, nuevos, actualizados, sin cambios, error), **nunca textos de alumnos** (AGENTS.md);
   - reutiliza las funciones de `extract.py`, `build_batch.py` y `send_batch.py`, sin copiarlas.
3. **El servicio en `compose.yml`:**
   - `restart: unless-stopped`, **sin puertos**, en la red interna;
   - un **volumen propio** para `data/` (marcadores, crudos y lotes): sobrevive a un reinicio, y la primera corrida relee los últimos `INGEST_REREAD_DAYS` días (7 por defecto). El upsert por `discord_id` y el `loteId` idempotente evitan los duplicados;
   - las variables, desde el `.env` de la raíz:
     - `BACKEND_INGEST_URL` apunta a `http://api-java:8080/…` (🔎 comprueba en `send_batch.py` si espera la URL completa de `/api/v1/lotes` o la base);
     - `BACKEND_API_KEY` sale de `${API_KEY_INGESTA}`: la misma clave, sin copiarla a otra variable del `.env`;
     - las de Discord (`DISCORD_BOT_TOKEN`, canales, webhooks, roles y `SIMULATED_MENTORS`), las mismas que usa el bot (DEC-74);
     - **`DISCORD_GUILD_ID`**, que hoy no está en el `.env` de la raíz. Súmala a `.env.example` y avísale a Harrison: es un ID, no un secreto, y lo tiene en `ingestion/discord/.env`;
   - un interruptor `INGESTA_HABILITADA` (por defecto `true`), para apagar el reloj sin quitar el servicio.
4. **No es un segundo bot:** la ingesta solo **lee** por la API REST de Discord y nunca escribe en un canal. Puede convivir con el bot encendido (AGENTS.md habla de dos bots que *responden*). Déjalo explicado en OPERACION.
5. Correr la ingesta **a mano** sigue funcionando (README de la ingesta), pero ya no hace falta. Correrla a mano con el servicio encendido no duplica nada; solo usa otros marcadores.

### Parte B · Java y el contrato (solo agrega)

6. **Puerta nueva `GET /api/v1/dashboard/ingesta`** (solo lectura). Responde `{ "ultimoLote": { "recibidoEn": "…", "modo": "historial", "total": 67, "nuevos": 0, "actualizados": 2 } }`, o `{ "ultimoLote": null }` si no hay ninguno. Usa el último lote de `lotes_recibidos` por `recibido_en`. 🔎 Ya está bajo `/api/v1/dashboard`, que solo abre la clave `panel` (`ApiKeyFilter`): compruébalo con una prueba, y que el controlador vuelva a revisar el cliente.
7. **Contrato:** la puerta en [PANEL_JAVA_v1.md](../../contratos/PANEL_JAVA_v1.md) §7, con un ejemplo y una nota "Agregado en T14". Solo agrega.

### Parte C · El panel

8. **El recuadro "Estado de los datos"** en la barra lateral de `app.py`, debajo de la navegación y encima de la sesión, como en el prototipo:
   - el ícono y el título según la decisión 2 ("Datos al día" o "Datos atrasados", "Todavía no hay lotes");
   - "Última actualización: hace N min" (con `estilo.hace`) y "Próxima: HH:00 (cada hora, sola)", calculada en hora de Bogotá;
   - solo textos fijos y números, con las piezas de `estilo.py`; los colores, los de T12, que no dependen del tema (DEC-156);
   - el ícono, de Material (`:material/check_circle:` o similar): los `<svg>` dentro de `st.html` no se ven;
   - el pedido a Java, en caché unos 60 s (no en cada clic). Si Java no responde, el recuadro dice "Estado de los datos: sin información" y la página sigue funcionando.
9. **Los íconos del dashboard:** cambiar los `ICONO_*` de `estilo.py` (reloj, alerta y documento), que hoy no se ven, por íconos de Material que sí se dibujen, sin cambiar nada más del dashboard. Capturas antes y después.
10. `cliente_java.py`: `dashboard_ingesta()`.

### Parte D · La IA

11. **Reintento ante un 503 o un 504** (decisión 4), en el camino en vivo de la duda (clasificar y el Agente FAQ, con su respuesta y su revisión):
    - solo ante **503** (`UNAVAILABLE`, "high demand") y **504** (`DEADLINE_EXCEEDED`). Nunca ante 400, 401, 403 ni 429: esos no se arreglan reintentando, y un 429 gasta la cuota;
    - una espera corta (por ejemplo, 1 a 2 s) y un máximo de intentos (por ejemplo, 2 más). **Solo si el tiempo que queda del tope de `tiempoReal` alcanza** para la llamada completa (el tiempo por llamada al LLM); si no, se rinde y el bot deriva, como hoy;
    - funciona junto con el respaldo (DEC-165): por ejemplo, el principal, el respaldo y después el reintento, mientras quede tiempo. Explica en el informe el orden que elegiste y por qué;
    - el Agente-Mod y la FAQ semanal **no** cambian: Java ya los reintenta en su vuelta siguiente;
    - el registro dice cuántos reintentos hubo y por qué código, **nunca** el texto de la duda.
12. **El respaldo por defecto** (decisión 5): `GEMINI_MODELO_RESPALDO=gemini-3.5-flash` en `compose.yml` (`${GEMINI_MODELO_RESPALDO:-gemini-3.5-flash}`) y en `.env.example`. 🔎 Comprueba en la documentación de Google (📘) que ese nombre de modelo exista hoy, y anótalo en el informe.

### Parte E · La documentación

13. DECISIONES.md: DEC-167 a DEC-170, y DEC-140 actualizada.
14. ARQUITECTURA.md: el mapa (§2), §3 (la ingesta pasa a ser el **sexto servicio**, sin puerto), §4.1 (corre sola cada hora), §4.3 (el reintento ante un 503), §4.7 o §4.6 (el aviso de la barra lateral), §6 y §9 (la tarea de la ingesta) y §12 (sale "la ingesta todavía se corre a mano").
15. AGENTS.md §3, la fila de la ingesta. README: el servicio nuevo. OPERACION.md: cómo ver el registro de la ingesta (`docker compose logs ingesta`), cómo correrla ya (`--una-vez`), cómo apagarla (`INGESTA_HABILITADA`) y la variable `DISCORD_GUILD_ID`.
16. ESTADO.md: OE1 y OE8 ✅ (o lo que falte); §3, el despliegue sigue en pausa, pero ya no le falta la ingesta; §5, la fila de esta rama; la mejora de los íconos, hecha.

## 4. Fuera de alcance

- El despliegue en un servidor (T10, en pausa): `compose.prod.yml`, Caddy, respaldos y claves del servidor.
- Cambiar el contrato v1, la puerta de lotes, `transform.py` o la forma de los lotes. Cambiar el Agente-Mod o la FAQ semanal.
- Encender LinkedIn o correr `scripts/publicar_linkedin.py`.
- **No ejecutar `simulate_students.py`**, y que no entre a la imagen. **Nunca dos bots que respondan.** **Nunca** leer ni mostrar un `.env`: para revisar uno, solo los nombres de sus variables.

## 5. Pruebas exigidas

| Pieza | # | Caso | Resultado esperado |
|---|---|---|---|
| Ingesta | 1 | La próxima corrida, a distintas horas (incluida una a las 23:59 y una justo a la hora en punto) | La hora en punto siguiente, en Bogotá |
| Ingesta | 2 | Una corrida que falla (Discord o Java simulados con error) | Se registra; el programador sigue y espera a la siguiente |
| Ingesta | 3 | Dos corridas a la vez | La segunda no arranca mientras la primera sigue |
| Ingesta | 4 | `--una-vez` | Corre una vez y termina, con código 0 si salió bien y distinto de 0 si falló |
| Ingesta | 5 | El registro | Solo números y estados: ningún texto de un mensaje (una prueba con un mensaje falso que tenga un texto reconocible) |
| Ingesta | 6 | La imagen | No trae `simulate_students.py` ni `simulation/`, ni un `.env` |
| Ingesta | 7 | Las pruebas que ya existían (desde `ingestion/discord`: `python -m pytest -q`) | Siguen pasando |
| Java | 8 | `/api/v1/dashboard/ingesta` sin lotes y con varios | `null` / el más reciente por `recibido_en` |
| Java | 9 | Claves: sin clave / con la de `ingesta` o `bot` / con una ruta disfrazada (`;x=1`, `%65`) | 401 / 403 / 403 |
| Java | 10 | Las 256 que ya existían (reutilizar las propiedades de `DashboardApiTest` o `CuraduriaApiTest`) | Siguen pasando |
| Panel | 11 | El recuadro: lote hace 10 min / hace 3 h / sin lotes / Java caído | "Datos al día" / "Datos atrasados" / "Todavía no hay lotes" / "sin información", sin romper la página |
| Panel | 12 | "Próxima" a las 14:20 y a las 23:50 en Bogotá | 15:00 y 00:00 |
| Panel | 13 | Los íconos del dashboard | Se dibujan (no son `<svg>` dentro de `st.html`); las pruebas del dashboard siguen pasando |
| Panel | 14 | Las 136 que ya existían | Siguen pasando |
| IA | 15 | Un 503 al clasificar con tiempo de sobra / un 503 cuando ya no queda tiempo / un 400 / un 429 | Reintenta y responde / se rinde enseguida / no reintenta / no reintenta |
| IA | 16 | El respaldo y el reintento juntos, y el tope de 40 s | El orden que elegiste, y nunca más de 40 s (con un reloj simulado: sin esperas reales largas) |
| IA | 17 | Las 86 que ya existían, y las 22 del bot | Siguen pasando |

**Capturas** ([diseno/README.md §4](../diseno/README.md)): la barra lateral con el recuadro en claro y en oscuro, cambiando el tema sin recargar, y el dashboard con sus íconos, antes y después. Como en T13: una copia aparte del panel, sin puertos, con un Java simulado. **Solo mirar.**

**Prueba real, la corre Harrison** (gasta 1 llamada a Gemini, la de clasificar el mensaje de prueba):
1. Sumar `DISCORD_GUILD_ID` al `.env` de la raíz (el mismo valor de `ingestion/discord/.env`). El chat de tarea lo comprueba **solo por el nombre**.
2. `docker compose up -d --build`: los 6 servicios en `docker compose ps`; `ingesta` sin puertos.
3. `docker compose logs ingesta`: la primera corrida terminó, con los números del lote (casi todo "sin cambios").
4. El panel: "Datos al día · Última actualización: hace 0 o 1 min · Próxima: HH:00". El dashboard, con sus íconos.
5. **El rescate**: `docker compose stop bot`; escribir un mensaje en `#dudas` (nadie lo responde); `docker compose exec ingesta python programador.py --una-vez` (o el comando que deje el chat); comprobar que el mensaje llegó (lo verifica el chat de tarea en la base, sin mostrar el texto); `docker compose start bot`.
6. Opcional: esperar a la hora en punto y ver en `docker compose logs ingesta` que corrió sola.

## 6. Criterios de terminado

- [ ] El servicio `ingesta` corre al arrancar y cada hora en punto, sin puertos, con su volumen, sin `simulate_students.py` y sin textos en el registro.
- [ ] La barra lateral muestra el estado de los datos como el prototipo, en claro y en oscuro, y aguanta a Java caído.
- [ ] El bot reintenta ante un 503 o un 504 solo mientras le queda tiempo, y nunca pasa del tope.
- [ ] El respaldo por defecto y los íconos del dashboard están hechos.
- [ ] La puerta nueva solo agrega y está en `PANEL_JAVA_v1.md`.
- [ ] Las pruebas de la ingesta, Java, el panel, la IA y el bot pasan, y la prueba real dio lo esperado (🧪 en el informe).
- [ ] DEC-167 a DEC-170, DEC-140, ARQUITECTURA, AGENTS, README, OPERACION y ESTADO al día.
- [ ] El informe `docs/historico/tareas/T14-informe.md` está completo ([plantilla](PLANTILLA_INFORME.md)), y no se tocó nada fuera del alcance. **Si algo fuera del alcance hace falta, se le pide a Harrison antes, y el informe lo dice en su propia sección**, como hizo T15.

## 7. Git

Harrison crea la rama `tarea/T14-ingesta-automatica` desde `main`, y esta ficha es su primer commit. El chat de tarea **no** ejecuta comandos de git que cambian algo, ni los que reconstruyen o apagan servicios: se los da a Harrison **uno por línea**, con la carpeta y lo que debería ver. Un commit por parte (A a E), con un solo `-m` y **sin** `Co-Authored-By` (DEC-65), comprobando cada uno con `git log --oneline -3`. Al final, `git push` y avisarle al orquestador **"T14 terminó"**.

## 8. Cómo abrir el chat de esta tarea

1. En VS Code, abrir un chat nuevo de Claude Code **en esta misma carpeta**, con la rama `tarea/T14-ingesta-automatica` activa.
2. Elegir **Opus 5.5** con `/model`.
3. Primer mensaje: *"Eres el chat de la tarea T14. Lee AGENTS.md y docs/historico/tareas/T14-ingesta-automatica.md completos, y empieza. Respóndeme en español y dame los comandos de git uno por línea."*

⚠️ **Nunca pegues el contenido de un `.env`, un token ni tu contraseña del panel en el chat.**
