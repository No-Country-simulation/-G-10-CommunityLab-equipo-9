# Ingesta de Discord — InsightEdu Lab

Este módulo es la puerta de entrada de InsightEdu Lab: se conecta a Discord, extrae los mensajes de los canales `#dudas` y `#logros` y los prepara para el resto del sistema.

- **Qué incluye y qué no:** [docs/SCOPE.md](docs/SCOPE.md)
- **Cómo son los datos de Discord** (léelo si nunca trabajaste con Discord): [docs/DISCORD_DATA_GUIDE.md](docs/DISCORD_DATA_GUIDE.md)

## Estructura

```
ingestion/discord/
├── README.md                 ← este archivo
├── docs/
│   ├── SCOPE.md              ← alcance, decisiones y pendientes
│   └── DISCORD_DATA_GUIDE.md ← guía y diccionario de datos
├── config.py                 ← lee la configuración del .env
├── discord_api.py            ← cliente de la API de Discord (autenticación, reintentos y límites)
├── verify_connection.py      ← paso 1: comprueba la conexión del bot
├── simulate_students.py      ← paso 2: publica conversaciones de alumnos ficticios
├── extract.py                ← paso 3: extrae los mensajes a data/raw/
├── simulation/
│   └── conversations.json    ← las conversaciones simuladas (se pueden editar)
├── requirements.txt          ← librerías de Python
├── .env.example              ← plantilla de configuración
└── .gitignore                ← evita subir data/ al repo
```

`data/` (los mensajes extraídos) y `.env` (los secretos) existen solo en tu computador y **nunca se suben al repo**.

## 1. Preparar Discord (una sola vez)

Hace falta un servidor de pruebas propio. Es gratis.

1. **Servidor y canales.** En Discord: **+** → **Crear el mío** → **Para mí y mis amigos**. Después crea los canales de texto `dudas` y `logros`.
2. **Bot.** En [discord.com/developers/applications](https://discord.com/developers/applications):
   1. **New Application**.
   2. En **Bot**, activa **Message Content Intent**.
   3. En **OAuth2 → URL Generator**, marca el scope `bot` y los permisos *View Channels*, *Read Message History* y *Send Messages*.
   4. Abre la URL generada y agrega el bot a tu servidor.
3. **Webhooks.** En cada canal: **Editar canal → Integraciones → Webhooks → Nuevo webhook**.

## 2. Instalar (Windows, PowerShell)

Requisito: **Python 3.12**. Revisa si lo tienes con `py -0p`; si no aparece, instálalo con `winget install -e --id Python.Python.3.12`.

```powershell
cd ingestion/discord
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Los comandos usan `.\.venv\Scripts\python.exe` en lugar de activar el entorno. Así funcionan también en equipos donde PowerShell bloquea la ejecución de scripts.

## 3. Configurar

```powershell
Copy-Item .env.example .env
```

Abre `.env` y completa:

| Variable | De dónde sale |
|---|---|
| `DISCORD_BOT_TOKEN` | Developer Portal → tu aplicación → **Bot** → **Reset Token** |
| `DISCORD_GUILD_ID`, `DISCORD_CHANNEL_DUDAS_ID`, `DISCORD_CHANNEL_LOGROS_ID` | Los muestra `verify_connection.py` (paso 1 de la sección siguiente) |
| `DISCORD_WEBHOOK_DUDAS_URL`, `DISCORD_WEBHOOK_LOGROS_URL` | En cada canal: **Integraciones → Webhooks → Copiar URL del webhook** |

## 4. Usar (en este orden)

| Paso | Comando | Qué hace |
|---|---|---|
| 1 | `.\.venv\Scripts\python.exe verify_connection.py` | Comprueba el token, el permiso de contenido y la lectura de cada canal, y muestra los IDs para el `.env`. Solo lee |
| 2 | `.\.venv\Scripts\python.exe simulate_students.py` | Publica las conversaciones de `simulation/conversations.json`. **Ejecútalo una sola vez**: cada ejecución vuelve a publicar todo y los mensajes se duplican |
| 3 | `.\.venv\Scripts\python.exe extract.py` | Descarga todos los mensajes de los dos canales a `data/raw/<canal>.json`, sin modificarlos. Solo lee |

## Seguridad

- **El token del bot y las URLs de los webhooks son contraseñas.** Van solo en `.env`: nunca en el código, en el chat ni en el repo.
- **Si alguno se filtra, se reemplaza:** el token, con **Reset Token**; un webhook, borrándolo y creando otro.
- **`data/` puede contener datos personales** cuando haya alumnos reales. Por eso está excluida del repo.
