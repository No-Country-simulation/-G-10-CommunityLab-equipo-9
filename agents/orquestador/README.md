# 🤖 Orquestador — InsightEdu Lab

> ⚠️ **Nota de T05 (2026-10-04): este README describe el diseño anterior.**
> La puerta `POST /procesar` (formato viejo, la usaba el bot directo) **ya no existe**: el bot pasa por la API Java (C2).
> Hoy la IA expone solo `POST /v1/procesar` y `GET /health`. Su contrato está en [docs/contratos/JAVA_IA_v1.md](../../docs/contratos/JAVA_IA_v1.md).
>
> | Lo que **sí** se usa | Lo que **ya no** se usa (se borra más adelante, mejora 🟡, DEC-69) |
> |---|---|
> | `api.py`, `grafo_v1.py`, `contrato_ia.py`, `config.py`, `config_http.py` (solo sus constantes de rutas y puerto), `clasificadores/etiquetador.py`, `clasificadores/keyword_fallback.py` (con su `base.py`), `clasificadores/llm_models.py`, `nodos/invocador_faq.py` (solo la carga compartida del Agente FAQ) y `contratos.py` (lo importan `keyword_fallback.py` e `invocador_faq.py`) | `orquestador.py`, `adaptador.py`, `test_orquestador.py`, `aristas/`, el resto de `nodos/` y de `clasificadores/`, y `storage/` |

Motor de triaje y enrutamiento del sistema **InsightEdu Lab**. Recibe mensajes
crudos de Discord, los filtra, clasifica y delega a los sub-agentes
especializados.

Forma parte del Hackathon ONE G10 — Equipo 9.

---

## 📋 Tabla de Contenidos

