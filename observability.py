"""Langfuse tracing and structured tool-call logging for the Cubik-Lite ADK agents.

Two pieces, both used by agents/cubik_tutor and agents/cubik_team:

- setup_tracing(): starts the Langfuse client (which registers its OpenTelemetry
  exporter) and turns on OpenInference's blanket ADK instrumentation, so every
  run, LLM call and tool call becomes a span in Langfuse. It is a no-op when the
  LANGFUSE_* keys are not set, so the tutor still runs without an account.
- TOOL_LOGGING: after_tool_callback / on_tool_error_callback for every agent.
  Each tool call writes one JSON log line carrying the current OpenTelemetry
  trace ID, which is the Langfuse trace ID: a log line can be pasted into the
  Langfuse search to open the trace it belongs to.

See week_13/README.md.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from opentelemetry import trace

logger = logging.getLogger("cubik.tools")

MAX_LOGGED_CHARS = 500  # tool results can be long (RAG chunks); keep each log line readable


def setup_tracing() -> bool:
    """Send ADK traces to Langfuse, if its keys are configured.

    Must run before the agents are built. Safe to call more than once.

    Returns:
        True if tracing is on, False if the LANGFUSE_* keys are missing.
    """
    load_dotenv(Path(__file__).resolve().parent / ".env")
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        return False

    from langfuse import get_client
    from openinference.instrumentation.google_adk import GoogleADKInstrumentor

    get_client()  # registers the exporter; without it the spans go nowhere
    instrumentor = GoogleADKInstrumentor()
    if not instrumentor.is_instrumented_by_opentelemetry:
        instrumentor.instrument()
    return True


def current_trace_id() -> str | None:
    """The active OpenTelemetry trace ID in Langfuse's format, or None when not tracing."""
    context = trace.get_current_span().get_span_context()
    return format(context.trace_id, "032x") if context.is_valid else None


def _summarize(response: Any) -> Any:
    """Shorten a tool result for the log: RAG chunks become their sources, long values are cut."""
    if isinstance(response, dict) and isinstance(response.get("chunks"), list):
        chunks = response["chunks"]
        return {"n_chunks": len(chunks), "sources": sorted({c.get("source") for c in chunks})}
    text = json.dumps(response, ensure_ascii=False, default=str)
    return response if len(text) <= MAX_LOGGED_CHARS else text[:MAX_LOGGED_CHARS] + "..."


def _log(event: str, tool, args: dict, tool_context, **fields) -> None:
    logger.info(json.dumps(
        {
            "event": event,
            "trace_id": current_trace_id(),
            "invocation_id": tool_context.invocation_id,
            "agent": tool_context.agent_name,
            "tool": tool.name,
            "args": args,
            **fields,
        },
        ensure_ascii=False,
        default=str,
    ))


def log_tool_call(tool, args: dict, tool_context, tool_response: Any) -> None:
    """after_tool_callback: one JSON line per tool call. Returns None, so the result is untouched."""
    _log("tool_called", tool, args, tool_context, result=_summarize(tool_response))


def log_tool_error(tool, args: dict, tool_context, error: Exception) -> None:
    """on_tool_error_callback: log the failure and let ADK handle the exception as before."""
    _log("tool_failed", tool, args, tool_context, error=f"{type(error).__name__}: {error}")


# Spread into every Agent(...) so the whole tool layer is logged the same way.
TOOL_LOGGING = {"after_tool_callback": log_tool_call, "on_tool_error_callback": log_tool_error}
