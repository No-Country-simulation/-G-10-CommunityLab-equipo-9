# 🤖 Agente FAQ — InsightEdu Lab

> ⚠️ **Documento histórico:** el README original del Agente FAQ, de antes de la integración. **No es una instrucción vigente.** Cómo funciona hoy: [ARQUITECTURA.md](../../ARQUITECTURA.md) · Qué falta: [ESTADO.md](../../ESTADO.md)

Módulo del Agente FAQ (RAG) que responde dudas académicas recurrentes de los estudiantes basándose EXCLUSIVAMENTE en los PDFs institucionales (cursos, requisitos, beneficios).

Forma parte del sistema **InsightEdu Lab** del Hackathon ONE G10 — Equipo 9.

---

## 📋 Tabla de Contenidos

- [Objetivo](#-objetivo)
- [Arquitectura](#-arquitectura)
- [Estructura de Archivos](#-estructura-de-archivos)
- [Contratos de Entrada/Salida](#-contratos-de-entradasalida)
- [Instalación](#-instalación)
- [Configuración](#-configuración)
- [Notas de Compatibilidad](#-notas-de-compatibilidad)

---

## 🎯 Objetivo

El Agente FAQ recibe una pregunta del Orquestador (clasificada como `PREGUNTA_FAQ`) y devuelve una respuesta basada en los PDFs institucionales, con:

- **Citación de fuente** (archivo + página).
- **Scores de confianza** (similitud RAG + fidelidad al contexto).
- **Guardrail anti-alucinación** (valida que la respuesta esté respaldada por el contexto).
- **Reporte de metadata** con detección de preguntas repetidas.

Si no encuentra respuesta en los PDFs, **no la inventa**: deriva a un mentor humano.

---

## 🏗️ Arquitectura

```text
┌─────────────────────────────────────────────────────────────┐
│ ORQUESTADOR (LangGraph)                                     │
│ Clasifica como PREGUNTA_FAQ                                 │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ AGENTE FAQ (LangChain + AgentExecutor)                      │
│                                                             │
│ Tool 1 "Buscador":                                          │
│ → Retrieval (FAISS, top 8)                                  │
│ → Reranking (Cross-Encoder, top 3)                          │
│ → Generación (LLM con prompt estricto)                      │
│ → Guardrail (validación de fidelidad)                       │
│                                                             │
│ Tool 2 "Reporte":                                           │
│ → Detección de preguntas repetidas                          │
│ → Generación de reporte con metadata                        │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Output: respuesta + reporte (JSON)                          │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Estructura de Archivos

```md
agents/agent-faq/
├── README.md                  ← Correspondiente al modulo FAQ
├── requirements.txt           ← Dependencias del módulo **REVISAR**
├── config.py                  ← Configuración centralizada
├── contratos.py               ← Schemas Pydantic (contratos del agente)
├── llm_models.py              ← Configuracion modelos LLM (multi-proveedor) **REVISAR**
├── agente_faq.py              ← Lógica principal del agente **REVISAR**
│
├── data/
│   ├── pdfs/                  ← PDFs institucionales
│   ├── vectorstore/           ← Índices FAISS (se generan automaticamente)
│   │   ├── faiss_pdfs/
│   │   └── faiss_preguntas/
│   └── historial_preguntas.json ← Histórico de preguntas (se genera automaticamente)
│
├── prompts/
│   └── prompts.py             ← System prompts y plantillas, **REVISAR**
│
├── tools/
│   ├── buscador.py            ← Tool 1: RAG + Rerank + Guardrail **REVISAR**
│   ├── reporte_faq.py         ← Tool 2: Metadata + frecuencia **REVISAR**
│   └── crear_herramientas.py  ← Fábrica de tools **REVISAR**
│
└── vectorstore/
    ├── embedding_models.py    ← Fábrica de embeddings
    ├── loader.py              ← Carga de PDFs + chunking
    ├── store.py               ← FAISS para PDFs
    ├── preguntas_store.py     ← FAISS para preguntas anteriores
    └── reranker.py            ← Cross-Encoder
```

## 📜 Contratos de Entrada/Salida

**Contrato de Entrada**
Corresponde a una pregunta simple en un str. Si el orquestador en lugar de una pregunta simple maneja una estructura, se debe implementar un contrato de entrada.

**Contratos de Salida** (hacia el Orquestador)
Ver contratos.py:

- `BuscadorOutput` — Output de la Tool "Buscador".
- `ReporteFAQ` — Output de la Tool "Reporte".
- `EvaluacionFidelidad` — Output del guardrail.
- `AnalisisFrecuencia` — Análisis de repetición.
- `PreguntaSimilar` — Representa una pregunta previa similar.

## 🔧 Instalación

**Requisito previo (obligatorio)**
**`Python 3.12`**

### Pasos

```Bash
# 1. Crear entorno virtual
python3.12 -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate    # Linux/macOS

# 2. Instalar dependencias
pip install -r agents/agent-faq/requirements.txt
```

## ⚙️ Configuración

**Variables de entorno (.env):**

- Cambiar de proveedor de LLM o embeddings solo requiere modificar las variables de entorno.

```python
# LLM (elegir uno)
LLM_PROVIDER=google
LLM_MODEL_NAME=gemini-1.5-flash
GEMINI_API_KEY=tu_api_key_aqui

# Embeddings (elegir uno)
EMBEDDING_PROVIDER=huggingface
EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-small
```

**Parámetros de `config.py`**

- Todos los umbrales, rutas y parámetros de chunking están centralizados en `config.py`.

## ⚠️ Notas de Compatibilidad

**IMPORTANTE: Este módulo está en revisión activa. La instalación puede requerir ajustes manuales debido a cambios recientes en el ecosistema de LangChain.**

### Problemas conocidos

**Migración a `langchain-classic`:**
Muchas clases que antes estaban en langchain ahora viven en `langchain-classic` (ej. create_react_agent, AgentExecutor). Si al importar aparece un ImportError, verificar los imports:

```Python
# Antes
from langchain.agents import create_react_agent

# Ahora
from langchain_classic.agents import create_react_agent
```

**Versiones de LangChain**
El ecosistema de LangChain cambia rápido. Se recomienda fijar versiones específicas en requirements.txt para evitar romper la compatibilidad.

FAISS y embeddings locales
`faiss-cpu` y `sentence-transformers` pueden requerir dependencias del sistema (compiladores, BLAS). En entornos limitados, considerar usar embeddings de Google/OpenAI.
