from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from smartmoney_cub_harness.external_analysis import ingest_external_report
from smartmoney_cub_harness.schemas import SAFETY_DECLARATION

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = str(REPO_ROOT / "src")
FORBIDDEN_EXECUTION_FIELDS = {"order", "broker", "execution", "auto_trade", "cancel_order", "position_execution"}


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC_PATH + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "smartmoney_cub_harness.cli", *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def write_report(path: Path) -> None:
    path.write_text(
        """# TradingAgents Toy Report

## Bull Case
Revenue momentum is improving in the toy fixture.

## Bear Case
Liquidity is thin and the setup can fail quickly.

## Risk Notes
This is toy offline research evidence only.

## External Proposal
The upstream view says buy on strength, sell if invalidated, and keep position sizing small.

## Confidence
0.61
""",
        encoding="utf-8",
    )


def assert_schema_accepts(schema: dict[str, Any], payload: dict[str, Any]) -> None:
    assert set(schema["required"]) <= set(payload)
    if schema.get("additionalProperties") is False:
        assert set(payload) <= set(schema["properties"])
    for key, rule in schema["properties"].items():
        if key not in payload:
            continue
        value = payload[key]
        if "const" in rule:
            assert value == rule["const"]
        if "enum" in rule:
            assert value in rule["enum"]
        if rule.get("type") == "object":
            assert isinstance(value, dict)
            assert_schema_accepts(rule, value)
        elif rule.get("type") == "string":
            assert isinstance(value, str)
        elif isinstance(rule.get("type"), list):
            allowed = set(rule["type"])
            assert (
                ("string" in allowed and isinstance(value, str))
                or ("number" in allowed and isinstance(value, int | float))
                or ("null" in allowed and value is None)
            )


def collect_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for nested in value.values():
            keys.update(collect_keys(nested))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(collect_keys(item))
        return keys
    return set()


def test_external_artifact_matches_schema_and_has_no_execution_fields(tmp_path: Path):
    report_path = tmp_path / "tradingagents_report.md"
    output_dir = tmp_path / "external"
    write_report(report_path)

    result = ingest_external_report(
        source="tradingagents",
        input_path=report_path,
        decision_time="2026-07-05T09:30:00+08:00",
        available_at="2026-07-05T09:20:00+08:00",
        output_dir=output_dir,
        market="CN",
        ticker="TOY.CUB",
    )

    artifact = json.loads(Path(result["artifact_path"]).read_text(encoding="utf-8"))
    schema = json.loads((REPO_ROOT / "schemas" / "external_analysis_artifact.schema.json").read_text(encoding="utf-8"))

    assert_schema_accepts(schema, artifact)
    assert artifact["source_project"] == "tradingagents"
    assert artifact["source_license"] == "Apache-2.0"
    assert "buy on strength" in artifact["external_proposal"]
    assert FORBIDDEN_EXECUTION_FIELDS.isdisjoint(collect_keys(artifact))
    assert (output_dir / artifact["raw_report_path"]).read_text(encoding="utf-8").startswith("# TradingAgents Toy Report")


def test_future_leakage_failed_import_returns_nonzero_and_marks_artifact(tmp_path: Path):
    report_path = tmp_path / "future_report.md"
    output_dir = tmp_path / "external"
    write_report(report_path)

    result = run_cli(
        "ingest-external-report",
        "--source",
        "tradingagents",
        "--input",
        str(report_path),
        "--decision-time",
        "2026-07-05T09:30:00+08:00",
        "--available-at",
        "2026-07-05T09:31:00+08:00",
        "--output",
        str(output_dir),
    )

    assert result.returncode == 2, result.stdout
    artifact_paths = list(output_dir.glob("external_tradingagents_*.json"))
    assert len(artifact_paths) == 1
    artifact = json.loads(artifact_paths[0].read_text(encoding="utf-8"))
    assert artifact["future_leakage_check"] == {
        "available_at_lte_decision_time": False,
        "status": "failed",
        "reason": "available_at is later than decision_time; external report is not admissible review evidence",
    }


def test_successful_import_preserves_read_only_invariant(tmp_path: Path):
    report_path = tmp_path / "safe_report.md"
    output_dir = tmp_path / "external"
    write_report(report_path)

    result = run_cli(
        "ingest-external-report",
        "--source",
        "tradingagents",
        "--input",
        str(report_path),
        "--decision-time",
        "2026-07-05T09:30:00+08:00",
        "--available-at",
        "2026-07-05T09:30:00+08:00",
        "--output",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    artifact = json.loads(next(output_dir.glob("external_tradingagents_*.json")).read_text(encoding="utf-8"))
    assert artifact["safety"] == SAFETY_DECLARATION
    assert artifact["read_only_invariant"]["no_order"] is True
    assert artifact["read_only_invariant"]["no_cancel"] is True
    assert artifact["read_only_invariant"]["no_trade"] is True
    assert artifact["read_only_invariant"]["no_broker_connection"] is True
    assert artifact["read_only_invariant"]["champion_mutated"] is False
    assert artifact["read_only_invariant"]["network_required"] is False
    assert artifact["read_only_invariant"]["telemetry"] is False
    assert artifact["read_only_invariant"]["broker_execution"] is False
