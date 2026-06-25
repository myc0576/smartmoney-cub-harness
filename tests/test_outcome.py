from __future__ import annotations

import json
from pathlib import Path

import pytest

from smartmoney_cub_harness.outcome import build_outcome


def _prices(path: Path) -> Path:
    price_path = path / "prices.json"
    price_path.write_text(
        json.dumps(
            {
                "TOY.CUB": {
                    "20260601": {"close": 10.0, "low": 9.9},
                    "20260602": {"close": 10.5, "low": 9.8, "met_user_pattern": True},
                    "20260604": {"close": 10.8, "low": 9.7, "met_user_pattern": True},
                },
                "TOY.BETA": {
                    "20260601": {"close": 8.0, "low": 7.9},
                    "20260602": {"close": 7.8, "low": 7.5},
                },
            }
        ),
        encoding="utf-8",
    )
    return price_path


def test_build_outcome_writes_d1_price_fields_with_provenance(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "decision.json").write_text(
        json.dumps({"symbol": "TOY.CUB", "decision_time": "2026-06-01T15:30:00+08:00"}),
        encoding="utf-8",
    )

    outcome_path = build_outcome(run_dir, horizon="d1", price_source=_prices(tmp_path))

    outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
    assert outcome["d1_return_pct"] == 5.0
    assert outcome["max_adverse_excursion_pct"] == -2.0
    assert outcome["met_user_pattern"] is True


def test_build_outcome_derives_symbol_from_artifact_candidate(tmp_path: Path):
    run_dir = tmp_path / "run"
    artifact_dir = run_dir / "artifacts"
    artifact_dir.mkdir(parents=True)
    (run_dir / "decision.json").write_text(
        json.dumps({"action_label": "ALERT", "decision_time": "2026-06-01T15:30:00+08:00"}),
        encoding="utf-8",
    )
    (artifact_dir / "toy.stdout.txt").write_text(
        json.dumps({"observation_candidates": [{"symbol": "TOY.CUB"}]}),
        encoding="utf-8",
    )

    outcome_path = build_outcome(run_dir, horizon="d1", price_source=_prices(tmp_path))

    outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
    assert outcome["symbol"] == "TOY.CUB"


def test_build_outcome_rejects_ambiguous_artifact_codes(tmp_path: Path):
    run_dir = tmp_path / "run"
    artifact_dir = run_dir / "artifacts"
    artifact_dir.mkdir(parents=True)
    (run_dir / "decision.json").write_text(
        json.dumps({"action_label": "ALERT", "decision_time": "2026-06-01T15:30:00+08:00"}),
        encoding="utf-8",
    )
    (artifact_dir / "toy.stdout.txt").write_text(
        json.dumps({"context": [{"symbol": "TOY.CUB"}, {"symbol": "TOY.BETA"}]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="ambiguous"):
        build_outcome(run_dir, horizon="d1", price_source=_prices(tmp_path))
