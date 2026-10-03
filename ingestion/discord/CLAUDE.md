# CLAUDE.md — Ingesta de Discord (InsightEdu Lab)

Contexto para Claude Code al trabajar en `ingestion/discord/`, desde cualquier máquina. La memoria de sesiones anteriores **no viaja entre máquinas**: este archivo y la carpeta `docs/` son la fuente de contexto.

## Antes de responder

Lee, en este orden:
1. [README.md](README.md): qué es el módulo y cómo se corre.
2. [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md): el brief del cliente, los objetivos de negocio y qué entra en el MVP. Es la referencia para decidir el contrato.
3. [docs/SCOPE.md](docs/SCOPE.md): objetivos O1–O5, decisiones, pendientes P1–P7 y criterios de terminado.
4. [docs/DISCORD_DATA_GUIDE.md](docs/DISCORD_DATA_GUIDE.md): cómo son los datos de Discord (hallazgos, riesgos e implicaciones para el contrato).
5. [docs/EVENT_CATALOG.md](docs/EVENT_CATALOG.md): el catálogo de eventos de la comunidad, que es la base del contrato.
6. [docs/ARCHITECTURE_PROPOSAL.md](docs/ARCHITECTURE_PROPOSAL.md): la arquitectura propuesta (dos flujos, un contrato). Por ahora se discute solo con el usuario, no con el equipo.
7. [docs/CONTRACT.md](docs/CONTRACT.md): el contrato de ingesta v1. Se diseñó de forma independiente de backend y del motor IA, y se compara con ellos después de validarlo.
8. [docs/INGESTION_GUIDE.md](docs/INGESTION_GUIDE.md): la explicación para el equipo (nivel training), con lotes y en vivo, los duplicados, la comparación con backend y las opciones A, B y C (se recomienda la C, "etiqueta + caja").

## Proyecto

- **InsightEdu Lab:** hackatón de No Country y ONE, grupo G10, equipo 9. Dura 5 semanas; **la entrega final es el 2026-10-26**. Solo Discord.
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
- **Hecho (2026-10-01): contrato validado** ([docs/CONTRACT.md](docs/CONTRACT.md), v0.2). Las 7 decisiones de la §8 están aprobadas. Criterio: el contrato debe funcionar con una institución real, no solo con la simulación. Las más importantes:
  - el rol del autor sale de sus roles reales de Discord, con un mapeo configurado y una lista de respaldo para los simulados;
  - el campo `hilo` existe desde la v1, en `null`.
  Los ejemplos de la §7 salen de [prototypes/contract_prototype.py](prototypes/contract_prototype.py), un prototipo desechable.
- **Del brief no entran:** X, newsletters ni *Community Highlights* (ver [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md)).
- **Hecho (2026-10-02): comparación con backend** (`feature/java-core-api`, commit b5e03e9), documentada en [docs/INGESTION_GUIDE.md](docs/INGESTION_GUIDE.md). Falta la respuesta de backend sobre las opciones A, B y C.
- **Hecho (2026-10-02): la ingesta por lotes completa.**
  - Archivos: `contract.py` (pydantic y JSON Schema), `transform.py` (función pura), `extract.py` (incremental, con marcador, relectura de 7 días y roles en `context.json`), `build_batch.py` (valida y arma el lote) y `send_batch.py` (opción C, "etiqueta + caja", y marcador).
  - 34 pruebas con `pytest`. Los 38 mensajes cumplen el contrato.
- **Falta:**
  - probar el envío contra el backend real cuando aplique la opción C;
  - el pull request a `main` (meta: 2026-10-10);
  - el bot en vivo, en otra rama.
- **Especificación del endpoint para backend:** por ahora la cubren el JSON Schema y [docs/INGESTION_GUIDE.md](docs/INGESTION_GUIDE.md) §11. Se cierra cuando backend elija una opción.

## Cómo trabajar con el usuario

- **Idioma y nivel.** Responder en español. El usuario está aprendiendo git, sabe Python básico y es su primer proyecto de este tipo: explicar desde cero, con ejemplos de InsightEdu.
- **No ampliar el alcance.** Ante cada idea nueva, preguntar: ¿cambia el contrato? Si no lo cambia, va a pendientes. El usuario pidió explícitamente no seguir sumando documentación.
- **Diseño independiente.** El contrato se diseña desde el catálogo de eventos, sin tomar como referencia a backend ni al motor IA, para no sesgarlo. Cada campo cita los casos del catálogo que lo necesitan. La comparación con los demás equipos se hace al final.
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
0. **Seguridad al abandonar una máquina.** El repo de la máquina anterior estaba dentro de OneDrive, así que su `.env` (token y URLs de los webhooks) y `data/` se sincronizaron a la nube. Para anular esas copias:
   - pedir un token nuevo con **Reset Token** y actualizar el `.env` de la máquina actual;
   - opcionalmente, borrar los webhooks y crear otros nuevos.

   Revisar también la identidad de git: `git config --global user.name` y `user.email` deben ser los de la cuenta de GitHub. En la máquina anterior, git había configurado un correo local automáticamente.
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
