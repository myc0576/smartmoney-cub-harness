# CLI Version Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare release `0.1.1` with a single version source, reliable CLI version reporting, privacy-safe launcher conflict diagnostics, and documented pipx/PyPI upgrade practices.

**Architecture:** Keep the version as a literal package attribute and let setuptools read it dynamically for build metadata. Add a focused launcher-diagnostics module that returns path-free booleans and counts to `doctor`, while argparse owns the top-level version flag. Keep installation and release policy in documentation; do not add network checks or self-update behavior.

**Tech Stack:** Python 3.10+, argparse, pathlib, sysconfig, setuptools PEP 621 metadata, pytest, Markdown, GitHub Actions.

## Global Constraints

- Preserve `READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE` on every existing protected output.
- Keep default operation offline with no telemetry, upload, update check, broker integration, or self-update mutation.
- Add no runtime or development dependencies.
- Never emit launcher paths, Python installation paths, usernames, credentials, or local identifiers.
- Prepare version `0.1.1`; do not claim or perform a PyPI release before Trusted Publishing is configured and verified.
- Use Semantic Versioning and never reuse a published version.

---

### Task 1: Single Version Source and `--version`

**Files:**
- Create: `tests/test_cli_version.py`
- Modify: `src/smartmoney_cub_harness/__init__.py`
- Modify: `src/smartmoney_cub_harness/cli.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: `smartmoney_cub_harness.__version__: str` with value `0.1.1`.
- Produces: `smcub --version` output `smcub 0.1.1` with exit code 0.
- Produces: setuptools dynamic version mapping to `smartmoney_cub_harness.__version__`.

- [ ] **Step 1: Write failing CLI and metadata tests**

```python
from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from pathlib import Path

from smartmoney_cub_harness import __version__

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_cli_version_matches_package_version():
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-m", "smartmoney_cub_harness.cli", "--version"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"smcub {__version__}"
    assert __version__ == "0.1.1"


def test_build_metadata_uses_package_version_attribute():
    payload = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert payload["project"]["dynamic"] == ["version"]
    assert "version" not in payload["project"]
    assert payload["tool"]["setuptools"]["dynamic"]["version"] == {
        "attr": "smartmoney_cub_harness.__version__"
    }
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_cli_version.py -v`

Expected: FAIL because `--version` is not defined, the package version is `0.1.0`, and `pyproject.toml` still has a static version.

- [ ] **Step 3: Implement the single source and CLI flag**

Change `src/smartmoney_cub_harness/__init__.py`:

```python
__version__ = "0.1.1"
```

In `build_parser()` add before subparser creation:

```python
parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
```

In `pyproject.toml`, replace the static version with:

```toml
[project]
dynamic = ["version"]
```

and add:

```toml
[tool.setuptools.dynamic]
version = { attr = "smartmoney_cub_harness.__version__" }
```

- [ ] **Step 4: Run focused and packaging tests and verify GREEN**

Run: `python -m pytest tests/test_cli_version.py tests/test_doctor.py -v`

Expected: all selected tests PASS.

Run: `python -m pip wheel . --no-deps --wheel-dir tmp/version-wheel`

Expected: exit 0 and a wheel named `smartmoney_cub_harness-0.1.1-*.whl`.

- [ ] **Step 5: Commit the independently working version feature**

```text
git add pyproject.toml src/smartmoney_cub_harness/__init__.py src/smartmoney_cub_harness/cli.py tests/test_cli_version.py
git commit -m "Make installed CLI versions unambiguous"
```

The actual commit must include the repository Lore trailers and record focused tests plus wheel build evidence.

---

### Task 2: Privacy-Safe Launcher Diagnostics

**Files:**
- Create: `src/smartmoney_cub_harness/launcher.py`
- Create: `tests/test_launcher.py`
- Modify: `src/smartmoney_cub_harness/cli.py`
- Modify: `tests/test_doctor.py`

**Interfaces:**
- Produces: `launcher_diagnostics(path_value: str | None = None, scripts_dir: str | Path | None = None, platform_name: str | None = None, pathext: str | None = None) -> dict[str, bool | int]`.
- Returns keys: `launcher_found`, `launcher_count`, `multiple_launchers`, `resolved_to_current_environment`.
- `doctor()` adds the result under `launcher` without changing existing keys.

- [ ] **Step 1: Write failing discovery and privacy tests**

```python
from __future__ import annotations

import json
import os
from pathlib import Path

from smartmoney_cub_harness.launcher import launcher_diagnostics


def _make_launcher(directory: Path, name: str = "smcub.exe") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    launcher = directory / name
    launcher.write_text("fixture", encoding="utf-8")
    return launcher


def test_launcher_diagnostics_reports_missing_launcher(tmp_path):
    result = launcher_diagnostics(
        path_value=str(tmp_path / "missing"),
        scripts_dir=tmp_path / "current",
        platform_name="nt",
        pathext=".EXE;.CMD",
    )

    assert result == {
        "launcher_found": False,
        "launcher_count": 0,
        "multiple_launchers": False,
        "resolved_to_current_environment": False,
    }


