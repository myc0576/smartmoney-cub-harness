from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from smartmoney_cub_harness.evidence_pack import build_evidence_pack, replay_evidence_pack
from smartmoney_cub_harness.schemas import SAFETY_DECLARATION


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _make_run(tmp_path: Path, run_id: str, decision: dict, outcome: dict) -> Path:
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    manifest = {
        "schema": "smartmoney_cub_run_manifest.v1",
        "run_id": run_id,
        "decision_time": "2026-07-10T09:30:00+08:00",
        "mode": "offline",
        "data_sources": [
            {
                "name": "toy_source",
                "fetch_time": "2026-07-10T09:00:00+08:00",
                "available_at": "2026-07-10T09:00:00+08:00",
                "data_quality_flag": "ok",
            }
        ],
        "safety": SAFETY_DECLARATION,
    }
    _write_json(run_dir / "run_manifest.json", manifest)
    _write_json(run_dir / "decision.json", {**decision, "safety": SAFETY_DECLARATION})
    _write_json(run_dir / "outcome_d1.json", {**outcome, "safety": SAFETY_DECLARATION})
    return run_dir


def _alert() -> dict:
    return {
        "action_label": "ALERT",
        "invalidation_price": 9.5,
        "time_stop": "d1_close",
        "give_up_conditions": ["pattern_failed"],
        "data_source": "toy_source",
        "available_at": "2026-07-10T09:00:00+08:00",
        "data_quality_flag": "ok",
    }


def test_evidence_pack_public_api_is_available() -> None:
    assert callable(build_evidence_pack)
    assert callable(replay_evidence_pack)


def test_build_freezes_three_runs_with_hashes_metrics_and_human_gate(tmp_path: Path) -> None:
    samples = [
        _make_run(tmp_path, "sample-useful", _alert(), {"d1_return_pct": 4.0}),
        _make_run(
            tmp_path,
            "sample-false-alert",
            _alert(),
            {"d1_return_pct": -4.0, "max_adverse_excursion_pct": -4.0},
        ),
        _make_run(
            tmp_path,
            "sample-missed",
            {"action_label": "SILENT"},
            {"d1_return_pct": 4.0, "met_user_pattern": True},
        ),
    ]
    output_dir = tmp_path / "evidence"

    result = build_evidence_pack(
        output_dir,
        samples,
        {"rule_id": "toy-rule-v2", "family": "toy-rule", "notes": r"C:\private\notes.txt"},
    )

    saved = json.loads((output_dir / "evidence_pack.json").read_text(encoding="utf-8"))
    assert result == saved
    assert saved["metrics"] == {
        "sample_count": 3,
        "false_alert_rate": 1 / 3,
        "missed_opportunity_rate": 1 / 3,
        "future_leakage_count": 0,
        "risk_contract_violation_rate": 0.0,
    }
    assert saved["failure_count"] == 0
    assert saved["trailing_consecutive_failure_count"] == 0
    assert saved["review_status"] == "challenger"
    assert saved["promotion_gate"] == {
        "eligible_for_human_review": False,
        "human_confirmation_required": True,
        "champion_mutated": False,
        "core_rules_mutated": False,
    }
    expected_paths = {"rule_candidate.json"}
    for sample_id in ("sample-useful", "sample-false-alert", "sample-missed"):
        expected_paths.update(
            {
                f"samples/{sample_id}/run_manifest.json",
                f"samples/{sample_id}/decision.json",
                f"samples/{sample_id}/outcome_d1.json",
                f"samples/{sample_id}/evaluation.json",
            }
        )
    assert set(saved["hashes"]) == expected_paths
    for relative_path, expected_hash in saved["hashes"].items():
        frozen = output_dir / Path(relative_path)
        assert frozen.is_file()
        assert hashlib.sha256(frozen.read_bytes()).hexdigest() == expected_hash
        assert json.loads(frozen.read_text(encoding="utf-8"))["safety"] == SAFETY_DECLARATION
    assert "C:\\private" not in json.dumps(saved)
    assert saved["promotion_gate"]["champion_mutated"] is False


def test_build_overwrites_invalid_safety_on_every_frozen_artifact(tmp_path: Path) -> None:
    sample = _make_run(tmp_path, "sample-wrong-safety", _alert(), {"d1_return_pct": 4.0})
    for filename in ("run_manifest.json", "decision.json", "outcome_d1.json"):
        path = sample / filename
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["safety"] = "WRONG_SAFETY"
        _write_json(path, payload)
    output_dir = tmp_path / "evidence"

    pack = build_evidence_pack(
        output_dir,
        [sample],
        {"rule_id": "toy-rule", "family": "toy", "safety": "WRONG_SAFETY"},
    )

    for relative_path in pack["hashes"]:
        frozen = json.loads((output_dir / relative_path).read_text(encoding="utf-8"))
        assert frozen["safety"] == SAFETY_DECLARATION


