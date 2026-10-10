# T10 · Despliegue en Oracle Cloud y ensayo de la demo

| Dato | Valor |
|---|---|
| Fase del plan | 6 · OCI y despliegue ([análisis §9](../ANALISIS_INGENIERIA_PROPUESTA_3.md#9-prioridades-y-orden)) |
| Objetivos | **OE9** (desplegarlo y ensayar la demo) y lo que falta de **OE1** (la ingesta cada hora) y de **OE8** (todo con un comando, seguro) |
| Hallazgos y decisiones que resuelve | O1, O3, O5, O6 (parte), O7, Q7, DEC-51, DEC-52, DEC-56, DEC-71 (claves nuevas en el servidor) y observaciones de T04, T06b, T07, T08 y T09 ([README](README.md)) |
| Tamaño | L (archivos de producción en el repositorio, más el despliegue y el ensayo, que hace Harrison guiado) |
| Modelo de Claude recomendado | **Opus 5.5**: seguridad de un servidor público, redes de Docker y operación |
| Depende de | T01 a T09 ✅. Pendientes de T09 que conviene cerrar aquí: **la confirmación de Gabriel** y **la prueba con la PAR propia** (DEC-129) |
| Rama | `tarea/T10-despliegue-demo` |
| Decisiones previas 👤 | Las de la sección 1.1, validadas por Harrison el 2026-10-05 |

## 1. Objetivo

Que InsightEdu Lab corra **en una máquina virtual gratis de Oracle Cloud**, como en la vida real:
- el **panel** abierto a internet con **HTTPS**, en un subdominio de DuckDNS, como **única puerta pública**;
- la **ingesta corriendo sola cada hora**;
- **respaldos diarios** de la base;
- **claves nuevas**, propias del servidor.

Además, que exista un **guion de la demo** ensayado de punta a punta.

🧪 **Lo que consume hoy** (medido el 2026-10-05): ~1,6 GB de RAM en reposo (la IA, ~950 MB) e imágenes por ~5,6 GB. 🔎 La VM necesita como mínimo 4 GB de RAM, 2 CPU y 25 GB de disco. Al construir, Maven y PyTorch piden más.

### 1.1 Decisiones previas 👤 (2026-10-05)

| # | Pregunta | Decisión | Descartada |
|---|---|---|---|
| 1 | ¿Dónde se despliega? (DEC-137) | **Una VM "Always Free" de Oracle Cloud**, en la cuenta de Harrison (procesador ARM Ampere, con RAM de sobra dentro del nivel gratuito). Reemplaza a D7 (el servidor del equipo), que nunca se revisó (O4) | El servidor del equipo; la demo desde la PC, que no cumple "desplegado" |
| 2 | ¿Cómo se abre el panel con HTTPS? (DEC-138) | **Caddy** como puerta de entrada (pone el certificado HTTPS solo, con Let's Encrypt) y **un subdominio gratis de DuckDNS**. Abiertos solo los puertos 80 y 443, que van al panel | Un túnel SSH sin enlace público; un dominio propio (no hay) |
| 3 | ¿Qué datos muestra la demo? (DEC-139) | **Los reales, más mensajes escritos en vivo** durante la demo | Cargar datos ficticios de varias semanas |
| 4 | ¿Qué versión se entrega? (DEC-57) | ⏳ **Harrison lo decide con el equipo.** La ficha no fusiona nada a `main` | — |

Decisiones del chat principal (Harrison no se opuso), **DEC-140**:
- la ingesta es un servicio de Docker que habla con Java **por la red interna**: las claves nunca viajan por internet (resuelve DEC-56 junto con DEC-138);
- `cron` la corre cada hora;
- respaldos diarios con `pg_dump`, guardando los últimos 7;
- **claves nuevas en el servidor**, generadas allí con los scripts (DEC-71);
- **un solo bot**: cuando se enciende el del servidor, se apaga el de la PC.

## 2. Contexto que hay que leer

| Qué | Dónde |
|---|---|
| La propuesta de despliegue: un solo `docker compose`, red interna y el panel como única puerta | [Análisis §7](../ANALISIS_INGENIERIA_PROPUESTA_3.md) (O1 a O9) y [PDF de la propuesta 3](../propuesta-3/Propuesta_3_Arquitectura_InsightEdu.pdf), §8 |
| Cómo se levanta hoy, servicio por servicio, y qué variables pide cada uno | [OPERACION.md](../../OPERACION.md) y `compose.yml` |
| La guía para el equipo (los pasos que un integrante sigue en su PC) | [README.md](../../../README.md), "Guía para probar el proyecto" |
| La ingesta: `extract.py`, `build_batch.py`, `send_batch.py`, sus marcadores y `INGEST_REREAD_DAYS` | `ingestion/discord/` y su `.env.example` |
| Observaciones que pasan a esta tarea: HTTPS y la consulta de Streamlit a un servicio externo (T07), el ritmo de la clasificación (T04), Java encendido el lunes para la FAQ (T06b), el vencimiento de la PAR y los 2 pendientes (T09), "dudas sin responder" en la demo (T08) | [README de tareas](README.md), filas "T10" |
| Decisiones de seguridad que no se pueden romper | DEC-42 (puertos), DEC-43 (secretos), DEC-70 (cada clave, su puerta) y DEC-110 (inicio de sesión del panel) en [DECISIONES.md](../../DECISIONES.md) |

## 3. Alcance: qué entra

### Parte A · Preparar el repositorio para producción (el chat de tarea, probado en la PC)

1. **`compose.prod.yml`**, un archivo que se suma a `compose.yml` (`docker compose -f compose.yml -f compose.prod.yml …`):
   - el servicio **`caddy`** (imagen oficial) con un `Caddyfile` que lleva el dominio de una variable (por ejemplo, `DOMINIO`) hacia `panel:8501`. Es el **único** servicio con puertos publicados (80 y 443), con volúmenes para sus certificados;
   - en producción, **ningún otro servicio publica puertos**, ni siquiera en `127.0.0.1`: se administra por SSH;
   - `restart: unless-stopped` en todos, y un **tope de tamaño a los registros** de Docker (O6), por ejemplo con `max-size` y `max-file`;
   - la configuración local (`compose.yml` solo) **sigue funcionando igual** en la PC.
2. **Servicio `ingesta`** (O1, O3):
   - un `Dockerfile` para `ingestion/discord`, construido desde la raíz como los demás;
   - corre `extract.py`, `build_batch.py` y `send_batch.py` una vez y termina (`docker compose run --rm ingesta`);
   - habla con `http://api-java:8080` **por la red interna**;
   - sus marcadores y lotes en un volumen, para no releer todo cada hora;
   - la variable `INGEST_REREAD_DAYS` permite traer el historial completo **la primera vez** (por ejemplo, 60 días), porque los mensajes de prueba son de fines de septiembre.
3. **Programación y respaldos:**
   - un script (por ejemplo, `scripts/servidor/`) con las líneas de `crontab` para la ingesta cada hora (O3) y el respaldo diario;
   - el respaldo: `pg_dump` comprimido, con fecha en el nombre, guardando los últimos 7 días;
   - cómo **restaurar** un respaldo, probado en la PC con la base `insightedu_test`, nunca con la principal.
4. **Endurecer lo público:**
   - Streamlit en producción **sin** consultar servicios externos al arrancar (la "External URL" de la observación de T07) y sin estadísticas de uso. El chat de tarea verifica la configuración en la documentación de Streamlit (📘);
   - Caddy con las cabeceras de seguridad básicas.
5. **Compatibilidad con ARM:** las imágenes tienen que construirse en una VM ARM (Ampere): PyTorch para CPU, Maven y las imágenes base. El chat de tarea lo verifica en la documentación (📘) y, si se puede, construye la imagen de la IA para `linux/arm64` en la PC.
6. **`docs/DESPLIEGUE.md`**, escrito para que Harrison lo siga paso a paso, con el estilo del README:
   1. crear la VM en Oracle Cloud (Ubuntu, Ampere A1, OCPU y RAM dentro del nivel gratuito) y su clave SSH. ⚠️ **La clave privada nunca va a un chat**;
   2. abrir los puertos 80 y 443 en la "Security List" de la red de OCI **y** en el firewall de la VM. 🔎 Las imágenes de Ubuntu de Oracle traen reglas de `iptables` propias: verificarlo en la documentación (📘);
   3. instalar Docker, clonar el repositorio y crear el `.env` del servidor con **claves nuevas** (DEC-71), un usuario del panel y la **PAR propia** de T09;
   4. crear el subdominio en DuckDNS, apuntarlo a la IP pública de la VM y levantar todo;
   5. instalar el `crontab` (ingesta y respaldos), comprobar todo y saber actualizar (cómo bajar una versión nueva y reconstruir);
   6. **apagar el bot de la PC** antes de encender el del servidor.
7. **`docs/GUION_DEMO.md`** (Q7), para una demo de unos 10 minutos:
   - el problema del cliente en una frase;
   - los mensajes que se escriben en vivo y qué se muestra después de cada uno: la respuesta del bot, la derivación al mentor, el 🎉, el borrador en el panel, aprobarlo con consentimiento, el archivo en el bucket, el dashboard y la FAQ semanal;
   - cómo explicar las "dudas sin responder" (observación de T08);
   - un **plan B** si Gemini falla o se agota el cupo: mostrar borradores ya generados;
   - una lista de comprobación del día anterior: la PAR vigente, el cupo de Gemini, que el único bot encendido sea el del servidor y que haya un respaldo reciente.
8. Actualizar `OPERACION.md`, `CLAUDE.md` (mapa de servicios) y el README (cómo se ve la versión desplegada).

### Parte B · Desplegar y ensayar (Harrison, guiado por el chat de tarea)

9. Seguir `DESPLIEGUE.md` en la VM real. El chat de tarea acompaña cada paso con comandos de solo lectura para comprobar, y corrige el documento si un paso no sirve.
10. **Cerrar los pendientes de T09 aquí:** la PAR propia en el `.env` del servidor (con las subidas reencoladas) y la confirmación de lo que hay en el bucket.
11. **Ensayar el guion completo** contra la versión desplegada y anotar los tiempos.

## 4. Fuera de alcance

- Fusionar a `main` o decidir qué versión se entrega (DEC-57: lo decide Harrison con el equipo).
- Alta disponibilidad, varios servidores, monitoreo con alertas, CI/CD (O9).
- Llevar a la VM los datos de la base de la PC: el servidor arma su historial con la ingesta.
- Revocar la PAR vieja del historial (DEC-41). Las mejoras 🟡 del README de tareas.
- **No ejecutar `simulate_students.py`.** **Nunca dos bots encendidos a la vez.** Nunca pegar en el chat el `.env`, la PAR, la clave SSH privada ni el token de DuckDNS.

## 5. Pruebas exigidas

**En la PC (parte A):**

| # | Caso | Resultado esperado |
|---|---|---|
| 1 | `docker compose -f compose.yml -f compose.prod.yml config` | Válido; solo `caddy` publica puertos |
| 2 | Producción en la PC con un dominio de prueba (por ejemplo, Caddy con certificado interno o `localhost`) | El panel responde a través de Caddy; `api-java`, `ia` y `postgres` no responden desde fuera de Docker |
| 3 | `docker compose run --rm ingesta` | Envía un lote por la red interna; la segunda vez no duplica nada (`sin cambios`) |
| 4 | Respaldo y restauración | Se crea el archivo y se restaura en `insightedu_test`, con las mismas cantidades de filas |
| 5 | La configuración local de siempre (`compose.yml` solo) | Sigue levantando igual |
| 6 | Las pruebas existentes (Java, IA, bot, panel e ingesta) | Siguen pasando |

**En la VM (parte B), con evidencia en el informe:**
- `https://<subdominio>.duckdns.org` muestra el inicio de sesión del panel con el candado de HTTPS;
- desde internet, solo responden los puertos 80 y 443 (por ejemplo, intentar `:8008` o `:8000` y que fallen);
- el bot del servidor responde en Discord, con el de la PC apagado;
- la ingesta de cada hora aparece en el registro;
- hay un archivo de respaldo;
- los borradores llegan al bucket con la PAR propia;
- el guion de la demo se ensayó completo, con sus tiempos.

## 6. Criterios de terminado

- [ ] El sistema corre en la VM de Oracle con HTTPS y el panel como única puerta pública.
- [ ] La ingesta corre sola cada hora y hay respaldos diarios que se pueden restaurar.
- [ ] El servidor usa claves nuevas y la PAR propia (cierra los pendientes de T09).
- [ ] `DESPLIEGUE.md` y `GUION_DEMO.md` están escritos y probados de verdad.
- [ ] Las pruebas pasan, y el informe `docs/tareas/T10-informe.md` tiene la evidencia de la VM, sin secretos.

## 7. Comandos de git para Harrison

**Al empezar**, desde `C:\Users\LENOVO\Documents\Cursos\No Country\Hackaton ONE 10\insightedu-lab`, **después de subir la ficha** y con `git status` en `working tree clean`:
```
git switch feature/integracion-arquitectura-3
git pull
git switch -c tarea/T10-despliegue-demo
```

**Al terminar:** el chat de tarea da los comandos de commit (un solo `-m`, **sin** `Co-Authored-By`: DEC-65). Después:
```
git push -u origin tarea/T10-despliegue-demo
```

Luego le dices al chat principal **"T10 terminó"**.

## 8. Cómo abrir el chat de esta tarea

1. En VS Code, abrir un chat nuevo de Claude Code **en esta misma carpeta**.
2. Elegir el modelo **Opus 5.5** con `/model`.
3. Primer mensaje: *"Eres el chat de la tarea T10. Lee CLAUDE.md y docs/tareas/T10-despliegue-demo.md y empieza."*

🔎 Esta tarea puede ocupar más de una sesión: la parte A en la PC y la parte B en la VM. Si el chat se llena, puede dejar un traspaso en el informe y seguir en otro chat con la misma ficha.

⚠️ **Nunca pegues en el chat** el `.env`, la URL PAR, la clave SSH privada ni el token de DuckDNS.
