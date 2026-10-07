# Google ADK agent

## 1. What changes compared to `main.py`

`agents/cubik_tutor/` is the same tutor as `main.py` (same system prompt, same RAG over `data/`, same
Gemini/Ollama switch from `llm_client.py`), but running as a Google ADK agent:

| | `main.py` | ADK agent |
|---|---|---|
| Retrieval | `main.py` calls `retriever.query()` and prepends the "Contexto recuperado" block to each question. | The model decides to call the `search_knowledge_base` tool, which wraps `retriever.query()`. |
| History | `SlidingWindowManager` in process memory. | ADK's `SessionService`: events and state per session. |
| Loop | A single `completion()` call per turn. | The `Runner` runs the model → tool → model cycle until the final answer. |
| Model | `litellm.completion(CHAT_MODEL)` | ADK's native Gemini if `GEMINI_API_KEY` is set; otherwise, `LiteLlm` pointing to Ollama. |
| Output | JSON from the system prompt. | The same JSON (the agent reuses `prompts/system_prompt.txt`). |

`main.py` was not touched: the Corte 1 chat keeps working the same way.

## 2. Tools and state scope

ADK builds each tool's schema from its type hints and its docstring. `tool_context` is injected by ADK and is
not exposed to the model.

| Tool | State key | Scope | Why that scope |
|---|---|---|---|
| `search_knowledge_base` | `temp:last_sources` | Turn | The retrieved sources only matter for the current answer; the next turn searches again. |
| `set_explanation_level` | `user:explanation_level` | User (all of their sessions) | It is a preference of the student, not of a single conversation or of all students. |
| `log_practice_attempt` | `practice_log` | Session | The practice log belongs to this conversation; a new session starts from scratch. |
| `log_practice_attempt` | `app:total_attempts_all_users` | App (all users) | It is a global counter for the tutor, shared by everyone. |
| `get_progress_summary` | reads the ones above | — | Read-only. |
| `reset_practice_log` | `practice_log` | Session | Clears only the session; it does not touch `user:` or `app:`. |

The agent's instruction injects `{user:explanation_level?}` to adjust the level of detail in the `steps`. The `?`
makes the variable optional: if the student has not chosen a level yet, it is replaced with an empty value instead
of failing.

## 3. How to run it

From the repo root, with the RAG index already built (`python retriever.py`):

```bash
adk web agents
```

Scope test in the UI:

1. "Prefiero explicaciones detalladas. ¿Cuál es la integral de x·e^x dx?" (I prefer detailed explanations. What
   is the integral of x·e^x dx?) → the trace shows `set_explanation_level` and `search_knowledge_base`, and the
   answer cites `techniques/integration_by_parts.md`.
2. "Ya lo resolví, anótalo" (I already solved it, log it) → `log_practice_attempt`.
3. Open a **new session with the same user**: `user:explanation_level` and `app:total_attempts_all_users`
   are still there, and `practice_log` is empty.

With the default `InMemorySessionService`, everything is lost when `adk web` restarts. To keep it:
`adk web agents --session_service_uri sqlite:///adk_sessions.db`.

`agent.py` adds the repo root to `sys.path` because `adk` only adds `agents/`, and the agent needs to import
`retriever.py` and `llm_client.py`. The agent lives in `agents/` and not in the root so that the `adk web`
selector does not list `tests/` (which has an `__init__.py`) as if it were an agent.

## 4. Relation to the Corte 2 proposal

[PROPOSAL.md](../../PROPOSAL.md) proposes a **triage agent** that classifies the question and **solver agents** per
technique. This agent is the foundation of that design:

- `cubik_tutor` becomes the generic solver. The per-technique solvers would be copies with a narrower
  instruction and the same `search_knowledge_base` tool.
- The triage is added as `root_agent` with these agents in `sub_agents` (Week 8, multi-agent).
- `practice_log` and `get_progress_summary` give the triage information about which techniques the student
  practices and which ones they struggle with.
