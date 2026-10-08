"""Tests for the ADK agent tools in agents/cubik_tutor/agent.py.

The tools only touch tool_context.state (and retriever.query, which is
monkeypatched), so a plain object with a dict for state is enough and no model
or embedding provider is needed. The agent's real tool-calling loop is
verified manually with `adk web agents`.
"""

import asyncio
from types import SimpleNamespace

import pytest
from agents.cubik_tutor import agent


@pytest.fixture
def ctx() -> SimpleNamespace:
    """A stand-in for ADK's ToolContext with an empty session state."""
    return SimpleNamespace(state={})


def test_root_agent_is_adk_web_target() -> None:
    """Verify the module exposes root_agent with every tool registered."""
    tool_names = {
        getattr(tool, "name", None) or tool.__name__ for tool in agent.root_agent.tools
    }
    assert agent.root_agent.name == "cubik_tutor"
    assert tool_names == {
        "search_knowledge_base",
        "set_explanation_level",
        "log_practice_attempt",
        "get_progress_summary",
        "reset_practice_log",
    }


def test_search_knowledge_base_stores_sources_in_temp_state(
    ctx: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify retrieval goes through retriever.query and sources land in temp: state."""
    chunks = [
        {
            "text": "∫ u dv = uv - ∫ v du",
            "source": "techniques/integration_by_parts.md",
        },
        {"text": "LIATE", "source": "techniques/integration_by_parts.md"},
        {"text": "∫ e^x dx = e^x + C", "source": "indefinite_integrals/basic_rules.md"},
    ]
    monkeypatch.setattr(agent.retriever, "query", lambda question: chunks)

    result = agent.search_knowledge_base("¿Integral de x·e^x?", ctx)

    assert result == {"chunks": chunks}
    assert ctx.state == {
        "temp:last_sources": [
            "indefinite_integrals/basic_rules.md",
            "techniques/integration_by_parts.md",
        ]
    }


def test_set_explanation_level_is_user_scoped(ctx: SimpleNamespace) -> None:
    """Verify a valid level is normalized and saved under the user: prefix."""
    result = agent.set_explanation_level("  Detallado ", ctx)

    assert result == {"explanation_level": "detallado"}
    assert ctx.state == {"user:explanation_level": "detallado"}


def test_set_explanation_level_rejects_unknown_level(ctx: SimpleNamespace) -> None:
    """Verify an unknown level returns an error and leaves state untouched."""
    result = agent.set_explanation_level("avanzado", ctx)

    assert "error" in result
    assert ctx.state == {}


def test_log_practice_attempt_updates_session_and_app_state(
    ctx: SimpleNamespace,
) -> None:
    """Verify each attempt is appended to the session log and counted app-wide."""
    ctx.state["app:total_attempts_all_users"] = 41

    agent.log_practice_attempt("Integration by parts", True, ctx)
    result = agent.log_practice_attempt("substitution", False, ctx)

    assert result == {"session_attempts": 2, "total_attempts_all_users": 43}
    assert ctx.state["practice_log"] == [
        {"technique": "integration by parts", "solved": True},
        {"technique": "substitution", "solved": False},
    ]


def test_get_progress_summary_groups_by_technique(ctx: SimpleNamespace) -> None:
    """Verify the summary counts attempts and solved exercises per technique."""
    ctx.state["user:explanation_level"] = "basico"
    agent.log_practice_attempt("substitution", True, ctx)
    agent.log_practice_attempt("substitution", False, ctx)
    agent.log_practice_attempt("partial fractions", True, ctx)

    assert agent.get_progress_summary(ctx) == {
        "by_technique": {
            "substitution": {"attempts": 2, "solved": 1},
            "partial fractions": {"attempts": 1, "solved": 1},
        },
        "explanation_level": "basico",
        "total_attempts_all_users": 3,
    }


def test_reset_practice_log_keeps_user_and_app_state(ctx: SimpleNamespace) -> None:
    """Verify resetting the session log does not touch user: or app: state."""
    agent.set_explanation_level("detallado", ctx)
    agent.log_practice_attempt("substitution", True, ctx)
    agent.log_practice_attempt("substitution", True, ctx)

    result = agent.reset_practice_log(ctx)

    assert result == {"cleared_attempts": 2}
    assert ctx.state["practice_log"] == []
    assert ctx.state["user:explanation_level"] == "detallado"
    assert ctx.state["app:total_attempts_all_users"] == 2


def test_reset_practice_log_is_guarded_by_a_confirmation_tool() -> None:
    """Verify the root agent holds the confirmation-guarded wrapper, not the bare function."""
    assert agent.reset_practice_log_tool.func is agent.reset_practice_log
    assert agent.reset_practice_log_tool in agent.root_agent.tools
    assert agent.reset_practice_log not in agent.root_agent.tools


def test_has_practice_attempts_only_when_the_log_has_entries(
    ctx: SimpleNamespace,
) -> None:
    """Verify the confirmation condition is False for a missing or empty log."""
    assert agent.has_practice_attempts(ctx) is False

    ctx.state["practice_log"] = []
    assert agent.has_practice_attempts(ctx) is False

    agent.log_practice_attempt("substitution", True, ctx)
    assert agent.has_practice_attempts(ctx) is True


class ConfirmationContext(SimpleNamespace):
    """A stand-in for ToolContext that records the approvals ADK asks for."""

    def __init__(self, state: dict, tool_confirmation=None) -> None:
        super().__init__(
            state=state,
            tool_confirmation=tool_confirmation,
            actions=SimpleNamespace(skip_summarization=False),
            approvals_requested=[],
        )

    def request_confirmation(self, **kwargs) -> None:
        self.approvals_requested.append(kwargs)


def run_reset_tool(context: ConfirmationContext) -> dict:
    """Run the guarded reset tool the way ADK does."""
    return asyncio.run(
        agent.reset_practice_log_tool.run_async(args={}, tool_context=context)
    )


def logged_state() -> dict:
    """A session state with one logged attempt."""
    return {"practice_log": [{"technique": "substitution", "solved": True}]}


def test_reset_asks_for_approval_and_keeps_the_log_until_answered() -> None:
    """Verify a reset with attempts logged does not run before the student answers."""
    context = ConfirmationContext(logged_state())

    result = run_reset_tool(context)

    assert "requires confirmation" in result["error"]
    assert len(context.approvals_requested) == 1
    assert context.state["practice_log"] == logged_state()["practice_log"]


def test_reset_runs_when_the_student_approves() -> None:
    """Verify an approved reset clears the log."""
    context = ConfirmationContext(
        logged_state(), tool_confirmation=SimpleNamespace(confirmed=True)
    )

    assert run_reset_tool(context) == {"cleared_attempts": 1}
    assert context.state["practice_log"] == []


def test_reset_does_not_run_when_the_student_rejects() -> None:
    """Verify a rejected reset leaves the log intact."""
    context = ConfirmationContext(
        logged_state(), tool_confirmation=SimpleNamespace(confirmed=False)
    )

    assert "rejected" in run_reset_tool(context)["error"]
    assert context.state["practice_log"] == logged_state()["practice_log"]


def test_reset_with_nothing_to_lose_skips_the_approval() -> None:
    """Verify an empty log is reset without asking."""
    context = ConfirmationContext({})

    assert run_reset_tool(context) == {"cleared_attempts": 0}
    assert context.approvals_requested == []


def test_reset_approval_request_is_in_spanish_and_counts_the_attempts() -> None:
    """Verify the student sees ADK's approval request in Spanish, not the default English hint."""
    one = ConfirmationContext(logged_state())
    two = ConfirmationContext(
        {"practice_log": logged_state()["practice_log"] * 2}
    )

    run_reset_tool(one)
    run_reset_tool(two)

    hint_one = one.approvals_requested[0]["hint"]
    hint_two = two.approvals_requested[0]["hint"]
    assert "Se borrarán 1 intento de tu registro" in hint_one
    assert "Se borrarán 2 intentos de tu registro" in hint_two
    assert "Confirmed" in hint_one and "yes" in hint_one
    assert "Please approve or reject" not in hint_one


def test_reset_hint_is_only_requested_once_per_pending_approval() -> None:
    """Verify an answered approval goes through ADK's own path and does not ask again."""
    context = ConfirmationContext(
        logged_state(), tool_confirmation=SimpleNamespace(confirmed=True)
    )

    run_reset_tool(context)

    assert context.approvals_requested == []
