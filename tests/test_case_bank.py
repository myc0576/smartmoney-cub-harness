from __future__ import annotations

import json
from pathlib import Path

from smartmoney_cub_harness.case_bank import collect_offline_case
from smartmoney_cub_harness.schemas import SAFETY_DECLARATION


def test_collect_offline_case_writes_redacted_relative_case_record(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "decision.json").write_text(
        json.dumps(
            {
                "symbol": "TOY.CUB",
                "action_label": "ALERT",
                "thesis": "toy only token=abc C:\\Users\\Trader\\secret.txt",
                "safety": SAFETY_DECLARATION,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "outcome_d1.json").write_text(
        json.dumps({"symbol": "TOY.CUB", "horizon": "d1", "d1_return_pct": 5, "safety": SAFETY_DECLARATION}),
        encoding="utf-8",
    )
    (run_dir / "eval.json").write_text(
        json.dumps({"grade": "useful_alert", "failure_tags": [], "safety": SAFETY_DECLARATION}),
        encoding="utf-8",
    )

    result = collect_offline_case(run_dir)
    record = json.loads((run_dir / "case_record.json").read_text(encoding="utf-8"))

    assert result["status"] == "normalized"
    assert result["safety"] == SAFETY_DECLARATION
    assert record["schema"] == "smartmoney_cub_case_record.v1"
    assert record["source_paths"] == {
        "decision": "decision.json",
        "outcome": "outcome_d1.json",
        "evaluation": "eval.json",
    }
    assert record["network_required"] is False
    assert record["telemetry"] is False
    assert record["champion_mutated"] is False
    assert "abc" not in json.dumps(record, ensure_ascii=False)
    assert "C:\\Users\\Trader" not in json.dumps(record, ensure_ascii=False)
