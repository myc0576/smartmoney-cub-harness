from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from smartmoney_cub_harness.schemas import SAFETY_DECLARATION

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "smartmoney_cub_harness.cli", *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_readme_quick_start_loop_command_is_real():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    zh_readme = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

    assert 'smcub loop --preset toy --agent-trigger "自进化"' in readme
    assert 'smcub loop --preset toy --agent-trigger "自进化"' in zh_readme

    result = run_cli("loop", "--preset", "toy", "--agent-trigger", "自进化")
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["status"] == "ok"
    assert payload["loop_report"].endswith("loop_report.md")
    assert payload["trace"].endswith("trace.jsonl")
    assert payload["safety"] == SAFETY_DECLARATION


def test_readmes_document_control_plane_commands_and_boundaries():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    zh_readme = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

    for command in (
        "capture-run",
        "validate-envelope",
        "build-evidence-pack",
        "replay-evidence-pack",
    ):
        assert command in readme
        assert command in zh_readme

    assert "local-first" in readme
    assert "agent-agnostic" in readme
    assert "no embedded LLM" in readme
    assert "no broker connection" in readme
    assert "no automatic trading" in readme
    assert SAFETY_DECLARATION in readme

    assert "本地优先" in zh_readme
    assert "不绑定任何 Agent" in zh_readme
    assert "不内置 LLM" in zh_readme
    assert "不连接券商" in zh_readme
    assert "不自动交易" in zh_readme
    assert SAFETY_DECLARATION in zh_readme


def test_toy_rule_candidate_is_challenger_only_and_read_only():
    candidate_path = REPO_ROOT / "examples" / "toy_strategy" / "sample_rule_candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    assert candidate["candidate_role"] == "challenger"
    assert candidate["champion_mutated"] is False
    assert candidate["core_rules_mutated"] is False
    assert candidate["safety"] == SAFETY_DECLARATION


def test_architecture_scopes_capture_writes_separately_from_governance():
    architecture = (REPO_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")

    assert "`writes: run_directory_only` applies to captured external tool calls" in architecture
    assert "governance commands may write local evidence and registry artifacts" in architecture
    assert "`register-candidate --confirm-promote`" in architecture
    assert "Its only write permission is the selected run/evidence directory" not in architecture
