# Week 13 — Observability for Cubik-Lite (Activity 4)

Langfuse tracing and structured tool-call logging for the ADK agents (`agents/cubik_team` and
`agents/cubik_tutor`).

| Piece | File | What it does |
|---|---|---|
| Tracing + tool logging | [`../observability.py`](../observability.py) | `setup_tracing()` starts the Langfuse client and OpenInference's blanket ADK instrumentation. `TOOL_LOGGING` is the pair of tool callbacks every agent gets. |
| Wiring | `agents/cubik_tutor/agent.py`, `agents/cubik_team/agent.py` | `setup_tracing()` runs before ADK is imported; `**TOOL_LOGGING` is spread into every `Agent(...)`. |
| 5-prompt run | [`run_prompts.py`](run_prompts.py) | Runs 5 varied prompts through the real team, one trace each. |
| Tests | [`../tests/test_observability.py`](../tests/test_observability.py) | Log format, trace-ID correlation, truncation, and that every agent has the callbacks. |

## Run it

```bash
pip install -r requirements.txt
# In .env: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL (see .env.example)
python week_13/run_prompts.py     # 5 traces, tagged week-13
adk web agents                    # or chat by hand: every turn is traced as well
```

Without the `LANGFUSE_*` keys the agents run exactly as before, untraced.

## Design decisions

**Blanket instrumentation, set up once.** `GoogleADKInstrumentor().instrument()` traces every invocation,
agent run, LLM call and tool call, so no call site can be forgotten. It needs `google-adk >= 2.10`: with an
older ADK it only logs a `DependencyConflict` and instruments nothing.

**Tool-layer logs carry the Langfuse trace ID.** An `after_tool_callback` writes one JSON line per tool call
with `trace_id`, `invocation_id`, `agent`, `tool`, `args` and a short `result`. The trace ID is the active
OpenTelemetry one, which is the ID Langfuse shows, so a log line leads straight to its trace. RAG results are
logged as their sources, not their text, and long results are cut at 500 characters. An
`on_tool_error_callback` logs failures and lets ADK raise them as before.

```json
{"event": "tool_called", "trace_id": "a1592e99f3d8ec36c7e4177687c007c9", "agent": "solver_agent",
 "tool": "solve_integral", "args": {"integrand": "x*exp(x)", "variable": "x"}, "result": {...}}
```

**One root observation per prompt in `run_prompts.py`.** It holds the prompt and the final answer, so the
Langfuse trace list shows them. A turn where the model returns no content is marked `level=ERROR`, so it is
found with `level:ERROR` instead of looking like an empty success.

## The 5 prompts

| Case | Prompt | Path it exercises |
|---|---|---|
| theory | ¿Por qué siempre sumamos la constante +C…? | coordinator → theory_agent → `search_knowledge_base` |
| solver | Resuelve la integral de x*e^x dx | coordinator → solver_agent → `solve_integral` + `search_knowledge_base` |
| verifier | La integral de cos(x) dx es -sin(x) + C, ¿está bien? | coordinator → verifier_agent → `check_student_antiderivative` |
| coordinator | Quiero explicaciones detalladas… y dime cuál es mi progreso | `set_explanation_level` + `progress_agent` (AgentTool) |
| out_of_scope | ¿Cuál es la capital de Francia? | declined, no tools |

## Findings from the traces (local qwen2.5:14b)

* **verifier**: the coordinator returns no content (`MODEL_RETURNED_NO_CONTENT`) and never hands off. It
  happens on `main` too, so it is the local model's routing, not the instrumentation; the week-12 evals ran on
  Gemini, where it routes correctly.
* **coordinator**: in one run the tool log showed `get_progress_summary` called with an argument the model made up
  (`{"tool_context": ...}`); ADK injects the real context, so it is harmless, but only the logs show it.