def test_replay_clean_pack_verifies_frozen_results(tmp_path: Path) -> None:
    sample = _make_run(tmp_path, "sample-clean", _alert(), {"d1_return_pct": 4.0})
    output_dir = tmp_path / "evidence"
    built = build_evidence_pack(output_dir, [sample], {"rule_id": "toy-rule", "family": "toy"})

    replay = replay_evidence_pack(output_dir)

    saved = json.loads((output_dir / "replay_report.json").read_text(encoding="utf-8"))
    assert replay == saved
    assert replay["evidence_status"] == "verified"
    assert replay["metrics"] == built["metrics"]
    assert replay["failure_count"] == built["failure_count"]
    assert replay["trailing_consecutive_failure_count"] == built["trailing_consecutive_failure_count"]
    assert replay["safety"] == SAFETY_DECLARATION


@pytest.mark.parametrize(
    ("failure_count", "expected_status"),
    [(1, "pending_review"), (2, "pending_review"), (3, "blocked")],
)
def test_replay_clean_pack_status_reflects_recomputed_failures(
    tmp_path: Path, failure_count: int, expected_status: str
) -> None:
    samples = [
        _make_run(tmp_path, f"failed-{index}", {"action_label": "ERROR"}, {})
        for index in range(failure_count)
    ]
    output_dir = tmp_path / "evidence"
    build_evidence_pack(output_dir, samples, {"rule_id": "toy-rule", "family": "toy"})

    replay = replay_evidence_pack(output_dir)

    assert replay["hash_mismatches"] == []
    assert replay["result_mismatches"] == []
    assert replay["failure_count"] == failure_count
    assert replay["trailing_consecutive_failure_count"] == failure_count
    assert replay["evidence_status"] == expected_status
    assert replay["promotion_gate"]["eligible_for_human_review"] is False


def test_replay_never_qualifies_threshold_passing_failed_samples(tmp_path: Path) -> None:
    failed = _make_run(tmp_path, "failed-first", {"action_label": "ERROR"}, {})
    successful = [
        _make_run(tmp_path, f"successful-{index}", _alert(), {"d1_return_pct": 4.0})
        for index in range(19)
    ]
    output_dir = tmp_path / "evidence"
    build_evidence_pack(
        output_dir,
        [failed, *successful],
        {"rule_id": "toy-rule", "family": "toy"},
    )

    replay = replay_evidence_pack(output_dir)

    assert replay["metrics"] == {
        "sample_count": 20,
        "false_alert_rate": 0.0,
        "missed_opportunity_rate": 0.0,
        "future_leakage_count": 0,
        "risk_contract_violation_rate": 0.0,
    }
    assert replay["failure_count"] == 1
    assert replay["trailing_consecutive_failure_count"] == 0
    assert replay["evidence_status"] == "pending_review"
    assert replay["promotion_gate"]["eligible_for_human_review"] is False


def test_replay_detects_tampered_frozen_file(tmp_path: Path) -> None:
    sample = _make_run(tmp_path, "sample-tampered", _alert(), {"d1_return_pct": 4.0})
    output_dir = tmp_path / "evidence"
    build_evidence_pack(output_dir, [sample], {"rule_id": "toy-rule", "family": "toy"})
    decision_path = output_dir / "samples" / "sample-tampered" / "decision.json"
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    decision["action_label"] = "SILENT"
    _write_json(decision_path, decision)

    replay = replay_evidence_pack(output_dir)

    assert replay["evidence_status"] == "pending_review"
    assert "samples/sample-tampered/decision.json" in replay["hash_mismatches"]
    assert "evaluation:sample-tampered" in replay["result_mismatches"]
    assert replay["promotion_gate"]["champion_mutated"] is False


def test_build_uses_pending_and_blocked_failure_transitions(tmp_path: Path) -> None:
    failed_samples = [
        _make_run(tmp_path, f"failed-{index}", {"action_label": "ERROR"}, {}) for index in range(3)
    ]

    pending = build_evidence_pack(
        tmp_path / "pending", failed_samples[:2], {"rule_id": "pending", "family": "toy"}
    )
    blocked = build_evidence_pack(
        tmp_path / "blocked", failed_samples, {"rule_id": "blocked", "family": "toy"}
    )

    assert pending["failure_count"] == 2
    assert pending["trailing_consecutive_failure_count"] == 2
    assert pending["review_status"] == "pending_review"
    assert blocked["failure_count"] == 3
    assert blocked["trailing_consecutive_failure_count"] == 3
    assert blocked["review_status"] == "blocked"


def test_build_rejects_zero_samples(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least one sample"):
        build_evidence_pack(tmp_path / "empty", [], {"rule_id": "empty", "family": "toy"})
