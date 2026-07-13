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
    command = 'smcub loop --preset toy --agent-trigger "自进化"'

    assert command in readme
    assert command in zh_readme
    assert SAFETY_DECLARATION in readme
    assert SAFETY_DECLARATION in zh_readme

    result = run_cli("loop", "--preset", "toy", "--agent-trigger", "自进化")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["loop_report"].endswith("loop_report.md")
    assert payload["trace"].endswith("trace.jsonl")
    assert payload["safety"] == SAFETY_DECLARATION


def test_readme_points_to_integration_contract():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    integrations = (REPO_ROOT / "docs" / "integrations.md").read_text(encoding="utf-8")

    assert "wbh604/UZI-Skill" in readme
    assert "docs/integrations.md" in readme
    assert "recommended-companion" in integrations
    assert "runtime-integrated" in integrations
    assert SAFETY_DECLARATION in integrations


def test_readmes_document_control_plane_commands_and_boundaries():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    zh_readme = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

    for command in ("capture-run", "validate-envelope", "build-evidence-pack", "replay-evidence-pack"):
        assert command in readme
        assert command in zh_readme

    for phrase in (
        "local-first",
        "agent-agnostic",
        "no embedded LLM",
        "no broker connection",
        "no automatic trading",
        "declarative, unverified policy record",
        "not a subprocess sandbox",
        "only selects the disposable `tmp/sandbox` output namespace",
        "evidence_pack.sha256",
    ):
        assert phrase in readme
    for phrase in (
        "本地优先",
        "不绑定任何 Agent",
        "不内置 LLM",
        "不连接券商",
        "不自动交易",
        "声明式、未经验证的策略记录",
        "不是子进程沙箱",
        "只选择一次性的 `tmp/sandbox` 输出目录",
        "evidence_pack.sha256",
    ):
        assert phrase in zh_readme


def test_toy_rule_candidate_is_challenger_only_and_read_only():
    candidate = json.loads(
        (REPO_ROOT / "examples" / "toy_strategy" / "sample_rule_candidate.json").read_text(
            encoding="utf-8"
        )
    )
    assert candidate["candidate_role"] == "challenger"
    assert candidate["champion_mutated"] is False
    assert candidate["core_rules_mutated"] is False
    assert candidate["safety"] == SAFETY_DECLARATION


def test_architecture_distinguishes_declared_policy_from_enforcement():
    architecture = (REPO_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")

    assert "`enforcement: declarative`" in architecture
    assert "`verified: false`" in architecture
    assert "does not sandbox arbitrary captured commands" in architecture
    assert "governance commands may write local evidence and registry artifacts" in architecture
    assert "not an authenticated signature" in architecture
    assert "`register-candidate --confirm-promote`" in architecture
