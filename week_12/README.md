# Week 12 — Evaluation pipeline for Cubik-Lite (Activity 4)

Eval pipeline for the Corte 2 multi-agent tutor in this repo (`agents/cubik_team`).
This folder holds only the evaluation side; it sits at the project root.

| Piece | File | What it checks |
|---|---|---|
| Eval cases | [`evalsets/cubik_team.evalset.json`](evalsets/cubik_team.evalset.json) | 5 cases: theory (RAG), solver, verifier, coordinator, and a two-turn conversation. |
| Criteria | [`evalsets/cubik_team_config.json`](evalsets/cubik_team_config.json) | `adk eval` metrics and thresholds. |
| LLM judge | [`cubik_judge.py`](cubik_judge.py) | Faithfulness / relevance of the RAG-backed answers, plus declining out-of-scope questions. Writes [`judge_report.json`](judge_report.json). |
| One-command runner | [`run_pipeline.py`](run_pipeline.py) | `adk eval`, then the judge; non-zero exit if either fails. |

## Run it

```bash
pip install -r week_12/requirements.txt  # project dependencies + the google-adk[eval] extra
# GEMINI_API_KEY is read from the project's .env; the RAG index must exist (python retriever.py)
python week_12/run_pipeline.py           # both stages
```

Or separately. `adk eval` must run from the **project root** (the agent imports `retriever`, `math_tools` and
`agents.*` relative to it, and the `chroma_db/` index lives there):

```bash
python -m google.adk.cli eval agents/cubik_team week_12/evalsets/cubik_team.evalset.json \
    --config_file_path week_12/evalsets/cubik_team_config.json --print_detailed_results
python week_12/cubik_judge.py
```

The project root is this folder's parent; set `CUBIK_PROJECT_ROOT` to use another checkout.

> `adk eval` exits with code 0 even when cases fail (it only prints `Tests failed: N`). `run_pipeline.py`
> therefore reads that summary line instead of trusting the exit code.

## Design decisions

**Trajectory, not just answers.** `tool_trajectory_avg_score` is matched `IN_ORDER` with `ignore_args`. Each
case's `tool_uses` lists only the calls the prompts *require*, in the order they must happen (for example
`transfer_to_agent` → `solve_integral` → `search_knowledge_base` for the solver); extra calls are allowed.
Arguments are ignored because the model rewrites them on every run (`x^2` vs `x**2`, a free-text `technique`,
the wording of the search query). Argument correctness is covered by the answer itself: the SymPy tools produce
the result, so a wrong argument shows up as a wrong answer.

**Multi-tool trajectories.** `solver_power_rule_multi_tool` (handoff + 2 tools),
`coordinator_detail_level_and_progress_multi_tool` (a tool and an `AgentTool` in one turn) and
`verifier_wrong_answer_then_progress_two_turns` (turn 1 logs an attempt through a tool, turn 2 reads it back
through another agent, so it also exercises session state).

**Isolated cases.** Every case has its own `user_id`. Without it, `user:` state leaked between cases (the
two-turn case saw the `detallado` preference another case had set). `app:` state (the global attempt counter)
is still shared by the whole run and cannot be isolated from the evalset, so no expected value depends on it.

**Response match.** `response_match_score` is ROUGE-1 against a reference written in the agent's real output
shape (the five-key JSON). The threshold, **0.4**, comes from measurements, not a default:

| | ROUGE-1 F |
|---|---|
| Right answer, 3 runs × 5 cases | 0.55 – 0.87 |
| Answer of a *different* case, same 5 cases cross-compared | median 0.28, max 0.52 |
| Old threshold (kept every answer, even an unrelated one) | 0.1 |

0.4 sits above the typical wrong-topic score and 0.15 below the weakest correct one. ROUGE-1 is only a coarse
"same topic and shape" check (the verifier and solver replies look alike, which is why the wrong-answer maximum
is 0.52); faithfulness is the judge's job.

**`final_response_match_v2` was tried and dropped.** ADK's LLM response matcher approved a reference about the
capital of France for an answer about the constant of integration (score 1.0): its prompt judges whether the
agent's answer is right for the *question* and treats the reference as a hint, so it did not discriminate.

**LLM-as-judge on the real agent.** `cubik_judge.py` runs the real team (not a stand-in generator) with ADK's
`InMemoryRunner`, collects the chunks `search_knowledge_base` actually returned and the SymPy tool results, and has a
Gemini judge score the final JSON answer against *that* evidence. A deterministic check on top fails any case
whose `source` cites a file the retriever never returned. The out-of-scope question must be declined with nothing
retrieved. In-scope cases need faithfulness ≥ 4 and relevance ≥ 4.

## Evidence that the checks can fail

Both layers were run against deliberately broken inputs:

| Control | Result |
|---|---|
| Solver case expecting the verifier's tool | `tool_trajectory_avg_score` 0.0 → FAILED |
| Theory case with an expected answer about France | `response_match_score` 0.14 < 0.4 → FAILED |
| Judge, answer with invented theorems and a made-up source | faithfulness 1, flagged the fake source → FAIL |
| Judge, true answer plus one outside claim ("formalizado por Newton y Leibniz") | faithfulness 3, claim listed as unsupported → FAIL |

## Results (real agent, Gemini)

* `adk eval`, 3 consecutive runs: 5/5 cases pass each time, trajectory 1.0 in all 15 case-runs.
* Judge ([`judge_report.json`](judge_report.json)): in-scope faithfulness 5.00, relevance 5.00; the out-of-scope
  question was declined with nothing retrieved. 5/5.

**Hand spot-check of a judge verdict** (`theory_constant_c`, judged faithfulness 5): the answer's claims
that an antiderivative satisfies `F'(x) = f(x)`, that integration is the inverse of differentiation, and that
`∫ f dx` is the family of all antiderivatives all appear in `data/indefinite_integrals/antiderivatives.md` and
`basic_rules.md`, the two files it cites; the derivative of the constant is the `+ 0` in the differentiation
check of `antiderivatives.md`. The verdict is right.

## Known limits

* Arguments are not checked by the trajectory metric (see above).
* The judge is Gemini grading Gemini output; the controls show it catches unsupported claims, but a perfect
  5.00 on five cases is a small sample.
* An observation about the project, not the eval: `progress_agent` also receives the app-wide attempt counter,
  and in the two-turn case the coordinator once described it as "interacciones registradas en la sesión".
