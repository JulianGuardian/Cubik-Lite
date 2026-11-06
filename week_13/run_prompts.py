"""Week 13, Activity 4 -- run 5 varied prompts through the real cubik_team and trace them to Langfuse.

Each prompt runs in its own session, inside a root Langfuse observation that carries the prompt and the
final answer, so every one shows up in Langfuse as a separate `cubik_team_turn` trace (tagged `week-13`).
The tool-call logs written by observability.py carry the same trace ID, and so do the turn logs below.

The five prompts cover every path of the team: theory (RAG), solver (SymPy + RAG), verifier
(SymPy check + practice log), the coordinator's own tools (preference + progress_agent as AgentTool)
and an out-of-scope question that must be declined.

Needs LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_BASE_URL in the project's .env and the RAG
index built (python retriever.py). Run from the project root with: python week_13/run_prompts.py
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from observability import setup_tracing  # noqa: E402

if not setup_tracing():
    raise SystemExit("Set LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_BASE_URL in the project's .env.")

from agents.cubik_team.agent import root_agent  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402
from langfuse import get_client, propagate_attributes  # noqa: E402

PROMPTS = [
    ("theory", "¿Por qué siempre sumamos la constante +C al calcular una integral indefinida?"),
    ("solver", "Resuelve la integral de x*e^x dx"),
    ("verifier", "La integral de cos(x) dx es -sin(x) + C, ¿está bien?"),
    ("coordinator", "Quiero explicaciones detalladas de ahora en adelante, y dime cuál es mi progreso"),
    ("out_of_scope", "¿Cuál es la capital de Francia?"),
]
USER_ID = "week13_student"

logging.basicConfig(level=logging.INFO, format="%(message)s")
for noisy in ("LiteLLM", "httpx", "httpcore", "google_adk", "google_genai"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
logger = logging.getLogger("cubik.turns")


def log_event(event: str, **fields) -> None:
    langfuse = get_client()
    logger.info(json.dumps({"event": event, "trace_id": langfuse.get_current_trace_id(), **fields},
                           ensure_ascii=False))


async def run_prompt(runner: InMemoryRunner, label: str, prompt: str) -> str | None:
    """Run one prompt in a fresh session; return its Langfuse trace ID."""
    langfuse = get_client()
    session = await runner.session_service.create_session(app_name=runner.app_name, user_id=USER_ID)
    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    with propagate_attributes(trace_name="cubik_team_turn", session_id=session.id, user_id=USER_ID,
                              tags=["week-13", label]):
        with langfuse.start_as_current_observation(name="cubik_team_turn", as_type="agent",
                                                   input=prompt) as turn:
            trace_id = langfuse.get_current_trace_id()
            log_event("turn_started", case=label, prompt=prompt)
            answer, error = "", None
            async for event in runner.run_async(user_id=USER_ID, session_id=session.id, new_message=message):
                if event.error_code:  # e.g. MODEL_RETURNED_NO_CONTENT: the model answered with nothing
                    error = f"{event.error_code}: {event.error_message}"
                if event.is_final_response() and event.content and event.content.parts:
                    answer = "".join(part.text or "" for part in event.content.parts)
            if error and not answer:
                # Mark the trace so it shows up under level:ERROR in Langfuse instead of as an empty success.
                turn.update(output=None, level="ERROR", status_message=error)
                log_event("turn_failed", case=label, error=error)
            else:
                turn.update(output=answer)
                log_event("turn_completed", case=label, answer_preview=answer[:150])
    return trace_id


async def main() -> None:
    runner = InMemoryRunner(agent=root_agent, app_name="cubik_team")
    trace_ids = []
    for label, prompt in PROMPTS:
        print(f"\n===== [{label}] {prompt}", flush=True)
        trace_ids.append((label, await run_prompt(runner, label, prompt)))

    langfuse = get_client()
    langfuse.flush()  # send every buffered span before exiting
    print("\n===== Traces sent to Langfuse =====")
    for label, trace_id in trace_ids:
        try:
            url = langfuse.get_trace_url(trace_id=trace_id)
        except Exception:  # noqa: BLE001  (the URL needs an API call; the ID alone is enough to search)
            url = None
        print(f"{label:<13} {trace_id}  {url or ''}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
