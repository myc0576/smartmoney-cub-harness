from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from smartmoney_cub_harness.schemas import SAFETY_DECLARATION

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_STEPS = [
    "resolve_agent_trigger",
    "doctor",
    "observe",
    "candidate",
    "plan",
    "position_check",
    "outcome",
    "evaluate",
    "review",
    "propose_challenger_rule",
    "generate_report",
]
FORBIDDEN_PHRASES = [
    "buy now",
    "sell now",
    "guaranteed",
    "recommendation",
    "should buy",
    "sure win",
]
ABSOLUTE_PATH_RE = re.compile(r"(?i)([A-Z]:\\|/Users/|/home/)")


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "smartmoney_cub_harness.cli", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def load_summary(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def read_loop_outputs(summary: dict) -> tuple[str, str, list[dict]]:
    report_text = (REPO_ROOT / summary["report_path"]).read_text(encoding="utf-8")
    trace_text = (REPO_ROOT / summary["trace_path"]).read_text(encoding="utf-8")
    trace = [json.loads(line) for line in trace_text.splitlines() if line.strip()]
    return report_text, trace_text, trace


def assert_no_local_path_leakage(*texts: str) -> None:
    for text in texts:
        assert not ABSOLUTE_PATH_RE.search(text)


def assert_forbidden_phrases_absent(*texts: str) -> None:
    lowered = "\n".join(texts).lower()
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in lowered


def test_loop_preset_toy_exits_successfully_and_prints_safe_summary():
    result = run_cli("loop", "--preset", "toy", "--json")

    summary = load_summary(result)

    assert summary["status"] == "ok"
    assert summary["loop_name"] == "observe_candidate_plan_position_outcome_review_rule_update"
    assert summary["preset"] == "toy"
    assert summary["safety"] == SAFETY_DECLARATION
    assert summary["champion_mutated"] is False
    assert summary["grade"] == "useful_alert"
    assert SAFETY_DECLARATION in result.stdout
    assert '"champion_mutated": false' in result.stdout


def test_loop_accepts_chinese_and_english_agent_triggers():
    chinese = load_summary(run_cli("loop", "--preset", "toy", "--agent-trigger", "自进化"))
    english = load_summary(run_cli("loop", "--preset", "toy", "--agent-trigger", "loop"))

    assert chinese["status"] == "ok"
    assert english["status"] == "ok"
    assert chinese["agent_intent"] == "full_loop"
    assert english["agent_intent"] == "full_loop"


def test_loop_generates_report_trace_and_required_artifacts():
    summary = load_summary(run_cli("loop", "--preset", "toy", "--agent-trigger", "loop", "--horizon", "d1"))
    report_path = REPO_ROOT / summary["report_path"]
    trace_path = REPO_ROOT / summary["trace_path"]

    assert report_path.exists()
    assert trace_path.exists()
    assert (REPO_ROOT / summary["decision_path"]).exists()
    assert (REPO_ROOT / summary["outcome_path"]).exists()
    assert (REPO_ROOT / summary["evaluation_path"]).exists()
    assert (REPO_ROOT / summary["proposed_challenger_rule_path"]).exists()

    report_text, trace_text, trace = read_loop_outputs(summary)
    assert [line["step"] for line in trace] == REQUIRED_STEPS
    assert all(line["safety"] == SAFETY_DECLARATION for line in trace)
    assert all(line["champion_mutated"] is False for line in trace)
    assert all(line["no_future_leakage"] is True for line in trace)
    assert "Smartmoney Cub Agent Loop Report" in report_text
    assert "champion_mutated: false" in report_text
    assert_no_local_path_leakage(result_text := json.dumps(summary, ensure_ascii=False), report_text, trace_text)
    assert_forbidden_phrases_absent(result_text, report_text, trace_text)


def test_challenger_rule_proposal_does_not_mutate_champion_registry():
    summary = load_summary(run_cli("loop", "--preset", "toy", "--agent-trigger", "规则进化"))
    registry = json.loads((REPO_ROOT / summary["rule_registry_path"]).read_text(encoding="utf-8"))
    proposal = json.loads((REPO_ROOT / summary["proposed_challenger_rule_path"]).read_text(encoding="utf-8"))

    assert registry["champions"] == {}
    assert proposal["candidate_role"] == "challenger"
    assert proposal["champion_mutated"] is False


def test_readme_demo_command_shape_works_when_console_script_is_available():
    smcub = shutil.which("smcub")
    if smcub is None:
        result = run_cli("loop", "--preset", "toy", "--agent-trigger", "loop")
    else:
        result = subprocess.run(
            [smcub, "loop", "--preset", "toy", "--agent-trigger", "loop"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    summary = load_summary(result)

    assert summary["status"] == "ok"
    assert summary["safety"] == SAFETY_DECLARATION
