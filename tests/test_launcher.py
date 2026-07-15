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