def test_launcher_diagnostics_deduplicates_path_entries(tmp_path):
    scripts = tmp_path / "current"
    _make_launcher(scripts)
    result = launcher_diagnostics(
        path_value=os.pathsep.join([str(scripts), str(scripts)]),
        scripts_dir=scripts,
        platform_name="nt",
        pathext=".EXE;.CMD",
    )

    assert result["launcher_count"] == 1
    assert result["multiple_launchers"] is False
    assert result["resolved_to_current_environment"] is True


def test_launcher_diagnostics_detects_conflicting_launchers_without_paths(tmp_path):
    stale = tmp_path / "stale"
    current = tmp_path / "current"
    _make_launcher(stale)
    _make_launcher(current)
    result = launcher_diagnostics(
        path_value=os.pathsep.join([str(stale), str(current)]),
        scripts_dir=current,
        platform_name="nt",
        pathext=".EXE;.CMD",
    )

    assert result == {
        "launcher_found": True,
        "launcher_count": 2,
        "multiple_launchers": True,
        "resolved_to_current_environment": False,
    }
    rendered = json.dumps(result)
    assert str(stale) not in rendered
    assert str(current) not in rendered
```

Extend `tests/test_doctor.py`:

```python
def test_doctor_includes_path_free_launcher_diagnostics():
    result = doctor()

    assert set(result["launcher"]) == {
        "launcher_found",
        "launcher_count",
        "multiple_launchers",
        "resolved_to_current_environment",
    }
    assert all(not isinstance(value, str) for value in result["launcher"].values())
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_launcher.py tests/test_doctor.py -v`

Expected: collection FAIL because `smartmoney_cub_harness.launcher` does not exist.

- [ ] **Step 3: Implement deterministic launcher discovery**

Create `src/smartmoney_cub_harness/launcher.py` with:

```python
from __future__ import annotations

import os
import sysconfig
from pathlib import Path


def launcher_diagnostics(
    path_value: str | None = None,
    scripts_dir: str | Path | None = None,
    platform_name: str | None = None,
    pathext: str | None = None,
) -> dict[str, bool | int]:
    path_value = os.environ.get("PATH", "") if path_value is None else path_value
    scripts_path = Path(sysconfig.get_path("scripts") if scripts_dir is None else scripts_dir)
    platform_name = os.name if platform_name is None else platform_name
    if platform_name == "nt":
        raw_extensions = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD") if pathext is None else pathext
        names = [f"smcub{extension.lower()}" for extension in raw_extensions.split(";") if extension]
    else:
        names = ["smcub"]

    launchers: list[Path] = []
    seen: set[str] = set()
    for entry in path_value.split(os.pathsep):
        if not entry:
            continue
        for name in names:
            candidate = Path(entry) / name
            if not candidate.is_file():
                continue
            identity = os.path.normcase(str(candidate.resolve()))
            if identity not in seen:
                seen.add(identity)
                launchers.append(candidate)

    current_scripts = os.path.normcase(str(scripts_path.resolve()))
    first_is_current = bool(launchers) and os.path.normcase(str(launchers[0].parent.resolve())) == current_scripts
    return {
        "launcher_found": bool(launchers),
        "launcher_count": len(launchers),
        "multiple_launchers": len(launchers) > 1,
        "resolved_to_current_environment": first_is_current,
    }
```

Import `launcher_diagnostics` in `cli.py` and add:

```python
"launcher": launcher_diagnostics(),
```

to the doctor payload.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `python -m pytest tests/test_launcher.py tests/test_doctor.py -v`

Expected: all selected tests PASS.

Run: `python -m smartmoney_cub_harness.cli doctor`

Expected: exit 0, existing safety fields remain present, and `launcher` contains only booleans and an integer.

- [ ] **Step 5: Commit the independently working diagnostic feature**

```text
git add src/smartmoney_cub_harness/launcher.py src/smartmoney_cub_harness/cli.py tests/test_launcher.py tests/test_doctor.py
git commit -m "Expose safe CLI launcher conflict diagnostics"
```

The actual commit must include Lore trailers and focused verification evidence.

---

### Task 3: Installation, Upgrade, and Release Documentation

**Files:**
- Create: `docs/versioning.md`
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `tests/test_readme_commands.py`

**Interfaces:**
- Produces: documented Windows and POSIX isolated installation commands.
- Produces: pipx as the preferred post-PyPI end-user installation and upgrade path.
- Produces: explicit upgrade behavior for editable Git, pip, pipx, and copied source.

- [ ] **Step 1: Write failing documentation contract tests**

Extend `tests/test_readme_commands.py`:

```python
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
    assert "does not update automatically" in policy