- [Objetivo](#-objetivo)
- [Arquitectura](#-arquitectura)
- [Estructura de Archivos](#-estructura-de-archivos)
- [Categorías de Clasificación](#-categorías-de-clasificación)
- [Instalación](#-instalación)
- [Configuración](#-configuración)
- [Uso](#-uso)
- [API HTTP](#-api-http)
- [Contratos](#-contratos)
- [Estado Actual](#-estado-actual)
- [Roadmap](#-roadmap)
- [Equipo](#-equipo)

---

## 🎯 Objetivo

El Orquestador es el **primer punto de contacto** del sistema. Su misión es
recibir un lote de mensajes crudos de Discord (tal como los emite la API del
bot) y devolver una respuesta lista para que n8n la publique en el canal
correspondiente.

**Responsabilidades:**

1. **Filtrar ruido:** Descartar bots, comandos y mensajes vacíos.
2. **Clasificar:** Asignar una de las 4 categorías a cada mensaje.
3. **Enrutar:** Delegar al sub-agente correspondiente (Agente-Mod o Agente FAQ).
4. **Consolidar:** Empaquetar los resultados, generar logs y preparar la
   respuesta para Discord.
5. **Persistir:** Almacenar en OCI Object Storage + ChromaDB local.

---

## 🏗️ Arquitectura



----

## 📁 Estructura de Archivos

```text
agents/orquestador/
├── init.py
├── README.md ← Este archivo
├── requirements.txt ← Dependencias del módulo
│
├── config.py ← Configuración centralizada
├── config_http.py ← Contrato HTTP para el backend
├── contratos.py ← Schemas Pydantic
├── adaptador.py ← Webhook Discord → Input normalizado
├── orquestador.py ← StateGraph de LangGraph
├── api.py ← Endpoint FastAPI
├── test_orquestador.py ← Script de prueba standalone
│
├── clasificadores/ ← Clasificadores intercambiables
│ ├── init.py
│ ├── base.py ← Interfaz abstracta
│ ├── generic_adapter.py ← Adaptador genérico (Gemini/OpenAI/Cohere)
│ ├── laya_adapter.py ← Laya (en entrenamiento)
│ ├── keyword_fallback.py ← Fallback por keywords
│ ├── llm_models.py ← Fábrica de LLMs
│ └── laya_guardrail.py ← Guardrail anti-prompt-injection (opcional)
│
├── nodos/ ← Nodos del grafo
│ ├── init.py
│ ├── filtro_ruido.py
│ ├── clasificador.py
│ ├── invocador_mod.py
│ ├── invocador_faq.py
│ ├── descarte.py
│ └── consolidacion.py
│
├── aristas/ ← Aristas condicionales
│ ├── init.py
│ └── enrutamiento.py
│
├── storage/ ← Clientes de persistencia
│ ├── init.py
│ ├── oci_client.py ← OCI Object Storage
│ └── chroma_client.py ← ChromaDB local
│
└── data/ ← Generado localmente (gitignored)
├── chroma/
└── vectorstore/
```

---

## 🏷️ Categorías de Clasificación

| Categoría | Descripción | Sub-agente |
|---|---|---|
| **TESTIMONIO** | Logro verificable: contratación, certificación, beca, reconocimiento. | Agente-Mod |
| **PREGUNTA_FAQ** | Duda académica recurrente: cursos, inscripciones, requisitos, fechas. | Agente FAQ |
| **COMENTARIO** | Opinión o sentimiento sin logro verificable (positivo, negativo o neutro). | Agente-Mod |
| **OTRO** | Saludos, comandos, spam o ruido. | Descarte |

---

## 🔧 Instalación

### Requisitos

- **Python 3.12**
- Entorno virtual (`venv` o `uv`)

### Instalación de dependencias

```bash
# Crear entorno virtual (primera vez)
python -m venv .venv

# Activar
# Linux / macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Instalar dependencias del módulo
pip install -r agents/orquestador/requirements.txt

```

## ⚙️ Configuración

Variables de entorno (.env en la raíz)

```python

# ============================================================
# CLASIFICADOR DEL ORQUESTADOR
# ============================================================
# Proveedor activo: "gemini" | "openai" | "cohere" | "laya" | "keyword"
ORQ_CLASIFICADOR_PROVIDER=gemini
ORQ_CLASIFICADOR_MODEL=gemini-2.0-flash-exp
ORQ_CLASIFICADOR_TEMPERATURE=0.0

# API Keys (solo se usa la del proveedor activo)
GEMINI_API_KEY=tu_api_key_aqui
# OPENAI_API_KEY=tu_api_key_aqui
# COHERE_API_KEY=tu_api_key_aqui

# ============================================================
# LAYA (en entrenamiento, desactivado por defecto)
# ============================================================
LAYA_ENABLED=false
LAYA_MODEL=multilingual

# ============================================================
# OCI OBJECT STORAGE (opcional para el MVP)
# ============================================================
OCI_BUCKET=communitylab-activos-marketing
OCI_NAMESPACE=tu_namespace_oci
OCI_REGION=us-ashburn-1
# OCI_CONFIG_PATH=~/.oci/config

# ============================================================
# SUB-AGENTES
# ============================================================
ORQ_SUBAGENTE_MOD_PATH=agents.agent_mod.agente_mod.AgenteMod
ORQ_SUBAGENTE_FAQ_PATH=agents.agent_faq.agente_faq.AgenteFAQ
```

Cambiar de proveedor
Solo cambia 2 variables en .env:

```python
# Ejemplo: cambiar de Gemini a OpenAI
ORQ_CLASIFICADOR_PROVIDER=openai
ORQ_CLASIFICADOR_MODEL=gpt-4o-mini
OPENAI_API_KEY=tu_api_key
```

## 🚀 Uso

Simula un webhook crudo de Discord con 4 mensajes (testimonio, FAQ,
comentario, bot) y muestra el resultado formateado.

```bash
python -m agents.orquestador.test_orquestador
```

Salida esperada:

```text
[GenericAdapter] Inicializado (ChatGoogleGenerativeAI).
[Nodo] filtro_ruido
[Nodo] clasificador
[Nodo] invocador_mod
[Nodo] invocador_faq
[Nodo] descarte
[Nodo] consolidacion

📨 Mensaje ID: msg_001
   Canal: canal_logros
   Intención: TESTIMONIO
   Requiere humano: ⚠️ Sí
   Respuesta: ...

RESUMEN DEL LOTE
======================================================================
Total mensajes:       4
Descartados (filtro): 1
Testimonios:          1
Preguntas FAQ:        1
Comentarios:          1
Otro:                 0

```

## API HTTP (FastAPI)
```bash
uvicorn agents.orquestador.api:app --host 0.0.0.0 --port 8000 --reload
```

## 🌐 API HTTP

Endpoints expuestos
Método	Endpoint	Descripción
POST	/procesar	Recibe un lote de mensajes y devuelve la respuesta consolidada.
GET	/health	Verificación de salud del servicio.
GET	/docs	Swagger UI generado automáticamente.

## Contrato de entrada (POST /procesar)

```json
{
  "origen": "discord",
  "servidor": "Discord_ONE_G10",
  "mensajes": [
    {
      "id": "1553613486452383815",
      "channel_id": "1553596454248124467",
      "author": {
        "id": "1553598997250318336",
        "username": "Gabriel Lopez",
        "bot": false
      },
      "content": "Hola, quisiera saber cuándo comienzan las inscripciones...",
      "timestamp": "2026-10-01T03:45:19.913000+00:00"
    }
  ]
}
```

Nota: El adaptador filtra automáticamente los campos irrelevantes del
webhook crudo de Discord (avatar, flags, discriminator, etc.). Solo se
conservan los campos mostrados arriba.

Contrato de salida

```json
{
  "lote_id": "lote_20261001_143022_a3f5b8",
  "respuesta_discord": {
    "lote_id": "lote_20261001_143022_a3f5b8",
    "respuestas": [
      {
        "mensaje_id": "1553613486452383815",
        "channel_id": "1553596454248124467",
        "texto_respuesta": "📚 ¡Hola Gabriel! Las inscripciones...",
        "requiere_humano": false,
        "intencion": "PREGUNTA_FAQ"
      }
    ]
  },
  "paquete_final": { ... },
  "log_ejecucion": { ... }
}
```

## 📜 Contratos

Todos los contratos están definidos con Pydantic v2 en contratos.py.

| **Schema** | **Propósito** |
| --- | --- |
| InputOrquestador | Entrada del Orquestador (desde adaptador). |
| MensajeNormalizado | Mensaje individual limpio. |
| ClasificacionIntencion | Output del clasificador. |
| OutputSubAgente | Shell común de los sub-agentes. |
| PaqueteFinal | Paquete de auditoría con resumen del lote. |
| LogEjecucion | Métricas y trazabilidad. |
| RespuestaDiscord | Respuestas listas para n8n. |
| OutputOrquestador | Contrato de salida completo. |
