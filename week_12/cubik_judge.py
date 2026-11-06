"""Week 12, Activity 4 -- LLM-as-judge faithfulness check for the RAG-backed answers of the
Cubik-Lite project (proyecto_ai_agentic, Corte 2 multi-agent team).

Unlike the course's llm_judge.py (which judges a toy generator), this runs the REAL
`cubik_coordinator` team on each question and judges what the student would actually see:

  1. Run the team with ADK's InMemoryRunner and collect, from the event stream, the final JSON
     answer and the evidence the specialists saw (RAG chunks from `search_knowledge_base` plus the
     SymPy results of the math tools).
  2. Ask a Gemini judge to score faithfulness (every claim supported by that evidence?) and
     relevance (does it answer the question?), and to say whether the answer declined.
  3. A deterministic check on top: every path in the answer's "source" must be a source the
     retriever really returned (catches invented citations the judge could miss).

Out-of-scope questions are expected to be declined with no retrieved evidence.
Exit code is 1 when any case fails, so the pipeline can gate on it.

This folder lives at the project root (week_12/), so the project is its parent directory; set
CUBIK_PROJECT_ROOT to point somewhere else. Requires GEMINI_API_KEY (read from the project's .env).

Run with: python cubik_judge.py [--out judge_report.json]
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = Path(os.environ.get("CUBIK_PROJECT_ROOT", HERE.parent)).resolve()
if not (PROJECT_ROOT / "agents" / "cubik_team" / "agent.py").exists():
    raise SystemExit(f"cubik_team not found under {PROJECT_ROOT}; set CUBIK_PROJECT_ROOT.")
sys.path.insert(0, str(PROJECT_ROOT))

import llm_client  # noqa: E402,F401  (side effect: loads the project's .env, incl. GEMINI_API_KEY)
from agents.cubik_team.agent import root_agent  # noqa: E402  (the real team under test)
from google import genai  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "gemini-flash-latest")
MIN_FAITHFULNESS = 4  # 1-5 scale; below this an in-scope answer fails
MIN_RELEVANCE = 4
MAX_EVIDENCE_CHARS = 18000  # cap on the evidence text handed to the judge
TRANSFER_TOOL = "transfer_to_agent"  # routing, not evidence


@dataclass
class Case:
    case_id: str
    question: str
    in_scope: bool


# in_scope=False is deliberately outside the indexed knowledge base: the team must decline.
CASES = [
    Case("theory_constant_c", "¿Por qué siempre sumamos la constante +C al calcular una integral indefinida?", True),
    Case("theory_substitution_vs_parts", "¿Cuándo conviene usar sustitución en lugar de integración por partes?", True),
    Case("applications_area_between_curves", "¿Cómo se calcula el área entre dos curvas usando integrales definidas?", True),
    Case("solver_power_rule", "Resuelve la integral de x^2 dx", True),
    Case("out_of_scope_capital", "¿Cuál es la capital de Francia?", False),
]


class Verdict(BaseModel):
    faithfulness: int = Field(
        ge=1, le=5,
        description="1 = main claims unsupported by the evidence, 5 = every claim supported by it",
    )
    relevance: int = Field(ge=1, le=5, description="1 = off-topic, 5 = directly answers the question")
    declined: bool = Field(description="True if the answer declines/redirects instead of answering")
    unsupported_claims: list[str] = Field(description="Claims not backed by the evidence; empty if none")
    rationale: str = Field(description="One or two sentences justifying the scores")


JUDGE_PROMPT = """\
You are a strict evaluator of a RAG-backed tutoring assistant for integral calculus.

QUESTION asked by the student:
{question}

EVIDENCE the assistant had (passages retrieved from its knowledge base and results of exact SymPy tools):
{evidence}

ANSWER the student received (JSON from the assistant; "source" lists the files it cites):
{answer}

Score:
- faithfulness (1-5): is every claim about rules, theory or results supported by the EVIDENCE? Plain
  arithmetic or algebra that connects evidence steps is fine. Facts, rules or theorems that appear only
  in the assistant's own background knowledge are unsupported. If there is no evidence and the answer
  makes calculus claims, faithfulness is 1. If the answer only declines, faithfulness is 5.
