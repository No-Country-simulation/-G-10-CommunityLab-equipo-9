# InsightEdu Lab

> Convierte la actividad de una comunidad educativa en Discord en borradores de posts de LinkedIn, casos de éxito, respuestas a dudas, una FAQ semanal y alertas, **con una persona que aprueba todo antes de publicar**.
> Equipo 9 · G10 · Hackatón No Country + ONE · **Rama:** `main` · **Actualizado:** 2026-10-09

## Documentación

| Si quieres… | Lee |
|---|---|
| **Levantar y probar el proyecto** en tu computadora | Esta guía, desde la sección 1 |
| Entender **cómo funciona** (piezas, flujos, datos y seguridad) | [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) |
| Saber **qué está hecho, qué falta** y cómo continuar | [docs/ESTADO.md](docs/ESTADO.md) |
| Saber **por qué** se decidió cada cosa | [docs/DECISIONES.md](docs/DECISIONES.md) |
| Operar cada servicio con Docker | [docs/OPERACION.md](docs/OPERACION.md) |
| Los contratos entre las piezas | [docs/contratos/](docs/contratos/) y [el contrato v1](ingestion/discord/docs/CONTRACT.md) |
| Trabajar con un **asistente de IA** | [AGENTS.md](AGENTS.md) |
| Ver cómo se construyó (planes, tareas e informes) | [docs/historico/](docs/historico/) |

---

# 🚀 Guía para probar el proyecto en tu computadora

> **Para quién es:** integrantes del equipo que quieren levantar el proyecto completo en su propia máquina y probarlo, aunque recién estén aprendiendo Docker y Git.

## 1. Qué vas a levantar

InsightEdu Lab lee los mensajes de un servidor de Discord, los clasifica con IA, responde dudas en vivo y escribe borradores de posts de LinkedIn. **Una persona los aprueba en un panel antes de publicar nada.**

```
Discord ⇄ Bot ──► API Java ⇄ IA (Gemini)        Ingesta por lotes ──► API Java
                     │                           Panel (navegador) ──► API Java
                     └──► PostgreSQL (la base de datos)
```

Todo corre en **contenedores de Docker**. Un contenedor es como una "caja" con un programa y todo lo que necesita ya instalado: no hace falta instalar Java ni las librerías de la IA en tu computadora.

| Pieza | Qué hace | Dónde la ves |
|---|---|---|
| `postgres` | Guarda los mensajes, las etiquetas y los borradores | No se ve: es privada |
| `api-java` | La puerta única: recibe, guarda y coordina | `http://127.0.0.1:8008/actuator/health` |
| `ia` | Clasifica mensajes, responde dudas con los PDF y redacta borradores | `http://127.0.0.1:8000/health` |
| `bot` | Escucha `#dudas` y `#logros` en Discord y responde | En tu servidor de Discord |
| `panel` | Página web para aprobar borradores y ver el dashboard | `http://127.0.0.1:8501` |

## 2. ⚠️ Tres reglas antes de empezar

| Regla | Por qué |
|---|---|
| **Usa tu propio servidor de Discord y tu propio bot** (paso 4) | Si dos bots escuchan el mismo canal, cada mensaje se responde dos veces |
| **Nunca ejecutes `ingestion/discord/simulate_students.py`** | Publica mensajes falsos y los duplica en el servidor |
| **Nunca subas ni pegues en un chat el archivo `.env`** | Tiene tus claves (Gemini, Discord). Para revisarlo, usa el comando de la sección 9, que muestra solo los nombres de las variables |

## 3. Lo que necesitas instalar

| Programa | Para qué | Dónde se descarga |
|---|---|---|
| **Git** | Descargar el código | https://git-scm.com/downloads |
| **Docker Desktop** | Correr los contenedores. Tiene que estar **abierto** mientras pruebas | https://www.docker.com/products/docker-desktop/ |
| **Python 3.12** | Correr los scripts que crean las claves y la ingesta por lotes | https://www.python.org/downloads/ (marca "Add Python to PATH" al instalar) |

Necesitas también unos **10 GB libres** de disco: la primera vez se descargan los modelos de la IA.

Y dos cuentas gratuitas:

| Cuenta | Para qué |
|---|---|
| **Google AI Studio** (https://aistudio.google.com/) | Crear tu clave de Gemini (`GEMINI_API_KEY`). Sin ella, la IA no clasifica ni responde |
| **Discord** | Tu servidor de pruebas y tu bot (paso 4) |

## 4. Prepara tu servidor y tu bot de Discord

Lo haces una sola vez.

1. **Tu servidor:** en Discord, pulsa ➕ → "Crear mi propio servidor". Crea dos canales de texto: `dudas` y `logros`.
2. **Activa el modo desarrollador**, que te deja copiar IDs: Discord → ⚙️ Ajustes de usuario → Avanzado → **Modo desarrollador**.
3. **Copia tres IDs** (clic derecho → "Copiar ID") y guárdalos: el del **servidor**, el del canal **dudas** y el del canal **logros**.
4. **Tu bot:** entra a https://discord.com/developers/applications → **New Application** (ponle un nombre) → menú **Bot**:
   - pulsa **Reset Token** y **copia el token** (es la "contraseña" del bot; guárdalo, se muestra una sola vez);
   - más abajo, activa **Message Content Intent** y guarda los cambios.
5. **Invita el bot a tu servidor:** menú **OAuth2 → URL Generator**:
   - en *Scopes*, marca **bot**;
   - en *Bot Permissions*, marca **View Channels**, **Send Messages**, **Read Message History** y **Add Reactions**;
   - abre la URL que aparece abajo, elige tu servidor y autoriza.

## 5. Descarga el código

En PowerShell, en la carpeta donde guardas tus proyectos:

```powershell
git clone https://github.com/No-Country-simulation/-G-10-CommunityLab-equipo-9.git insightedu-lab
cd insightedu-lab
```

El repositorio se descarga en una carpeta llamada `insightedu-lab`, en la rama `main`, que tiene el proyecto completo. **Desde aquí, todos los comandos se ejecutan en esta carpeta (la "raíz" del repositorio)**, salvo que se diga otra cosa.

## 6. Crea tus archivos `.env` (la configuración)

Hay **dos** archivos `.env`: uno en la raíz, para Docker, y otro en `ingestion/discord/`, para la ingesta. Se crean copiando las plantillas:

```powershell
Copy-Item .env.example .env
Copy-Item ingestion/discord/.env.example ingestion/discord/.env
```

**6.1 · Completa a mano** (abre los archivos con un editor, por ejemplo VS Code):

| Archivo | Variable | Qué poner |
|---|---|---|
| `.env` | `POSTGRES_PASSWORD` | Una contraseña larga inventada (la de tu base de datos local) |
| `.env` | `GEMINI_API_KEY` | Tu clave de Google AI Studio |
| `.env` y `ingestion/discord/.env` | `DISCORD_BOT_TOKEN` | El token de **tu** bot (paso 4) |
| `.env` y `ingestion/discord/.env` | `DISCORD_CHANNEL_DUDAS_ID` y `DISCORD_CHANNEL_LOGROS_ID` | Los IDs de tus canales |
| `ingestion/discord/.env` | `DISCORD_GUILD_ID` | El ID de tu servidor |

Las demás variables de Discord (webhooks, roles de mentor) **pueden quedar vacías** para probar.

**6.2 · Las claves internas no se escriben a mano.** Las crean estos scripts al azar y las guardan en los `.env` sin mostrarlas:

```powershell
python scripts/generar_api_key.py
python scripts/generar_api_key.py --cliente ia
python scripts/generar_api_key.py --cliente bot
python scripts/generar_api_key.py --cliente panel
python scripts/crear_usuario_panel.py
```

| Script | Qué crea |
|---|---|
| `generar_api_key.py` (sin opciones) | La clave entre la ingesta y Java. La escribe en los dos `.env` |
| `--cliente ia`, `bot` y `panel` | La clave de cada pieza para hablar con Java. Cada clave abre solo su puerta |
| `crear_usuario_panel.py` | Tu usuario del panel. Te pide un nombre y una contraseña (no se ve mientras escribes) y guarda solo una versión cifrada |

Cada uno debería responder con un ✅.

## 7. Levanta todo

```powershell
docker compose up -d --build
```

La **primera vez tarda** (10 a 20 minutos): descarga PyTorch y los modelos de la IA. Las siguientes veces tarda segundos.

Comprueba que todo esté bien:

```powershell
docker compose ps
```

Después de uno o dos minutos, `postgres`, `api-java`, `ia` y `panel` deberían decir `(healthy)`, y `bot`, `Up`. En el navegador, `http://127.0.0.1:8008/actuator/health` debería mostrar `"status":"UP"`.

## 8. Prueba el sistema (unos 20 minutos)

Al principio tu base de datos está **vacía**: los datos los creas tú, escribiendo en tu servidor de Discord. Usa unas 10 llamadas a Gemini (gratis, dentro del límite de AI Studio).

### 8.1 · El bot en vivo

Escribe estos mensajes en tu servidor, uno por uno:

| Canal | Escribe | Deberías ver |
|---|---|---|
| `#dudas` | ¿Cuándo empiezan las inscripciones? | "Escribiendo…" y, en segundos, una respuesta que cita el calendario académico |
| `#dudas` | ¿Puedo entregar el proyecto final en Kotlin? | "Un mentor te responderá pronto 🙏" (la respuesta no está en los PDF) |
| `#dudas` | hola a todos | Nada: es un saludo |
| `#logros` | ¡Me contrataron como desarrollador junior después de 6 meses de bootcamp! | Una reacción 🎉, sin texto |
| `#logros` | Hoy por fin terminé el ejercicio de recursividad | Una reacción 🎉, sin texto |

### 8.2 · Los borradores en el panel

1. Espera **1 o 2 minutos** y abre `http://127.0.0.1:8501`. Entra con el usuario que creaste.
2. Página **Borradores:** el logro de la contratación debería tener un **post de LinkedIn** y un **caso de éxito**, con tu primer nombre. El de recursividad no tiene borradores: la IA lo considera un avance menor.
3. Aprueba el post. El botón se activa recién cuando marcas la **casilla de consentimiento** (el alumno aceptó que se publique su nombre).

### 8.3 · La ingesta por lotes

En producción, esto correrá solo cada hora y rescatará lo que el bot no vio. Aquí lo corres a mano, desde `ingestion/discord`, con un entorno de Python propio:

```powershell
cd ingestion/discord
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python extract.py
python build_batch.py
python send_batch.py
cd ../..
```

El último comando debería decir `Java recibió el lote …`, con `nuevos` (las respuestas del bot) y `sin cambios` o `actualizados` (los mensajes que ya había guardado el bot). **Ningún mensaje se duplica.** Las líneas de `venv` e `install` se hacen solo la primera vez; las siguientes basta con activar el entorno.

### 8.4 · El dashboard

En el panel, página **Dashboard:** verás los totales, el sentimiento por día, los temas y las alertas.
- Baja el umbral de **deserción** a pocos días para ver aparecer personas.
- La duda de Kotlin aparece en "dudas sin responder" después de 24 horas. Para verla ya, pon las horas en 0.

### 8.5 · Si algo salió distinto

Escribe en el canal del equipo **qué hiciste, qué esperabas y qué viste**, y pega lo que muestra `docker compose logs api-java --tail 30` (los registros no contienen claves ni textos de alumnos).

## 9. Comandos útiles y problemas comunes

| Para… | Comando |
|---|---|
| Ver el estado | `docker compose ps` |
| Ver los registros de una pieza | `docker compose logs -f bot` (o `api-java`, `ia`, `panel`). Se sale con `Ctrl+C` |
| Revisar tu `.env` sin mostrar las claves | `Get-Content .env \| ForEach-Object { ($_ -split '=')[0] }` |
| Apagar todo (los datos se conservan) | `docker compose down` |
| ⚠️ Apagar y **borrar** todos los datos | `docker compose down -v` (no tiene vuelta atrás) |

| Problema | Causa probable | Solución |
|---|---|---|
| `docker` no se reconoce, o "cannot connect to the Docker daemon" | Docker Desktop está cerrado | Ábrelo y espera a que diga "Engine running" |
| Un puerto está ocupado (`8008`, `8000` o `8501`) | Otro programa lo usa | Cambia el número de la izquierda en `compose.yml` (por ejemplo, `127.0.0.1:8009:8080`) |
| El bot se reinicia una y otra vez | Falta `DISCORD_BOT_TOKEN` en el `.env` de la raíz | Revísalo con el comando de arriba y vuelve a correr `docker compose up -d bot` |
| El bot no responde nada | No activaste **Message Content Intent**, el bot no está en tu servidor o los IDs de canal están mal | Revisa el paso 4 y el paso 6.1 |
| El bot responde siempre "un mentor te responderá" | Falta `GEMINI_API_KEY`, o se agotó tu límite gratuito | Revisa la clave en AI Studio |
| `send_batch.py` dice 401 | La clave de la ingesta no coincide | Vuelve a correr `python scripts/generar_api_key.py --reemplazar` y `docker compose up -d api-java` |
| El panel no deja entrar | No hay usuarios creados | Corre `python scripts/crear_usuario_panel.py` y `docker compose up -d panel` |
| Ya tienes **otra copia** del proyecto corriendo en la misma PC | `compose.yml` fija el nombre `insightedu`: las dos copias compartirían contenedores, la base de datos y el bot | Apaga la otra (`docker compose down` en su carpeta, **sin** `-v`) o levanta esta con otro nombre: `docker compose -p otro-nombre up -d --build` (y `docker compose -p otro-nombre …` en cada comando) |

**Para saber más:** [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) explica cómo funciona cada pieza, [docs/OPERACION.md](docs/OPERACION.md) cómo operarla y [docs/DECISIONES.md](docs/DECISIONES.md) por qué el sistema funciona así. La documentación original de cada equipo está en [docs/historico/equipos/](docs/historico/equipos/README_original_equipos.md).
