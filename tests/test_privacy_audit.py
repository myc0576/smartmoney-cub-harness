from __future__ import annotations

import json
from pathlib import Path

from smartmoney_cub.privacy_audit import inspect_run_artifacts, privacy_audit
from smartmoney_cub.schemas import SAFETY_DECLARATION


def test_privacy_audit_declares_offline_no_telemetry_no_upload():
    result = privacy_audit()

    assert result["network_required"] is False
    assert result["telemetry"] is False
    assert result["upload"] is False
    assert result["default_data_mode"] == "offline_json_fixtures"
    assert result["execution_integrations"] == "disabled"
    assert result["redaction"] == "enabled"
    assert "real_trades" in result["forbidden_public_data"]
    assert "local_absolute_paths" in result["forbidden_public_data"]
    assert result["safety"] == SAFETY_DECLARATION


def test_inspect_artifacts_reports_missing_and_private_markers(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "decision.json").write_text(
        json.dumps({"safety": SAFETY_DECLARATION, "note": "token=abc"}),
        encoding="utf-8",
    )

    result = inspect_run_artifacts(run_dir)

    assert result["status"] == "needs_review"
    assert "run_manifest.json" in result["missing_required"]
    assert result["private_pattern_hits"]
    assert result["safety"] == SAFETY_DECLARATION

