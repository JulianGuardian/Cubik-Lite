"""Week 12, Activity 4 -- run the whole Cubik-Lite eval pipeline with one command.

  1. `adk eval` on the real cubik_team agent with evalsets/cubik_team.evalset.json
     (tool trajectory + response match, thresholds in evalsets/cubik_team_config.json).
  2. cubik_judge.py: LLM-as-judge faithfulness check of the RAG-backed answers.

Both stages always run; the exit code is non-zero if either fails, so it can gate CI.
The project root is this folder's parent; override it with CUBIK_PROJECT_ROOT.

Run with: python run_pipeline.py
"""

import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = Path(os.environ.get("CUBIK_PROJECT_ROOT", HERE.parent)).resolve()

ADK_EVAL = [
    sys.executable, "-m", "google.adk.cli", "eval",
    "agents/cubik_team",  # relative to PROJECT_ROOT: adk imports agents.cubik_team from there
    str(HERE / "evalsets" / "cubik_team.evalset.json"),
    "--config_file_path", str(HERE / "evalsets" / "cubik_team_config.json"),
    "--print_detailed_results",
]
JUDGE = [sys.executable, str(HERE / "cubik_judge.py")]

# The agents print Spanish text with accents; avoid cp1252 errors on Windows consoles.
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}


def run(title: str, cmd: list[str], cwd: Path) -> tuple[bool, str]:
    """Run a stage, echoing its output live; return (exit code was 0, captured output)."""
    print(f"\n===== {title} =====", flush=True)
    proc = subprocess.Popen(
        cmd, cwd=cwd, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    lines = []
    for line in proc.stdout:
        print(line, end="", flush=True)
        lines.append(line)
    return proc.wait() == 0, "".join(lines)


def adk_eval_passed(exit_ok: bool, output: str) -> bool:
    """`adk eval` exits 0 even when cases fail, so read its own summary line instead."""
    failed = re.search(r"Tests failed:\s*(\d+)", output)
    passed = re.search(r"Tests passed:\s*(\d+)", output)
    return exit_ok and bool(failed and passed) and int(failed.group(1)) == 0 and int(passed.group(1)) > 0


def main() -> int:
    eval_ok, eval_out = run("adk eval", ADK_EVAL, PROJECT_ROOT)
    judge_ok, _ = run("LLM judge", JUDGE, HERE)
    results = {
        "adk eval (trajectory + response match)": adk_eval_passed(eval_ok, eval_out),
        "LLM-judge faithfulness": judge_ok,
    }
    print("\n===== SUMMARY =====")
    for name, ok in results.items():
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
