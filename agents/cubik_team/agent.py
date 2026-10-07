"""Multi-agent (Corte 2) version of the Cubik-Lite Integral Calculus Tutor.

A coordinator routes each student message to one of three specialists through
sub_agents handoffs (theory, solver, verifier) and calls a fourth one,
progress_agent, as an AgentTool. The specialists can't transfer, so every new
message comes back to the coordinator. Results and verdicts come from the SymPy
tools in math_tools.py, not from the model. See docs/en/multi_agent_design.md.

Instructions live in prompts/team/: shared.txt (a compact version of
prompts/system_prompt.txt for the agents that talk to the student) plus one
role file per agent. The model and the state/RAG tools are the ones from
agents/cubik_tutor/, imported instead of duplicated. That agent is left as is,
so both show up in `adk web agents` and can be compared.

Run from the repo root with `adk web agents` (pick cubik_team).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
# adk only puts agents/ on sys.path; the tutor modules live at the repo root.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.cubik_tutor.agent import (
    MODEL,
    get_progress_summary,
    log_practice_attempt,
    reset_practice_log,
    search_knowledge_base,
    set_explanation_level,
)
from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool
from google.genai import types
from math_tools import check_antiderivative, check_definite_integral, solve_integral

PROMPTS_DIR = REPO_ROOT / "prompts" / "team"

# A specialist that can't transfer isn't "transferable across the agent tree",
# so ADK sends the student's next message to the root (the coordinator) instead
# of the specialist that answered last. Routing then lives in one agent, rather
# than relying on each specialist to notice a topic switch and transfer, which
# the local model often got wrong (see docs/en/multi_agent_design.md, section 5).
NO_TRANSFERS = {"disallow_transfer_to_parent": True, "disallow_transfer_to_peers": True}

# Low temperature for every agent in the team: routing, tool arguments and the
# JSON format need to be consistent, and the local model drifted into other
# languages at the default temperature.
GENERATION_CONFIG = types.GenerateContentConfig(temperature=0.2)


def load_prompt(name: str) -> str:
    """Read prompts/team/<name>.txt."""
    return (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")


def student_facing_instruction(role: str) -> str:
    """Shared tutor rules and output format, followed by the agent's role file."""
    return load_prompt("shared") + "\n" + load_prompt(role)


def _record_check(result: dict, technique: str, tool_context: ToolContext) -> dict:
    """Log a checked attempt, unless the input was invalid or SymPy couldn't decide.

    An "unconfirmed" verdict is not logged: counting it as failed would mark a
    possibly correct answer as wrong in the student's progress.
    """
    logged = result.get("verdict") in {"correct", "incorrect"}
    if logged:
        log_practice_attempt(technique, result["verdict"] == "correct", tool_context)
    return {**result, "logged": logged}


def check_student_antiderivative(
    integrand: str,
    candidate: str,
    technique: str,
    tool_context: ToolContext,
    variable: str = "x",
) -> dict:
    """Check the student's antiderivative with SymPy and record the attempt in their practice log.

    Args:
        integrand: The function that was integrated, in SymPy syntax, e.g. "x*exp(x)".
        candidate: The student's answer, in SymPy syntax, e.g. "x*exp(x) - exp(x) + C".
        technique: The integration technique the exercise practices, e.g. "integration by parts".
        tool_context: Injected by ADK; gives access to session state.
        variable: The integration variable.

    Returns:
        check_antiderivative's result (the "verdict" and interpreted expressions)
        plus "logged", whether the attempt was recorded.
    """
    result = check_antiderivative(integrand, candidate, variable)
    return _record_check(result, technique, tool_context)


def check_student_definite_integral(
    integrand: str,
    lower: str,
    upper: str,
    candidate: str,
    technique: str,
    tool_context: ToolContext,
    variable: str = "x",
) -> dict:
    """Check the student's value for a definite integral with SymPy and record the attempt in their practice log.

    Args:
        integrand: The function that was integrated, in SymPy syntax, e.g. "sin(x)".
        lower: Lower limit, e.g. "0".
        upper: Upper limit, e.g. "pi".
        candidate: The student's value, e.g. "2".
        technique: The integration technique the exercise practices, e.g. "substitution".
        tool_context: Injected by ADK; gives access to session state.
        variable: The integration variable.

    Returns:
        check_definite_integral's result (the "verdict" and exact value) plus
        "logged", whether the attempt was recorded.
    """
    result = check_definite_integral(integrand, lower, upper, candidate, variable)
    return _record_check(result, technique, tool_context)


theory_agent = Agent(
    name="theory_agent",
    model=MODEL,
    generate_content_config=GENERATION_CONFIG,
    description=(
        "Explains integral calculus concepts, definitions and theorems (e.g. why +C, the Fundamental "
        "Theorem), citing the knowledge base. Does not solve or check specific exercises."
    ),
    instruction=student_facing_instruction("theory"),
    tools=[search_knowledge_base],
    **NO_TRANSFERS,
)

solver_agent = Agent(
    name="solver_agent",
    model=MODEL,
    generate_content_config=GENERATION_CONFIG,
    description=(
        "Solves a specific integral the student asks to be solved, step by step, naming the technique "
        "and the rule behind each step. Does not answer theory questions or check the student's own "
        "answers."
    ),
    instruction=student_facing_instruction("solver"),
    tools=[
        solve_integral,
        search_knowledge_base,
        check_antiderivative,
        check_definite_integral,
        log_practice_attempt,
    ],
    **NO_TRANSFERS,
)

verifier_agent = Agent(
    name="verifier_agent",
    model=MODEL,
    generate_content_config=GENERATION_CONFIG,
    description=(
        "Checks the student's own answer to a specific integral against an exact SymPy computation, "
        "and explains the mistake if it is wrong. Does not solve exercises the student has not "
        "attempted."
    ),
    instruction=student_facing_instruction("verifier"),
    tools=[
        check_student_antiderivative,
        check_student_definite_integral,
        search_knowledge_base,
    ],
    **NO_TRANSFERS,
)

progress_agent = Agent(
    name="progress_agent",
    model=MODEL,
    generate_content_config=GENERATION_CONFIG,
    description=(
        "Summarizes the student's practice progress per technique, or resets their practice log."
    ),
    instruction=load_prompt("progress"),
    tools=[get_progress_summary, reset_practice_log],
)

root_agent = Agent(
    name="cubik_coordinator",
    model=MODEL,
    generate_content_config=GENERATION_CONFIG,
    description=(
        "Entry point of the integral calculus tutor: classifies each student message and routes it to "
        "the right specialist."
    ),
    instruction=student_facing_instruction("coordinator"),
    sub_agents=[theory_agent, solver_agent, verifier_agent],
    tools=[set_explanation_level, AgentTool(agent=progress_agent)],
)
