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


def test_readmes_document_isolated_installation_and_cli_upgrades():
    readmes = [
        (REPO_ROOT / "README.md").read_text(encoding="utf-8"),
        (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8"),
    ]

    for readme in readmes:
        assert "python -m venv .venv" in readme
        assert "py -m venv .venv" in readme
        assert "pipx install smartmoney-cub-harness" in readme
        assert "pipx upgrade smartmoney-cub-harness" in readme
        assert "smcub --version" in readme
        assert "docs/versioning.md" in readme


def test_versioning_policy_covers_all_supported_update_paths():
    policy = (REPO_ROOT / "docs" / "versioning.md").read_text(encoding="utf-8")

    assert "Semantic Versioning" in policy
    assert "git pull" in policy
    assert "python -m pip install --upgrade smartmoney-cub-harness" in policy
    assert "pipx upgrade smartmoney-cub-harness" in policy
    assert "Trusted Publishing" in policy
    assert "vX.Y.Z" in policy
    assert "does not update automatically" in policy.lower()
    assert "Current release channel: GitHub Releases" in policy
    assert "git+https://github.com/myc0576/smartmoney-cub-harness.git@v0.1.1" in policy


def test_local_virtual_environment_is_ignored():
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert ".venv/" in gitignore
