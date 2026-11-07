"""Tests for observability.py: the tool-call log lines and their wiring into the ADK agents.

They don't call a model or Langfuse. Whether the traces reach Langfuse is checked by
running week_13/run_prompts.py against a real Langfuse project.
"""

import json
import logging
from types import SimpleNamespace

import observability
import pytest
from agents.cubik_team import agent as team
from agents.cubik_tutor import agent as tutor
from opentelemetry.sdk.trace import TracerProvider

TOOL = SimpleNamespace(name="search_knowledge_base")
CONTEXT = SimpleNamespace(invocation_id="inv-1", agent_name="theory_agent")


def logged_lines(caplog) -> list[dict]:
    """The JSON payloads written to the cubik.tools logger."""
    return [json.loads(r.getMessage()) for r in caplog.records if r.name == "cubik.tools"]


def test_tool_call_log_is_json_with_agent_tool_args_and_trace_id(caplog) -> None:
    """Verify a tool call is logged as one JSON line carrying the active trace ID."""
    tracer = TracerProvider().get_tracer("test")
    with caplog.at_level(logging.INFO, logger="cubik.tools"), tracer.start_as_current_span("tool") as span:
        result = observability.log_tool_call(TOOL, {"question": "+C"}, CONTEXT, {"answer": 1})

    [line] = logged_lines(caplog)
    assert result is None  # the callback must not replace the tool's result
    assert line == {
        "event": "tool_called",
        "trace_id": format(span.get_span_context().trace_id, "032x"),
        "invocation_id": "inv-1",
        "agent": "theory_agent",
        "tool": "search_knowledge_base",
        "args": {"question": "+C"},
        "result": {"answer": 1},
    }


def test_trace_id_is_none_outside_a_trace(caplog) -> None:
    """Verify the log still works, with a null trace ID, when nothing is being traced."""
    with caplog.at_level(logging.INFO, logger="cubik.tools"):
        observability.log_tool_call(TOOL, {}, CONTEXT, {})
    assert logged_lines(caplog)[0]["trace_id"] is None


def test_rag_chunks_are_logged_as_their_sources_only(caplog) -> None:
    """Verify retrieved chunk texts are not dumped into the log, only how many and from where."""
    chunks = [{"text": "long passage", "source": "a.md"}, {"text": "other", "source": "b.md"},
              {"text": "more", "source": "a.md"}]
    with caplog.at_level(logging.INFO, logger="cubik.tools"):
        observability.log_tool_call(TOOL, {}, CONTEXT, {"chunks": chunks})
    assert logged_lines(caplog)[0]["result"] == {"n_chunks": 3, "sources": ["a.md", "b.md"]}


def test_long_results_are_truncated(caplog) -> None:
    """Verify one huge tool result can't flood the log."""
    with caplog.at_level(logging.INFO, logger="cubik.tools"):
        observability.log_tool_call(TOOL, {}, CONTEXT, {"steps": "x" * 2000})
    result = logged_lines(caplog)[0]["result"]
    assert isinstance(result, str) and result.endswith("...")
    assert len(result) == observability.MAX_LOGGED_CHARS + 3


def test_tool_errors_are_logged_without_swallowing_them(caplog) -> None:
    """Verify a failing tool is logged and the error callback returns None (ADK re-raises)."""
    with caplog.at_level(logging.INFO, logger="cubik.tools"):
        result = observability.log_tool_error(TOOL, {"x": 1}, CONTEXT, ValueError("bad input"))
    [line] = logged_lines(caplog)
    assert result is None
    assert line["event"] == "tool_failed"
    assert line["error"] == "ValueError: bad input"


def test_setup_tracing_is_off_without_langfuse_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the tutor runs untraced, instead of failing, when no Langfuse keys are set."""
    monkeypatch.setattr(observability, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    assert observability.setup_tracing() is False


@pytest.mark.parametrize(
    "agent",
    [tutor.root_agent, team.root_agent, team.theory_agent, team.solver_agent, team.verifier_agent,
     team.progress_agent],
    ids=lambda agent: agent.name,
)
def test_every_agent_logs_its_tool_calls(agent) -> None:
    """Verify the whole tool layer is covered: every agent with tools has both callbacks."""
    assert agent.after_tool_callback is observability.log_tool_call
    assert agent.on_tool_error_callback is observability.log_tool_error
