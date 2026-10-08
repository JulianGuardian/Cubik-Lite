"""Tests for the multi-agent tree in agents/cubik_team/agent.py.

They check the team's wiring against docs/en/multi_agent_design.md (who is a
sub-agent, who is an AgentTool, which tools each agent gets) and the verifier's
check-and-log tools, without calling a model. The routing itself depends on the
model and is verified manually with `adk web agents`.
"""

from types import SimpleNamespace

import pytest
from agents.cubik_team import agent as team
from agents.cubik_tutor import agent as tutor
from google.adk.agents._agent_router import (
    find_agent_to_run,
    is_transferable_across_agent_tree,
)
from google.adk.events import Event
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.function_tool import FunctionTool

SPECIALISTS = [team.theory_agent, team.solver_agent, team.verifier_agent]


def tool_names(agent) -> set[str]:
    """Names of an agent's tools, whether plain functions or ADK tool wrappers."""
    return {getattr(tool, "name", None) or tool.__name__ for tool in agent.tools}


def test_root_agent_is_the_coordinator_with_three_handoff_specialists() -> None:
    """Verify theory, solver and verifier are sub_agents of the coordinator."""
    assert team.root_agent.name == "cubik_coordinator"
    assert [a.name for a in team.root_agent.sub_agents] == [
        "theory_agent",
        "solver_agent",
        "verifier_agent",
    ]


def test_progress_agent_is_an_agent_tool_of_the_coordinator() -> None:
    """Verify progress_agent is called as a tool, not handed the conversation."""
    agent_tools = [t for t in team.root_agent.tools if isinstance(t, AgentTool)]

    assert [t.agent for t in agent_tools] == [team.progress_agent]
    assert team.progress_agent not in team.root_agent.sub_agents
    assert tool_names(team.root_agent) == {
        "set_explanation_level",
        "reset_practice_log",
        "progress_agent",
    }


@pytest.mark.parametrize(
    ("agent", "expected"),
    [
        (team.theory_agent, {"search_knowledge_base"}),
        (
            team.solver_agent,
            {
                "search_knowledge_base",
                "solve_integral",
                "check_antiderivative",
                "check_definite_integral",
                "log_practice_attempt",
            },
        ),
        (
            team.verifier_agent,
            {
                "check_student_antiderivative",
                "check_student_definite_integral",
                "search_knowledge_base",
            },
        ),
        (team.progress_agent, {"get_progress_summary"}),
    ],
)
def test_each_agent_gets_only_its_tools(agent, expected: set[str]) -> None:
    """Verify every agent has exactly the tools assigned in the design."""
    assert tool_names(agent) == expected


def test_verifier_cannot_solve_integrals_or_log_by_hand() -> None:
    """Verify the verifier only judges through the check tools, which log on their own."""
    names = tool_names(team.verifier_agent)

    assert "solve_integral" not in names
    assert "log_practice_attempt" not in names


@pytest.mark.parametrize(
    ("candidate", "solved"),
    [("x^3/3 + C", True), ("x^3/2 + C", False)],
)
def test_check_student_antiderivative_logs_the_sympy_verdict(
    candidate: str, solved: bool
) -> None:
    """Verify the attempt is logged with solved taken from SymPy, not from the model."""
    ctx = SimpleNamespace(state={})

    result = team.check_student_antiderivative("x**2", candidate, "power rule", ctx)

    assert result["logged"] is True
    assert ctx.state["practice_log"] == [{"technique": "power rule", "solved": solved}]


def test_check_student_definite_integral_logs_the_sympy_verdict() -> None:
    """Verify a definite-integral check is logged the same way."""
    ctx = SimpleNamespace(state={})

    result = team.check_student_definite_integral(
        "sin(x)", "0", "pi", "2", "basic rules", ctx
    )

    assert result["verdict"] == "correct"
    assert ctx.state["practice_log"] == [{"technique": "basic rules", "solved": True}]


