from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from smartmoney_cub_harness.private_input import REQUIRED_PRIVATE_CASE_FIELDS
from smartmoney_cub_harness.self_evolve import confirm_promotion, run_self_evolve
from smartmoney_cub_harness.schemas import SAFETY_DECLARATION

REPO_ROOT = Path(__file__).resolve().parents[1]


def private_row(index: int, *, return_pct: float = 5.0) -> dict[str, object]:
    return {
        "case_id": f"PRIVATE.CASE{index:03d}",
        "decision_time": f"2026-06-{index:02d}T15:30:00+08:00",
        "action_label": "ALERT",
        "thesis": f"local private pullback observation {index}",
        "invalidation_price": "9.4",
        "time_stop": "D1 review",
        "give_up_conditions": "thesis broken; price below invalidation",
        "data_source": "local_journal_export",
        "available_at": f"2026-06-{index:02d}T15:29:00+08:00",
        "data_quality_flag": "ok",
        "horizon": "d1",
        "return_pct": str(return_pct),
        "max_adverse_excursion_pct": "-1.0",
        "met_user_pattern": "true",
    }


def write_private_csv(path: Path, count: int) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED_PRIVATE_CASE_FIELDS)
        writer.writeheader()
        for index in range(1, count + 1):
            writer.writerow(private_row(index))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_self_evolve_writes_required_artifacts_without_champion_mutation(tmp_path: Path):
    csv_path = tmp_path / "private_cases.csv"
    state_root = tmp_path / "state" / "self_evolve"
    write_private_csv(csv_path, 2)

    summary = run_self_evolve(
        input_csv=csv_path,
        max_iterations=2,
        time_budget_min=1,
        horizon="d1",
        state_root=state_root,
    )
    loop_dir = state_root / summary["loop_id"]

    assert summary["status"] == "ok"
    assert summary["loop_name"] == "private_csv_budgeted_self_evolve_loop"
    assert summary["completed_cases"] == 2
    assert summary["processed_this_run"] == 2
    assert summary["promotion_status"] == "blocked_challenger"
    assert summary["network_required"] is False
    assert summary["telemetry"] is False
    assert summary["champion_mutated"] is False

    for name in (
        "contract.json",
        "loop_state.json",
        "trace.jsonl",
        "self_evolve_report.md",
        "evolution_ledger.jsonl",
        "rule_registry.json",
        "promotion_packet.json",
    ):
        assert (loop_dir / name).exists(), name

    packet = read_json(loop_dir / "promotion_packet.json")
    registry = read_json(loop_dir / "rule_registry.json")
    state = read_json(loop_dir / "loop_state.json")
    trace_text = (loop_dir / "trace.jsonl").read_text(encoding="utf-8")

    assert packet["safety"] == SAFETY_DECLARATION
    assert packet["champion_mutated"] is False
    assert registry["champions"] == {}
    assert state["completed_case_ids"] == ["PRIVATE.CASE001", "PRIVATE.CASE002"]
    assert "planner_contract" in trace_text
    assert "runner_case" in trace_text
    assert "evaluator_gate" in trace_text
    assert "archivist_memory" in trace_text


def test_self_evolve_resume_skips_completed_cases(tmp_path: Path):
    csv_path = tmp_path / "private_cases.csv"
    state_root = tmp_path / "state" / "self_evolve"
    write_private_csv(csv_path, 2)

    first = run_self_evolve(
        input_csv=csv_path,
        max_iterations=1,
        time_budget_min=1,
        horizon="d1",
        state_root=state_root,
    )
    second = run_self_evolve(
        input_csv=csv_path,
        max_iterations=5,
        time_budget_min=1,
        horizon="d1",
        state_root=state_root,
        resume=first["loop_id"],
    )
    loop_dir = state_root / first["loop_id"]
    trace = [json.loads(line) for line in (loop_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines()]
    start_cases = [line for line in trace if line.get("step") == "start_case"]

    assert second["loop_id"] == first["loop_id"]
    assert second["processed_this_run"] == 1
    assert second["completed_cases"] == 2
    assert [line["case_id"] for line in start_cases] == ["PRIVATE.CASE001", "PRIVATE.CASE002"]


def test_promotion_requires_packet_then_explicit_confirmation(tmp_path: Path):
    csv_path = tmp_path / "private_cases.csv"
    state_root = tmp_path / "state" / "self_evolve"
    write_private_csv(csv_path, 20)

    summary = run_self_evolve(
        input_csv=csv_path,
        max_iterations=20,
        time_budget_min=1,
        horizon="d1",
        state_root=state_root,
    )
    loop_dir = state_root / summary["loop_id"]
    registry_before = read_json(loop_dir / "rule_registry.json")

    assert summary["promotion_status"] == "promotion_recommended"
    assert summary["promotion_blockers"] == []
    assert registry_before["champions"] == {}

    result = confirm_promotion(loop_dir / "promotion_packet.json", decision="promote", note="manual approval")
    registry_after = read_json(loop_dir / "rule_registry.json")
    packet_after = read_json(loop_dir / "promotion_packet.json")

    assert result["champion_mutated"] is True
    assert registry_after["champions"]["private-csv-review"] == "private-csv-risk-contract-challenger-v1"
    assert packet_after["human_confirmation"]["decision"] == "promote"
    assert packet_after["champion_mutated"] is True


def test_blocked_promotion_cannot_be_promoted(tmp_path: Path):
    csv_path = tmp_path / "private_cases.csv"
    state_root = tmp_path / "state" / "self_evolve"
    write_private_csv(csv_path, 2)

    summary = run_self_evolve(
        input_csv=csv_path,
        max_iterations=2,
        time_budget_min=1,
        horizon="d1",
        state_root=state_root,
    )
    loop_dir = state_root / summary["loop_id"]

    with pytest.raises(ValueError, match="cannot promote"):
        confirm_promotion(loop_dir / "promotion_packet.json", decision="promote")


def test_self_evolve_cli_command_runs(tmp_path: Path):
    csv_path = tmp_path / "private_cases.csv"
    state_root = tmp_path / "state" / "self_evolve"
    write_private_csv(csv_path, 1)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "smartmoney_cub_harness.cli",
            "self-evolve",
            "--input-csv",
            str(csv_path),
            "--max-iterations",
            "1",
            "--time-budget-min",
            "1",
            "--state-root",
            str(state_root),
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 0, result.stderr
    assert payload["status"] == "ok"
    assert payload["safety"] == SAFETY_DECLARATION
    assert payload["champion_mutated"] is False
