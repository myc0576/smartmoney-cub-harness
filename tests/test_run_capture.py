from __future__ import annotations

import json
import sys
from pathlib import Path

from smartmoney_cub_harness.run_capture import capture_run, unique_run_dir
from smartmoney_cub_harness.schemas import SAFETY_DECLARATION


def test_capture_run_writes_manifest_decision_and_artifacts(tmp_path: Path):
    script = tmp_path / "emit.py"
    script.write_text("print('toy context')\n", encoding="utf-8")

    result = capture_run(
        root=tmp_path,
        mode="after-close",
        commands=[{"name": "signal", "argv": [sys.executable, str(script)]}],
        decision_time="2026-06-01T15:30:00+08:00",
    )

    run_dir = Path(result["run_dir"])
    assert result["decision"]["action_label"] == "ALERT"
    assert result["decision"]["signal_sources"] == ["signal"]
    assert result["manifest"]["safety"] == SAFETY_DECLARATION
    assert (run_dir / "run_manifest.json").exists()
    assert (run_dir / "decision.json").exists()
    assert (run_dir / "artifacts" / "signal.stdout.txt").read_text(encoding="utf-8").strip() == "toy context"


def test_capture_run_derives_evaluable_fields_from_json_candidate(tmp_path: Path):
    script = tmp_path / "emit_json.py"
    script.write_text(
        "import json\n"
        "print(json.dumps({'observation_candidates': [{'symbol': 'TOY.CUB', 'invalidation_price': 9.4}]}))\n",
        encoding="utf-8",
    )

    result = capture_run(
        root=tmp_path,
        mode="after-close",
        commands=[{"name": "toy_strategy", "argv": [sys.executable, str(script)]}],
        decision_time="2026-06-01T15:30:00+08:00",
        sandbox=True,
    )

    decision = result["decision"]
    assert "tmp\\sandbox" in result["run_dir"] or "tmp/sandbox" in result["run_dir"]
    assert decision["symbol"] == "TOY.CUB"
    assert decision["invalidation_price"] == 9.4
    assert decision["time_stop"] == "D1/D3 review"
    assert decision["safety"] == SAFETY_DECLARATION


def test_capture_run_marks_empty_stdout_as_silent(tmp_path: Path):
    script = tmp_path / "silent.py"
    script.write_text("", encoding="utf-8")

    result = capture_run(
        root=tmp_path,
        mode="after-close",
        commands=[{"name": "silent", "argv": [sys.executable, str(script)]}],
        decision_time="2026-06-01T15:30:00+08:00",
    )

    assert result["decision"]["action_label"] == "SILENT"


def test_capture_run_marks_command_failure_as_error(tmp_path: Path):
    script = tmp_path / "fail.py"
    script.write_text("raise SystemExit(7)\n", encoding="utf-8")

    result = capture_run(
        root=tmp_path,
        mode="after-close",
        commands=[{"name": "failing", "argv": [sys.executable, str(script)]}],
        decision_time="2026-06-01T15:30:00+08:00",
    )

    assert result["decision"]["action_label"] == "ERROR"
    assert result["decision"]["failed_sources"] == ["failing"]


def test_capture_run_redacts_sensitive_artifacts(tmp_path: Path):
    script = tmp_path / "leak.py"
    local_path = "C:" + "\\Users\\Trader\\private.txt"
    assignment = "to" + "ken=abc "
    script.write_text(f"print({(assignment + local_path)!r})\n", encoding="utf-8")

    result = capture_run(
        root=tmp_path,
        mode="after-close",
        commands=[{"name": "leak", "argv": [sys.executable, str(script)]}],
        decision_time="2026-06-01T15:30:00+08:00",
    )

    run_dir = Path(result["run_dir"])
    saved = (run_dir / "artifacts" / "leak.stdout.txt").read_text(encoding="utf-8")
    assert "abc" not in saved
    assert "Trader" not in saved
    assert "[REDACTED]" in saved
    assert json.loads((run_dir / "artifacts" / "leak.meta.json").read_text(encoding="utf-8"))["argv"]


def test_unique_run_dir_reserves_directory_to_avoid_collisions(tmp_path: Path):
    first = unique_run_dir(tmp_path, "2026-06-01T15:30:00+08:00", "after-close", sandbox=True)
    second = unique_run_dir(tmp_path, "2026-06-01T15:30:00+08:00", "after-close", sandbox=True)

    assert first != second
    assert first.exists()
    assert second.exists()
