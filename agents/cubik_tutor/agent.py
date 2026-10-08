"""Google ADK version of the Cubik-Lite Integral Calculus Tutor.

Same tutor as main.py (same system prompt, same RAG over data/, same
Gemini/Ollama provider switch from llm_client.py), but run as an ADK agent:
retrieval is a tool the model calls instead of a block main.py prepends, and
conversation history lives in ADK's SessionService instead of
SlidingWindowManager.

State scopes used by the tools (see docs/en/adk_agent.md):
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

import retriever
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import ToolContext
from google.adk.tools.function_tool import FunctionTool
from llm_client import CHAT_MODEL, USING_GEMINI

EXPLANATION_LEVELS = ("basico", "detallado")

# Gemini goes through ADK's native integration (it reads GEMINI_API_KEY, which
# llm_client already loaded from .env); the Ollama fallback goes through LiteLlm.
MODEL = (
    CHAT_MODEL.removeprefix("gemini/") if USING_GEMINI else LiteLlm(model=CHAT_MODEL)
)

SYSTEM_PROMPT = (REPO_ROOT / "prompts" / "system_prompt.txt").read_text(
    encoding="utf-8"
)

ADK_INSTRUCTIONS = """
TOOLS (ADK)
- Before answering any integral calculus question, call search_knowledge_base with the student's question. Its
  "chunks" play the role of the "Contexto recuperado" block described in GROUNDING: answer only from them and
  cite their "source" values in the "source" field. If the message is a bare exercise (e.g. "∫ x·e^x dx"),
  search for the technique or rule that applies, as a short Spanish phrase ("integración por partes"), instead
  of the raw expression.
- When the student states how much detail they want ("explicame con mas detalle", "solo lo basico"), call
  set_explanation_level with "basico" or "detallado".
- After working through an exercise with the student, call log_practice_attempt with the technique used and
  whether the student solved it.
- When the student asks how they are doing, call get_progress_summary. When they ask to start their practice
  over, call reset_practice_log right away. Do not ask them to confirm in your own message: the system asks
  them to approve before the tool runs. If the tool reports it was rejected, tell them their log was kept.
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
            "error": f"Unknown level {level!r}. Use one of: {', '.join(EXPLANATION_LEVELS)}."
        }
    tool_context.state["user:explanation_level"] = level
    return {"explanation_level": level}


def log_practice_attempt(
    technique: str, solved: bool, tool_context: ToolContext
) -> dict:
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
        stats = by_technique.setdefault(
            entry["technique"], {"attempts": 0, "solved": 0}
        )
        stats["attempts"] += 1
        stats["solved"] += int(entry["solved"])

    return {
        "by_technique": by_technique,
        "explanation_level": tool_context.state.get("user:explanation_level"),
        "total_attempts_all_users": tool_context.state.get(
            "app:total_attempts_all_users", 0
        ),
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


def has_practice_attempts(tool_context: ToolContext) -> bool:
    """Whether this session's practice log has anything a reset would erase.

    It is reset_practice_log's require_confirmation condition. ADK calls it with
    the tool's own arguments, so its parameter must be named tool_context too.

    Args:
        tool_context: Injected by ADK; gives access to session state.

    Returns:
        True if at least one attempt is logged.
    """
    return bool(tool_context.state.get("practice_log"))


def reset_confirmation_hint(tool_context: ToolContext) -> str:
    """The text the student sees when asked to approve a practice reset (in Spanish).

    Args:
        tool_context: Injected by ADK; gives access to session state.

    Returns:
        A message that says how many attempts would be erased and how to answer.
    """
    attempts = len(tool_context.state.get("practice_log", []))
    noun = "intento" if attempts == 1 else "intentos"
    return (
        f"Se borrarán {attempts} {noun} de tu registro de práctica y no se puede deshacer. "
        "Para aprobar, marca «Confirmed» y pulsa «Submit» en la web, o escribe yes en la terminal. "
        "Cualquier otra respuesta cancela el reinicio."
    )


class SpanishConfirmationTool(FunctionTool):
    """A FunctionTool that asks for approval with its own message instead of ADK's English one.

    ADK hardcodes the approval request's hint in FunctionTool.run_async, with no
    option to change it. This only replaces the first step, the request itself;
    the approved, rejected and run steps are still ADK's (super().run_async).
    """

    def __init__(self, func, *, require_confirmation, hint) -> None:
        super().__init__(func, require_confirmation=require_confirmation)
        self._hint = hint

    async def run_async(self, *, args, tool_context):
        if not tool_context.tool_confirmation and await self.check_require_confirmation(
            args, tool_context
        ):
            tool_context.request_confirmation(hint=self._hint(tool_context))
            tool_context.actions.skip_summarization = True
            return {
                "error": "This tool call requires confirmation, please approve or reject."
            }
        return await super().run_async(args=args, tool_context=tool_context)


# Resetting erases the student's progress with no undo, so ADK pauses the run and
# asks the student to approve it first (only when there is something to lose).
# cubik_team gives this same tool to its coordinator rather than to progress_agent:
# an AgentTool runs a nested Runner whose events never reach the student, so an
# approval requested inside it could not be answered.
reset_practice_log_tool = SpanishConfirmationTool(
    reset_practice_log,
    require_confirmation=has_practice_attempts,
    hint=reset_confirmation_hint,
)


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
        reset_practice_log_tool,
    ],
)
