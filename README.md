# Cubik-Lite — Tutor de Cálculo Integral

**Español** | [English](README.en.md)

Asistente conversacional de tutoría para cálculo integral. Responde preguntas de teoría y guía la resolución de
ejercicios paso a paso, citando la regla o técnica aplicada, y fundamenta sus respuestas en una base de
conocimiento propia mediante RAG en vez de depender solo del conocimiento general del modelo. Ver
[PROPOSAL.md](PROPOSAL.md) para el alcance completo.

La documentación técnica está en español en [`docs/es/`](docs/es/) y en inglés en [`docs/en/`](docs/en/).

## Arquitectura

| Pieza | Archivo | Qué hace |
|---|---|---|
| Chat | [`main.py`](main.py) | Loop interactivo de terminal. |
| Agente ADK | [`agents/cubik_tutor/agent.py`](agents/cubik_tutor/agent.py) | El mismo tutor como agente de Google ADK: el RAG es una tool y guarda preferencias y progreso en el estado de sesión. Ver [docs/es/adk_agent.md](docs/es/adk_agent.md). |
| Equipo multiagente | [`agents/cubik_team/agent.py`](agents/cubik_team/agent.py) | Versión de Corte 2: un coordinador enruta cada mensaje a un especialista de teoría, de resolución o de verificación, y consulta el progreso como `AgentTool`. Ver [docs/es/multi_agent_design.md](docs/es/multi_agent_design.md). |
| Cálculo exacto | [`math_tools.py`](math_tools.py) | Resuelve integrales y comprueba respuestas con SymPy, para que el resultado y el veredicto no dependan del modelo. |
| Selección de modelo | [`llm_client.py`](llm_client.py) | Gemini si hay `GEMINI_API_KEY`, si no un modelo local vía Ollama. |
| Contexto conversacional | [`context_manager.py`](context_manager.py) | Ventana deslizante de turnos + presupuesto de caracteres. Ver [docs/es/context_strategy.md](docs/es/context_strategy.md). |
| RAG | [`retriever.py`](retriever.py) | Indexa `data/` en ChromaDB y recupera los chunks más relevantes por pregunta. Ver [docs/es/rag_strategy.md](docs/es/rag_strategy.md). |
| System prompt | [`prompts/system_prompt.txt`](prompts/system_prompt.txt) | Rol, alcance, reglas de rechazo y formato de salida JSON. |
| Prompts del equipo | [`prompts/team/`](prompts/team/) | Reglas compartidas (`shared.txt`) y el rol de cada agente del equipo multiagente. |
| Base de conocimiento | [`data/`](data/README.md) | Reglas, técnicas y aplicaciones de integración, en Markdown. |

## Setup

1. Instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

2. Copia `.env.example` a `.env`:

   ```bash
   cp .env.example .env
   ```

   `GEMINI_API_KEY` es **opcional**. Si la defines (consigue una key gratis en
   https://aistudio.google.com/apikey), el asistente usa la API de Gemini para chat y embeddings. Si la dejas
   vacía o con el placeholder, cae automáticamente a un modelo local vía [Ollama](https://ollama.com/):

   ```bash
   ollama pull qwen2.5:14b
   ollama pull nomic-embed-text
   ```

3. Construye el índice de RAG (hay que rehacerlo si cambia el contenido de `data/`, **o si cambias de
   proveedor**: los embeddings de Gemini y de Ollama no son intercambiables, así que alternar entre
   `GEMINI_API_KEY` presente/ausente exige reindexar):

   ```bash
   python retriever.py
   ```

4. Corre el chat:

   ```bash
   python main.py
   ```

   Comandos dentro del chat: `salir` para terminar, `limpiar` para reiniciar el historial.

5. (Opcional) Corre los agentes de Google ADK, desde la raíz del repo. También necesitan el índice del paso 3:

   ```bash
   adk web agents              # UI web con trace de cada llamada a tools; elige cubik_tutor o cubik_team
   adk run agents/cubik_tutor  # tutor de un solo agente (semana 7) en la terminal
   adk run agents/cubik_team   # equipo multiagente (Corte 2) en la terminal
   ```

   Para que las preferencias del estudiante (`user:`) sobrevivan a reiniciar `adk web`, usa un session service
   persistente: `adk web agents --session_service_uri sqlite:///adk_sessions.db`.

## Tests

```bash
pytest tests/
```

Cubre el gestor de contexto (`context_manager.py`), el chunking del RAG (`retriever.py`), las tools del agente ADK
(`agents/cubik_tutor/agent.py`), las tools de SymPy (`math_tools.py`) y la estructura del equipo multiagente
(`agents/cubik_team/agent.py`). La indexación y recuperación reales, que dependen de un proveedor de embeddings
activo (Gemini o Ollama), y el enrutamiento del equipo, que depende del modelo, se verifican a mano corriendo
`python retriever.py`, `python main.py` y `adk web agents`.
