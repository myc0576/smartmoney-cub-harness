from __future__ import annotations

import csv
from pathlib import Path

from smartmoney_cub_harness.private_input import REQUIRED_PRIVATE_CASE_FIELDS, fingerprint_file, load_private_cases
from smartmoney_cub_harness.safety import REDACTED
from smartmoney_cub_harness.schemas import SAFETY_DECLARATION


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: tuple[str, ...] = REQUIRED_PRIVATE_CASE_FIELDS) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def valid_row(case_id: str = "PRIVATE.CASE001") -> dict[str, object]:
    return {
        "case_id": case_id,
        "decision_time": "2026-06-01T15:30:00+08:00",
        "action_label": "ALERT",
        "thesis": "local private pullback observation",
        "invalidation_price": "9.4",
        "time_stop": "D1 review",
        "give_up_conditions": "thesis broken; price below invalidation",
        "data_source": "local_journal_export",
        "available_at": "2026-06-01T15:29:00+08:00",
        "data_quality_flag": "ok",
        "horizon": "d1",
        "return_pct": "5.0",
        "max_adverse_excursion_pct": "-1.0",
        "met_user_pattern": "true",
    }


def test_load_private_cases_normalizes_valid_csv(tmp_path: Path):
    csv_path = tmp_path / "private_cases.csv"
    write_csv(csv_path, [valid_row()])

    result = load_private_cases(csv_path, horizon="d1")

    assert result["ok"] is True
    assert result["safety"] == SAFETY_DECLARATION
    assert result["case_count"] == 1
    case = result["cases"][0]
    assert case["schema"] == "smartmoney_cub_private_case_csv.v1"
    assert case["decision"]["action_label"] == "ALERT"
    assert case["decision"]["give_up_conditions"] == ["thesis broken", "price below invalidation"]
    assert case["outcome"]["d1_return_pct"] == 5.0
    assert case["network_required"] is False
    assert case["telemetry"] is False


def test_load_private_cases_rejects_missing_required_columns(tmp_path: Path):
    csv_path = tmp_path / "private_cases.csv"
    write_csv(csv_path, [{"case_id": "PRIVATE.CASE001"}], fieldnames=("case_id",))

    result = load_private_cases(csv_path, horizon="d1")

    assert result["ok"] is False
    assert "missing_column:decision_time" in result["errors"]
    assert result["cases"] == []


def test_load_private_cases_rejects_future_leakage(tmp_path: Path):
    csv_path = tmp_path / "private_cases.csv"
    row = valid_row()
    row["available_at"] = "2026-06-01T15:31:00+08:00"
    write_csv(csv_path, [row])

    result = load_private_cases(csv_path, horizon="d1")

    assert result["ok"] is False
    assert "row_2:future_leakage:PRIVATE.CASE001" in result["errors"]


def test_load_private_cases_rejects_missing_non_silent_risk_contract(tmp_path: Path):
    csv_path = tmp_path / "private_cases.csv"
    row = valid_row()
    row["invalidation_price"] = ""
    row["time_stop"] = ""
    row["give_up_conditions"] = ""
    write_csv(csv_path, [row])

    result = load_private_cases(csv_path, horizon="d1")

    assert result["ok"] is False
    assert "row_2:missing_invalidation_price" in result["errors"]
    assert "row_2:missing_time_stop" in result["errors"]
    assert "row_2:missing_give_up_conditions" in result["errors"]


def test_fingerprint_redacts_private_local_path(tmp_path: Path):
    csv_path = tmp_path / "private_cases.csv"
    write_csv(csv_path, [valid_row()])

    result = fingerprint_file(csv_path)

    assert result["safety"] == SAFETY_DECLARATION
    assert result["sha256"]
    assert result["path"] == REDACTED
    assert str(csv_path) not in str(result)
