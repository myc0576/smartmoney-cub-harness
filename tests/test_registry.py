from __future__ import annotations

import json
from pathlib import Path

from smartmoney_cub_harness.registry import register_candidate


def strong_candidate() -> dict:
    return {
        "rule_id": "toy-rule-v2",
        "family": "toy-rule",
        "metrics": {
            "sample_count": 30,
            "false_alert_rate": 0.1,
            "missed_opportunity_rate": 0.12,
            "future_leakage_count": 0,
            "risk_contract_violation_rate": 0.0,
        },
    }


def test_registry_recommends_promotion_without_champion_overwrite(tmp_path: Path):
    registry_path = tmp_path / "registry.json"

    result = register_candidate(registry_path, strong_candidate())

    saved = json.loads(registry_path.read_text(encoding="utf-8"))
    assert result["status"] == "promotion_recommended"
    assert saved["champions"] == {}
    assert saved["promotion_recommendations"][0]["rule_id"] == "toy-rule-v2"


def test_registry_confirm_promote_updates_champions(tmp_path: Path):
    registry_path = tmp_path / "registry.json"

    result = register_candidate(registry_path, strong_candidate(), confirm_promote=True)

    saved = json.loads(registry_path.read_text(encoding="utf-8"))
    assert result["status"] == "promoted"
    assert saved["champions"]["toy-rule"] == "toy-rule-v2"


def test_registry_candidate_registration_is_idempotent(tmp_path: Path):
    registry_path = tmp_path / "registry.json"
    candidate = strong_candidate()

    register_candidate(registry_path, candidate)
    register_candidate(registry_path, candidate)

    saved = json.loads(registry_path.read_text(encoding="utf-8"))
    assert [item["rule_id"] for item in saved["candidates"]] == ["toy-rule-v2"]
    assert [item["rule_id"] for item in saved["promotion_recommendations"]] == ["toy-rule-v2"]


def test_registry_keeps_weak_candidate_as_challenger(tmp_path: Path):
    registry_path = tmp_path / "registry.json"
    candidate = strong_candidate()
    candidate["metrics"]["sample_count"] = 8

    result = register_candidate(registry_path, candidate)

    assert result["status"] == "challenger"
    assert result["reasons"] == ["sample_count_below_20"]
