# CLAUDE.md — Ingesta de Discord (InsightEdu Lab)

Contexto para Claude Code al trabajar en `ingestion/discord/`, desde cualquier máquina. La memoria de sesiones anteriores **no viaja entre máquinas**: este archivo y la carpeta `docs/` son la fuente de contexto.

## Antes de responder

Lee, en este orden:
1. [README.md](README.md): qué es el módulo y cómo se corre.
2. [docs/SCOPE.md](docs/SCOPE.md): objetivos O1–O5, decisiones, pendientes P1–P7 y criterios de terminado.
3. [docs/DISCORD_DATA_GUIDE.md](docs/DISCORD_DATA_GUIDE.md): cómo son los datos de Discord (hallazgos, riesgos e implicaciones para el contrato).
4. [docs/EVENT_CATALOG.md](docs/EVENT_CATALOG.md): la interpretación del brief del proyecto y el catálogo de eventos de la comunidad, que es la base del contrato.
5. [docs/ARCHITECTURE_PROPOSAL.md](docs/ARCHITECTURE_PROPOSAL.md): la arquitectura propuesta (dos flujos, un contrato), pendiente de discutir con el equipo.

## Proyecto

- **InsightEdu Lab:** hackatón de No Country y ONE, grupo G10, equipo 9. Dura 5 semanas; al 2026-09-28 había pasado 1.
- **Flujo:** Discord → ingesta (este módulo, en Python) → API Java (`backend-java/`) → motor IA con LLM (`agents/`, rama `feature/ai-engine`) → API Java → respuesta en Discord (fase 2).
- **Canales:** `#dudas` y `#logros`. Todo está simulado en un servidor de pruebas.
- **Equipo:** nivel training, sin experiencia previa con Discord. La ingesta define la pauta (el contrato) que el backend implementa.

## Estado (2026-09-29)

- **Hecho:** O1 (entorno simulado), O2 (conexión y extracción) y O3 (guía y diccionario de datos).
- **Decisiones del producto:**
  - El MVP incluye post de LinkedIn, caso de éxito, FAQ o contenido educativo, dashboard de salud con alertas, y un bot que responde dudas en vivo (por eso la ingesta en tiempo real entra en el MVP).
  - OCI Object Storage es obligatorio para los activos generados.
  - Databricks queda descartado.
- **Decisiones de alcance:**
  - El catálogo de eventos está aprobado (v1.0).
  - En el MVP no hay hilos ni foros (P5 descartado) ni datos de los miembros.
  - La ampliación de la simulación queda pospuesta.
  - Esta rama termina con el contrato v1, su entrega y un pull request a `main`. El bot en vivo va en otra rama.
- **Siguiente: O4.** Consolidar en una sola lista los datos que pide el catálogo, proponer el contrato v1 y **validarlo con el usuario antes de programar**. Después, el modelo `pydantic` que genera el JSON Schema y la transformación de `data/raw/` al contrato.
- **Luego: O5.** Salida a archivo, POST a la API Java y especificación del endpoint para backend.

## Cómo trabajar con el usuario

- **Idioma y nivel.** Responder en español. El usuario está aprendiendo git, sabe Python básico y es su primer proyecto de este tipo: explicar desde cero, con ejemplos de InsightEdu.
- **No ampliar el alcance.** Ante cada idea nueva, preguntar: ¿cambia el contrato? Si no lo cambia, va a pendientes. El usuario pidió explícitamente no seguir sumando documentación.
- **Definir antes de programar.** Seguir el orden escenario → objetivos → evaluación → alcance; proponer y esperar la validación.
- **Mejor opción a largo plazo.** Elegir lo mejor en eficiencia, seguridad e integración, no lo más fácil, y explicarlo bien.
- **Precisión.** Verificar en la documentación oficial de Discord (repo `discord/discord-api-docs`, carpeta `developers/`) y separar lo verificado de lo inferido.
- **Código.** Claude escribe el código Python; el usuario lo revisa y lo ejecuta.
- **Git.** Lo ejecuta el usuario: darle los comandos exactos, incluido un `git status` para comprobar que no se suben `.env` ni `data/`. Hacer commit o push solo si lo pide explícitamente.
- **Documentación para el equipo.** Debe entenderse sin haber leído el chat. Cada sección lleva una introducción, cada afirmación su fuente (📘 documentación, 🧪 simulado, 👤 usuario real), y hay ejemplos.

## Convenciones

- **Nombres:** carpetas y archivos en inglés; el código (funciones y variables), los comentarios y la documentación, en español.
- **Stack:**
  - Python 3.12 con `httpx` (REST) y `python-dotenv`.
  - `discord.py`, solo para la fase de tiempo real (Gateway).
  - `pydantic` para el contrato.
- **Secretos y datos:** la configuración y los secretos van solo en `.env` (plantilla: `.env.example`). `data/`, con los mensajes extraídos, está en `.gitignore`.
- **Contrato:** 1 mensaje de Discord = 1 registro. Se conserva el texto original y se toman solo los campos necesarios.

## Cuidado

- **No volver a correr `simulate_students.py`:** los mensajes ya están publicados y se duplicarían.
- **No leer, imprimir ni commitear el contenido de `.env`:** tiene el token del bot y las URLs de los webhooks.
- **No subir `data/`** ni copiar datos personales a la documentación; ocultar el usuario y el ID reales.
- **Windows y PowerShell:** si `Activate.ps1` está bloqueado, usar `.\.venv\Scripts\python.exe` en lugar de activar el entorno.
- **Permisos de Discord:** si falta el permiso Read Message History, la API devuelve una lista vacía, sin error.

## Continuar en otra máquina

Guía al usuario con estos pasos:
1. **En la máquina anterior,** `git status` debe decir `nothing to commit, working tree clean` y `up to date`.
2. **Instalar** Git y Python 3.12.
3. **Clonar y cambiar de rama:**
   ```powershell
   git clone https://github.com/No-Country-simulation/-G-10-CommunityLab-equipo-9.git
   cd -G-10-CommunityLab-equipo-9
   git switch feature/discord-ingestion
   ```
4. **Instalar el entorno:** seguir el README desde "2. Instalar". Discord ya está preparado; no hay que repetir la sección 1.
5. **Recrear `.env` desde `.env.example`.** Hay dos caminos:
   - copiarlo de forma segura (por ejemplo, con un gestor de contraseñas);
   - pedir un token nuevo con **Reset Token**, que invalida el anterior.

   Las URLs de los webhooks se vuelven a copiar desde Discord, y los IDs los muestra `verify_connection.py`.
6. **Probar:** correr `verify_connection.py` y, si hacen falta datos, `extract.py`. `data/` no viaja por git.
7. **Si usa las dos máquinas:** `git pull` al empezar y `add`, `commit` y `push` al terminar.
