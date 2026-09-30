"""Google ADK version of the Cubik-Lite Integral Calculus Tutor.

Same tutor as main.py (same system prompt, same RAG over data/, same
Gemini/Ollama provider switch from llm_client.py), but run as an ADK agent:
retrieval is a tool the model calls instead of a block main.py prepends, and
conversation history lives in ADK's SessionService instead of
SlidingWindowManager.

State scopes used by the tools (see docs/adk_agent.md):
- temp:last_sources        -> only for the current turn.
- practice_log             -> this session (conversation) only.
- user:explanation_level   -> this student, across all of their sessions.
- app:total_attempts_all_users -> shared by every student of the app.

Run from the repo root with `adk web agents` or `adk run agents/cubik_tutor`.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
# adk only puts agents/ on sys.path; the tutor modules live at the repo root.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from google.adk.agents import Agent  # noqa: E402
from google.adk.models.lite_llm import LiteLlm  # noqa: E402
from google.adk.tools import ToolContext  # noqa: E402

import retriever  # noqa: E402
from llm_client import CHAT_MODEL, USING_GEMINI  # noqa: E402

EXPLANATION_LEVELS = ("basico", "detallado")

# Gemini goes through ADK's native integration (it reads GEMINI_API_KEY, which
# llm_client already loaded from .env); the Ollama fallback goes through LiteLlm.
MODEL = CHAT_MODEL.removeprefix("gemini/") if USING_GEMINI else LiteLlm(model=CHAT_MODEL)

SYSTEM_PROMPT = (REPO_ROOT / "prompts" / "system_prompt.txt").read_text(
    encoding="utf-8"
)

ADK_INSTRUCTIONS = """
TOOLS (ADK)
- Before answering any integral calculus question, call search_knowledge_base with the student's question. Its
  "chunks" play the role of the "Contexto recuperado" block described in GROUNDING: answer only from them and
  cite their "source" values in the "source" field.
- When the student states how much detail they want ("explicame con mas detalle", "solo lo basico"), call
  set_explanation_level with "basico" or "detallado".
- After working through an exercise with the student, call log_practice_attempt with the technique used and
  whether the student solved it.
- When the student asks how they are doing, call get_progress_summary. When they ask to start their practice
  over, call reset_practice_log.
- Out-of-scope questions are refused as described in REFUSAL BEHAVIOR, without calling search_knowledge_base.

STUDENT PREFERENCES
Preferred explanation level: {user:explanation_level?}
If it is "basico", keep "steps" short (a few key steps). If it is "detallado", justify every step. If it is
empty, use a moderate level of detail.

Your final message must still be only the JSON object described in OUTPUT STYLE.
"""


def search_knowledge_base(question: str, tool_context: ToolContext) -> dict:
    """Search the integral calculus knowledge base for passages relevant to a question.

    Args:
        question: The student's question, or the specific concept to look up.
        tool_context: Injected by ADK; gives access to session state.

    Returns:
        A dict with the retrieved "chunks" (each with "text" and "source").
    """
    chunks = retriever.query(question)
    # Only this turn needs the sources, so they must not leak into later turns.
    tool_context.state["temp:last_sources"] = sorted({c["source"] for c in chunks})
    return {"chunks": chunks}


def set_explanation_level(level: str, tool_context: ToolContext) -> dict:
    """Save how detailed the student wants explanations to be: 'basico' or 'detallado'.

    Args:
        level: Either "basico" or "detallado".
        tool_context: Injected by ADK; gives access to session state.

    Returns:
        A dict confirming the saved level, or an error for an unknown level.
    """
    level = level.lower().strip()
    if level not in EXPLANATION_LEVELS:
        return {
            "error": f"Nivel desconocido {level!r}. Usa uno de: {', '.join(EXPLANATION_LEVELS)}."
        }
    tool_context.state["user:explanation_level"] = level
    return {"explanation_level": level}


def log_practice_attempt(technique: str, solved: bool, tool_context: ToolContext) -> dict:
    """Record an exercise the student just worked on in this session.

    Args:
        technique: The integration technique the exercise practiced (e.g. "integration by parts").
        solved: Whether the student reached the correct result.
        tool_context: Injected by ADK; gives access to session state.

    Returns:
        A dict with the number of attempts logged in this session and across all students.
    """
    entry = {"technique": technique.lower().strip(), "solved": solved}
    # Reassign instead of appending in place so ADK records the state change.
    log = tool_context.state.get("practice_log", []) + [entry]
    tool_context.state["practice_log"] = log

    total = tool_context.state.get("app:total_attempts_all_users", 0) + 1
    tool_context.state["app:total_attempts_all_users"] = total
    return {"session_attempts": len(log), "total_attempts_all_users": total}


def get_progress_summary(tool_context: ToolContext) -> dict:
    """Summarize the student's practice in this session, per technique.

    Args:
        tool_context: Injected by ADK; gives access to session state.

    Returns:
        A dict with per-technique attempt/solved counts, the preferred
        explanation level, and the app-wide attempt count.
    """
    by_technique: dict[str, dict[str, int]] = {}
    for entry in tool_context.state.get("practice_log", []):
        stats = by_technique.setdefault(entry["technique"], {"attempts": 0, "solved": 0})
        stats["attempts"] += 1
        stats["solved"] += int(entry["solved"])

    return {
        "by_technique": by_technique,
        "explanation_level": tool_context.state.get("user:explanation_level"),
        "total_attempts_all_users": tool_context.state.get("app:total_attempts_all_users", 0),
    }


def reset_practice_log(tool_context: ToolContext) -> dict:
    """Clear this session's practice log, keeping the student's saved preferences.

    Args:
        tool_context: Injected by ADK; gives access to session state.

    Returns:
        A dict with how many logged attempts were cleared.
    """
    cleared = len(tool_context.state.get("practice_log", []))
    tool_context.state["practice_log"] = []
    return {"cleared_attempts": cleared}


root_agent = Agent(
    name="cubik_tutor",
    model=MODEL,
    description=(
        "Integral calculus tutor that answers theory questions and guides exercises step by step, "
        "grounded in the course knowledge base."
    ),
    instruction=SYSTEM_PROMPT + ADK_INSTRUCTIONS,
    tools=[
        search_knowledge_base,
        set_explanation_level,
        log_practice_attempt,
        get_progress_summary,
        reset_practice_log,
    ],
)
