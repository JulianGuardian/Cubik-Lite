# Cubik-Lite — Integral Calculus Tutor

[Español](README.md) | **English**

Conversational tutoring assistant for integral calculus. It answers theory questions and guides students through
exercises step by step, citing the rule or technique applied, and grounds its answers in its own knowledge base
through RAG instead of relying only on the model's general knowledge. See [PROPOSAL.md](PROPOSAL.md) for the
full scope.

The tutor talks to students in Spanish, and its knowledge base in [`data/`](data/README.md) is in Spanish. The
technical documentation is in English in [`docs/en/`](docs/en/) and in Spanish in [`docs/es/`](docs/es/).

## Architecture

| Component | File | What it does |
|---|---|---|
| Chat | [`main.py`](main.py) | Interactive terminal loop. |
| ADK agent | [`agents/cubik_tutor/agent.py`](agents/cubik_tutor/agent.py) | The same tutor as a Google ADK agent: RAG is a tool, and it stores preferences and progress in session state. Resetting progress asks the student for approval. See [docs/en/adk_agent.md](docs/en/adk_agent.md). |
| Multi-agent team | [`agents/cubik_team/agent.py`](agents/cubik_team/agent.py) | Corte 2 version: a coordinator routes each message to a theory, solver or verifier specialist, and asks for progress through an `AgentTool`. See [docs/en/multi_agent_design.md](docs/en/multi_agent_design.md). |
| Exact math | [`math_tools.py`](math_tools.py) | Solves integrals and checks answers with SymPy, so the result and the verdict don't depend on the model. |
| Model selection | [`llm_client.py`](llm_client.py) | Gemini if `GEMINI_API_KEY` is set, otherwise a local model through Ollama. |
| Conversation context | [`context_manager.py`](context_manager.py) | Sliding window of turns + character budget. See [docs/en/context_strategy.md](docs/en/context_strategy.md). |
| RAG | [`retriever.py`](retriever.py) | Indexes `data/` in ChromaDB, retrieves candidate chunks for each question and re-ranks them with the chat model to keep the best ones. See [docs/en/rag_strategy.md](docs/en/rag_strategy.md). |
| System prompt | [`prompts/system_prompt.txt`](prompts/system_prompt.txt) | Role, scope, refusal rules and JSON output format. |
| Team prompts | [`prompts/team/`](prompts/team/) | Shared rules (`shared.txt`) and the role of each agent in the multi-agent team. |
| Knowledge base | [`data/`](data/README.md) | Integration rules, techniques and applications, in Markdown. |

## Setup

1. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env`:

   ```bash
   cp .env.example .env
   ```

   `GEMINI_API_KEY` is **optional**. If you set it (get a free key at
   https://aistudio.google.com/apikey), the assistant uses the Gemini API for chat and embeddings. If you leave it
   empty or with the placeholder, it automatically falls back to a local model through
   [Ollama](https://ollama.com/):

   ```bash
   ollama pull qwen2.5:14b
   ollama pull nomic-embed-text
   ```

3. Build the RAG index (rebuild it if the content of `data/` changes, **or if you switch providers**: Gemini and
   Ollama embeddings aren't interchangeable, so switching between having and not having `GEMINI_API_KEY`
   requires reindexing):

   ```bash
   python retriever.py
   ```

4. Run the chat:

   ```bash
   python main.py
   ```

   Commands inside the chat (in Spanish): `salir` to quit, `limpiar` to reset the history.

5. (Optional) Run the Google ADK agents from the repo root. They also need the index from step 3:

   ```bash
   adk web agents              # web UI with a trace of every tool call; pick cubik_tutor or cubik_team
   adk run agents/cubik_tutor  # single-agent tutor (Week 7) in the terminal
   adk run agents/cubik_team   # multi-agent team (Corte 2) in the terminal
   ```

   To keep the student's preferences (`user:`) across `adk web` restarts, use a persistent session service:
   `adk web agents --session_service_uri sqlite:///adk_sessions.db`.

## Tests

```bash
pytest tests/
```

They cover the context manager (`context_manager.py`), RAG chunking and re-ranking (`retriever.py`), the ADK agent's tools
(`agents/cubik_tutor/agent.py`), the SymPy tools (`math_tools.py`) and the structure of the multi-agent team
(`agents/cubik_team/agent.py`). Real indexing and retrieval, which depend on an active embedding provider (Gemini
or Ollama), and the team's routing, which depends on the model, are checked by hand by running
`python retriever.py`, `python main.py` and `adk web agents`.