- relevance (1-5): does the answer address the question?
- declined: true if the assistant declines or redirects instead of answering.
List each unsupported claim in unsupported_claims (empty list if none)."""


def parse_answer(text: str) -> dict:
    """The agents reply with a JSON object, sometimes wrapped in a ```json fence."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return {"answer": text, "steps": [], "rule": None, "confidence": None, "source": None}


async def run_team(question: str) -> dict:
    """Run the real team on one question in a fresh session; return answer + evidence."""
    runner = InMemoryRunner(agent=root_agent, app_name="cubik_team")
    session = await runner.session_service.create_session(app_name="cubik_team", user_id="judge")
    message = types.Content(role="user", parts=[types.Part(text=question)])

    final_text, chunks, tool_results, tools_called = "", [], [], []
    async for event in runner.run_async(user_id="judge", session_id=session.id, new_message=message):
        for call in event.get_function_calls():
            tools_called.append(call.name)
        for resp in event.get_function_responses():
            if resp.name == TRANSFER_TOOL:
                continue
            payload = resp.response or {}
            if resp.name == "search_knowledge_base":
                chunks.extend(payload.get("chunks", []))
            else:
                tool_results.append({"tool": resp.name, "result": payload})
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(p.text or "" for p in event.content.parts)
    return {
        "answer": parse_answer(final_text),
        "chunks": chunks,
        "tool_results": tool_results,
        "tools_called": tools_called,
    }


def format_evidence(chunks: list[dict], tool_results: list[dict]) -> str:
    parts = [f"[passage {i + 1}] source: {c['source']}\n{c['text']}" for i, c in enumerate(chunks)]
    parts += [f"[tool {r['tool']}] {json.dumps(r['result'], ensure_ascii=False)}" for r in tool_results]
    text = "\n\n".join(parts) if parts else "(none -- the assistant retrieved nothing)"
    return text[:MAX_EVIDENCE_CHARS]


def judge(client: genai.Client, question: str, evidence: str, answer: dict) -> Verdict:
    prompt = JUDGE_PROMPT.format(
        question=question, evidence=evidence, answer=json.dumps(answer, ensure_ascii=False)
    )
    config = types.GenerateContentConfig(
        temperature=0, response_mime_type="application/json", response_schema=Verdict
    )
    for attempt in range(3):  # transient 429/503s are common on the free tier
        try:
            response = client.models.generate_content(model=JUDGE_MODEL, contents=prompt, config=config)
            return Verdict.model_validate_json(response.text)
        except Exception as exc:  # noqa: BLE001
            if attempt == 2:
                raise
            print(f"  judge call failed ({type(exc).__name__}), retrying...", file=sys.stderr)
            time.sleep(2 ** (attempt + 1))


def check_case(case: Case, run: dict, verdict: Verdict) -> tuple[bool, list[str]]:
    """Apply the pass/fail rules; return (passed, reasons for failing)."""
    problems = []
    cited = run["answer"].get("source") or []
    if isinstance(cited, str):
        cited = [cited]
    retrieved = {c["source"] for c in run["chunks"]}
    invented = [s for s in cited if s not in retrieved]
    if invented:
        problems.append(f"cites sources the retriever never returned: {invented}")

    if case.in_scope:
        if verdict.declined:
            problems.append("declined an in-scope question")
        if verdict.faithfulness < MIN_FAITHFULNESS:
            problems.append(f"faithfulness {verdict.faithfulness} < {MIN_FAITHFULNESS}")
        if verdict.relevance < MIN_RELEVANCE:
            problems.append(f"relevance {verdict.relevance} < {MIN_RELEVANCE}")
    else:
        if not verdict.declined:
            problems.append("answered an out-of-scope question instead of declining")
        if run["chunks"]:
            problems.append("retrieved knowledge-base chunks for an out-of-scope question")
    return not problems, problems


async def main(out_path: Path | None) -> int:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key or api_key == "PEGA_TU_API_KEY_AQUI":
        raise SystemExit("Set GEMINI_API_KEY (in the project's .env or the environment).")
    client = genai.Client(api_key=api_key)

    report, failures = [], 0
    for case in CASES:
        print(f"Q [{case.case_id}] (in_scope={case.in_scope}): {case.question}")
        run = await run_team(case.question)
        evidence = format_evidence(run["chunks"], run["tool_results"])
        verdict = judge(client, case.question, evidence, run["answer"])
        passed, problems = check_case(case, run, verdict)
        failures += not passed

        print(f"  tools: {run['tools_called']}")
        print(f"  retrieved sources: {sorted({c['source'] for c in run['chunks']})}")
        print(f"  A: {str(run['answer'].get('answer'))[:300]}")
        print(f"  faithfulness={verdict.faithfulness} relevance={verdict.relevance} "
              f"declined={verdict.declined} -> {'PASS' if passed else 'FAIL'}")
        print(f"  judge: {verdict.rationale}")
        for claim in verdict.unsupported_claims:
            print(f"  unsupported: {claim}")
        for problem in problems:
            print(f"  problem: {problem}")
        print()
        report.append({
            "case_id": case.case_id, "question": case.question, "in_scope": case.in_scope,
            "passed": passed, "problems": problems, "tools_called": run["tools_called"],
            "retrieved_sources": sorted({c["source"] for c in run["chunks"]}),
            "answer": run["answer"], "verdict": verdict.model_dump(),
        })

    scored = [r["verdict"] for r in report if r["in_scope"]]
    print(f"In-scope average faithfulness: {sum(v['faithfulness'] for v in scored) / len(scored):.2f} / 5")
    print(f"In-scope average relevance:    {sum(v['relevance'] for v in scored) / len(scored):.2f} / 5")
    print(f"Cases passed: {len(CASES) - failures}/{len(CASES)}")

    if out_path:
        out_path.write_text(
            json.dumps({"judge_model": JUDGE_MODEL, "cases": report}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Report written to {out_path}")
    return 1 if failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=HERE / "judge_report.json")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.out)))
