"""Tests for the ADK agent tools in agents/cubik_tutor/agent.py.

The tools only touch tool_context.state (and retriever.query, which is
monkeypatched), so a plain object with a dict for state is enough and no model
or embedding provider is needed. The agent's real tool-calling loop is
verified manually with `adk web agents`.
"""

from types import SimpleNamespace

import pytest

from agents.cubik_tutor import agent


@pytest.fixture
def ctx() -> SimpleNamespace:
    """A stand-in for ADK's ToolContext with an empty session state."""
    return SimpleNamespace(state={})


def test_root_agent_is_adk_web_target() -> None:
    """Verify the module exposes root_agent with every tool registered."""
    tool_names = {tool.__name__ for tool in agent.root_agent.tools}
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
        {"text": "∫ u dv = uv - ∫ v du", "source": "techniques/integration_by_parts.md"},
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


def test_log_practice_attempt_updates_session_and_app_state(ctx: SimpleNamespace) -> None:
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
