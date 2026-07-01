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
