# Ingesta de Discord — InsightEdu Lab

Este módulo es la puerta de entrada de InsightEdu Lab: se conecta a Discord, extrae los mensajes de los canales `#dudas` y `#logros` y los prepara para el resto del sistema.

También define el **contrato v1**, el formato de cada mensaje en todo el sistema: el bot lo reutiliza (`transform.py`) para que un mensaje en vivo y uno del lote salgan idénticos.

- **Cómo encaja en el sistema:** [docs/ARQUITECTURA.md](../../docs/ARQUITECTURA.md) §4.1 (lotes) y §4.3 (en vivo)
- **El contrato v1, campo por campo** (fuente de verdad del formato): [docs/CONTRACT.md](docs/CONTRACT.md)
- **Qué pide el cliente y qué entra en el MVP:** [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md)
- **Cómo son los datos de Discord** (léelo si nunca trabajaste con Discord): [docs/DISCORD_DATA_GUIDE.md](docs/DISCORD_DATA_GUIDE.md)
- **Documentos de etapas anteriores** (guía para el equipo, alcance, catálogo de eventos y primera propuesta de arquitectura): [docs/historico/ingesta/](../../docs/historico/ingesta/). No son instrucciones vigentes

## Estructura

```
ingestion/discord/
├── README.md                 ← este archivo
├── docs/
│   ├── CONTRACT.md              ← contrato v1 (el formato que recibe el sistema)
│   ├── PROJECT_BRIEF.md         ← el brief del cliente, objetivos y qué entra en el MVP
│   └── DISCORD_DATA_GUIDE.md    ← guía y diccionario de datos de Discord
├── config.py                 ← lee la configuración del .env
├── discord_api.py            ← cliente de la API de Discord (autenticación, reintentos y límites)
├── contract.py               ← el contrato v1 como código (pydantic); genera el JSON Schema
├── transform.py              ← convierte un mensaje de Discord al contrato (sin internet)
├── verify_connection.py      ← paso 1: comprueba la conexión del bot
├── simulate_students.py      ← ⚠️ NO ejecutar: publica alumnos ficticios y duplica mensajes
├── extract.py                ← paso 3: extrae los mensajes y los roles a data/raw/
├── build_batch.py            ← paso 4: transforma, valida y arma el lote en data/batches/
├── send_batch.py             ← paso 5: envía el lote a la API Java, tal cual (D8), con la API key
├── schema/
│   └── contract_v1.schema.json ← la especificación del contrato para backend (generada)
├── tests/                    ← pruebas automáticas (pytest)
├── simulation/
│   └── conversations.json    ← las conversaciones simuladas (se pueden editar)
├── prototypes/
│   └── contract_prototype.py ← prototipo desechable que generó los ejemplos de docs/CONTRACT.md
├── requirements.txt          ← librerías de Python
├── pytest.ini                ← configuración de las pruebas
├── .env.example              ← plantilla de configuración
└── .gitignore                ← evita subir data/ al repo
```

`data/` (los mensajes extraídos, los lotes y el marcador) y `.env` (los secretos) existen solo en tu computador y **nunca se suben al repo**.

## 1. Preparar Discord (una sola vez)

Hace falta un servidor de pruebas propio. Es gratis.

1. **Servidor y canales.** En Discord: **+** → **Crear el mío** → **Para mí y mis amigos**. Después crea los canales de texto `dudas` y `logros`.
2. **Bot.** En [discord.com/developers/applications](https://discord.com/developers/applications):
   1. **New Application**.
   2. En **Bot**, activa **Message Content Intent**.
   3. En **OAuth2 → URL Generator**, marca el scope `bot` y los permisos *View Channels*, *Read Message History* y *Send Messages*.
   4. Abre la URL generada y agrega el bot a tu servidor.
3. **Webhooks** (opcional: solo sirven para reconocer los mensajes de alumnos simulados que ya existan). En cada canal: **Editar canal → Integraciones → Webhooks → Nuevo webhook**.

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
| `DISCORD_MENTOR_ROLE_IDS`, `DISCORD_STAFF_ROLE_IDS` | **Ajustes del servidor → Roles →** clic derecho en el rol **→ Copiar ID del rol** (requiere el Modo desarrollador) |
| `SIMULATED_MENTORS` | Los mentores simulados por su `autor.id`, por ejemplo `sim-andres-mentor` |
| `BACKEND_INGEST_URL` | La puerta de la API Java: `http://127.0.0.1:8008/api/v1/lotes`. Opcional: sin ella, `send_batch.py --prueba` funciona igual |
| `BACKEND_API_KEY` | La clave de la cabecera `X-Api-Key`. **No se escribe a mano:** desde la raíz del repositorio, `python scripts/generar_api_key.py` la crea y la escribe aquí y en el `.env` de la raíz, sin mostrarla |
| `INGEST_REREAD_DAYS` | Días que se releen en cada extracción (por defecto, 7) |

## 4. Usar (en este orden)

| Paso | Comando | Qué hace |
|---|---|---|
| 1 | `.\.venv\Scripts\python.exe verify_connection.py` | Comprueba el token, el permiso de contenido y la lectura de cada canal, y muestra los IDs para el `.env`. Solo lee |
| — | ~~`simulate_students.py`~~ | ⚠️ **No lo ejecutes.** Publica alumnos ficticios y, cada vez que corre, duplica los mensajes. Para probar, escribe los mensajes a mano en Discord |
| 3 | `.\.venv\Scripts\python.exe extract.py` | Descarga los mensajes de los dos canales a `data/raw/<canal>.json`, sin modificarlos, y guarda los roles en `data/raw/context.json`. La primera vez trae todo el historial; después, solo lo nuevo y los últimos días. Con `--todo`, siempre todo. Solo lee |
| 4 | `.\.venv\Scripts\python.exe build_batch.py` | Transforma los mensajes al contrato, **valida cada uno** y escribe el lote en `data/batches/`. Si un mensaje no cumple el contrato, dice qué campo falla |
| 5 | `.\.venv\Scripts\python.exe send_batch.py --prueba` | Revisa que el último lote cumpla el contrato, sin enviar nada. Se envía tal cual, sin convertirlo |
| 5 | `.\.venv\Scripts\python.exe send_batch.py` | Envía el último lote a la API Java, con la API key. Si Java confirma, guarda el marcador para que la próxima extracción pida solo lo nuevo. Reenviar el mismo lote no duplica nada: Java responde `yaRecibido` |

**Pruebas automáticas:** `.\.venv\Scripts\python.exe -m pytest` comprueba cada regla del contrato con mensajes de ejemplo. No se conecta a Discord ni usa `data/`.

**Si cambias el contrato en `contract.py`:** corre `.\.venv\Scripts\python.exe contract.py` para regenerar `schema/contract_v1.schema.json`. Una prueba avisa si te olvidas.

## Seguridad

- **El token del bot y las URLs de los webhooks son contraseñas.** Van solo en `.env`: nunca en el código, en el chat ni en el repo.
- **Si alguno se filtra, se reemplaza:** el token, con **Reset Token**; un webhook, borrándolo y creando otro.
- **`data/` puede contener datos personales** cuando haya alumnos reales. Por eso está excluida del repo.