def test_local_virtual_environment_is_ignored():
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert ".venv/" in gitignore
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_readme_commands.py -v`

Expected: FAIL because the new commands, policy file, and `.venv/` ignore rule do not exist.

- [ ] **Step 3: Add exact installation and upgrade documentation**

Add `.venv/` to `.gitignore`.

Update both README files with:

```text
Windows repository setup:
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\smcub.exe --version

POSIX repository setup:
python -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
./.venv/bin/smcub --version

Preferred end-user setup after PyPI publication:
pipx install smartmoney-cub-harness
pipx upgrade smartmoney-cub-harness
```

State that a global `smcub` may resolve to a different Python environment, and recommend `smcub doctor` plus `smcub --version` after installation. Link `docs/versioning.md`.

Create `docs/versioning.md` covering:

- SemVer meanings and `0.1.1` as the current prepared patch release;
- exact Git, pip, pipx, and copied-source upgrade commands;
- the sentence `Existing installations do not update automatically.`;
- `vX.Y.Z` tag, GitHub Release, PyPI Trusted Publishing, and clean pipx verification order;
- prohibition on reusing versions, embedded credentials, background update checks, and self-update mutation.

- [ ] **Step 4: Run documentation tests and verify GREEN**

Run: `python -m pytest tests/test_readme_commands.py -v`

Expected: all selected tests PASS.

- [ ] **Step 5: Commit the independently reviewable documentation**

```text
git add .gitignore README.md README.zh-CN.md docs/versioning.md tests/test_readme_commands.py
git commit -m "Give CLI users a reliable upgrade path"
```

The actual commit must include Lore trailers and the documentation test evidence.

---

### Task 4: Full Release Readiness Verification

**Files:**
- Verify only; modify earlier files only if a failing check exposes an in-scope defect.

**Interfaces:**
- Consumes: `__version__ == "0.1.1"`, `launcher_diagnostics(...)`, updated READMEs, and `docs/versioning.md`.
- Produces: fresh evidence that source tests, wheel metadata, doctor, privacy audit, and toy loop all satisfy the design.

- [ ] **Step 1: Run static diff and repository checks**

Run: `git diff main...HEAD --check`

Expected: exit 0 with no whitespace errors.

Run: `git status -sb`

Expected: only the intended branch and no unstaged source changes before final verification.

- [ ] **Step 2: Run the complete test suite**

Run: `python -m pytest -q`

Expected: exit 0 with all tests passing.

- [ ] **Step 3: Build and inspect the wheel**

Run: `python -m pip wheel . --no-deps --wheel-dir tmp/release-wheel`

Expected: exit 0 and a `smartmoney_cub_harness-0.1.1-*.whl` artifact.

- [ ] **Step 4: Verify installed CLI behavior through the current interpreter**

Run: `python -m smartmoney_cub_harness.cli --version`

Expected: exactly `smcub 0.1.1`.

Run: `python -m smartmoney_cub_harness.cli doctor`

Expected: JSON contains `version: 0.1.1`, launcher diagnostics, no exposed paths after redaction, and `READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE`.

Run: `python -m smartmoney_cub_harness.cli privacy-audit`

Expected: network, telemetry, and upload are false and the safety declaration is present.

Run: `python -m smartmoney_cub_harness.cli loop --preset toy --agent-trigger "自进化"`

Expected: status is ok, `champion_mutated` is false, network and telemetry are false, and the safety declaration is present.

- [ ] **Step 5: Inspect the final diff and commit any verification-only correction**

Run: `git diff main...HEAD --stat` and `git diff main...HEAD`.

Expected: changes are limited to the design, plan, version source, CLI diagnostics, tests, ignore rule, and version documentation. If verification required a correction, commit only the affected files with Lore trailers and repeat Steps 1–4.

---

### Task 5: Publish the Reviewed Branch

**Files:**
- No source modifications expected.

**Interfaces:**
- Consumes: clean verified branch `codex/cli-version-management`.
- Produces: pushed remote branch and draft pull request targeting `main`.

- [ ] **Step 1: Confirm authentication and scope**

Run: `gh --version`, `gh auth status`, `git status -sb`, and `git diff main...HEAD --stat`.

Expected: GitHub CLI is installed and authenticated, the worktree is clean, and only intended changes are present.

- [ ] **Step 2: Push the branch**

Run: `git push -u origin codex/cli-version-management`.

Expected: exit 0 and upstream tracking configured.

- [ ] **Step 3: Open a draft pull request**

Use the connected GitHub app with:

```text
repository: myc0576/smartmoney-cub-harness
base: main
head: codex/cli-version-management
title: Make CLI versions and upgrades predictable
draft: true
```

The PR body must summarize the single version source, `--version`, privacy-safe doctor diagnostics, pipx/PyPI lifecycle, root cause of the PATH conflict, and exact verification evidence.

- [ ] **Step 4: Report the handoff**

Report branch, commit list, PR URL, full test count, wheel version, manual CLI checks, and the remaining external step: configuring PyPI Trusted Publishing before the first PyPI publication.