def test_check_student_tools_do_not_log_errors_or_unconfirmed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify bad input and unconfirmed verdicts leave the practice log untouched."""
    ctx = SimpleNamespace(state={})

    bad_input = team.check_student_antiderivative("x", "x^^2 +", "power rule", ctx)
    monkeypatch.setattr(
        team, "check_antiderivative", lambda *args: {"verdict": "unconfirmed"}
    )
    unconfirmed = team.check_student_antiderivative("x", "x^2/2", "power rule", ctx)

    assert bad_input["logged"] is False
    assert unconfirmed["logged"] is False
    assert ctx.state == {}


def test_prompts_are_loaded_from_files() -> None:
    """Verify every student-facing agent gets the shared rules plus its own role file."""
    shared = team.load_prompt("shared")

    for agent, role in [
        (team.root_agent, "coordinator"),
        (team.theory_agent, "theory"),
        (team.solver_agent, "solver"),
        (team.verifier_agent, "verifier"),
    ]:
        assert agent.instruction.startswith(shared)
        assert agent.instruction.endswith(team.load_prompt(role))
    assert team.progress_agent.instruction == team.load_prompt("progress")


def test_shared_tools_are_reused_from_cubik_tutor() -> None:
    """Verify the state and RAG tools are cubik_tutor's functions, not copies."""
    shared = {}
    for agent in [team.root_agent, *SPECIALISTS, team.progress_agent]:
        for tool in agent.tools:
            if isinstance(tool, AgentTool):
                continue
            function = tool.func if isinstance(tool, FunctionTool) else tool
            if hasattr(tutor, function.__name__):
                shared[function.__name__] = function

    assert set(shared) == {
        "search_knowledge_base",
        "set_explanation_level",
        "log_practice_attempt",
        "get_progress_summary",
        "reset_practice_log",
    }
    for name, function in shared.items():
        assert function is getattr(tutor, name)


def test_coordinator_holds_the_guarded_reset_tool_directly() -> None:
    """Verify the coordinator uses cubik_tutor's confirmation-guarded reset, not a copy."""
    assert tutor.reset_practice_log_tool in team.root_agent.tools


def test_no_confirmation_tool_is_hidden_inside_an_agent_tool() -> None:
    """Verify approvals can reach the student: an AgentTool's nested run never forwards them.

    A tool that needs approval inside progress_agent would be blocked for good,
    since the student would never see the request.
    """
    for tool in team.root_agent.tools:
        if isinstance(tool, AgentTool):
            for inner in tool.agent.tools:
                assert not getattr(inner, "_require_confirmation", False)


@pytest.mark.parametrize("specialist", SPECIALISTS, ids=lambda a: a.name)
def test_specialists_cannot_transfer(specialist) -> None:
    """Verify specialists can't transfer, so they never keep the conversation."""
    assert specialist.disallow_transfer_to_parent
    assert specialist.disallow_transfer_to_peers
    assert not is_transferable_across_agent_tree(specialist)


def test_next_message_returns_to_the_coordinator() -> None:
    """Verify ADK routes the student's next message to the coordinator, not the last specialist."""
    for specialist in SPECIALISTS:
        last_reply = Event(author=specialist.name, invocation_id="i")
        session = SimpleNamespace(events=[last_reply])

        assert find_agent_to_run(session, team.root_agent) is team.root_agent


def test_coordinator_instruction_names_every_route() -> None:
    """Verify the coordinator is told when to use each specialist and progress_agent."""
    for name in ["theory_agent", "solver_agent", "verifier_agent", "progress_agent"]:
        assert name in team.root_agent.instruction


@pytest.mark.parametrize("specialist", SPECIALISTS, ids=lambda a: a.name)
def test_specialist_descriptions_state_what_they_do_not_handle(specialist) -> None:
    """Verify each description marks its boundary, since peers route on it."""
    assert "Does not" in specialist.description
