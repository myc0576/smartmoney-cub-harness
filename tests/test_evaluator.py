from __future__ import annotations

from smartmoney_cub_harness.evaluator import evaluate_decision
from smartmoney_cub_harness.schemas import SAFETY_DECLARATION


def test_evaluator_flags_missing_risk_controls_for_alert():
    decision = {
        "action_label": "ALERT",
        "symbol": "TOY.CUB",
        "data_source": "toy_strategy",
        "available_at": "2026-06-01T15:30:00+08:00",
        "data_quality_flag": "ok",
        "safety": SAFETY_DECLARATION,
    }
    outcome = {"d1_return_pct": 2.1, "max_adverse_excursion_pct": -1.2}

    result = evaluate_decision(decision, outcome)

    assert result["grade"] == "invalid"
    assert "missing_invalidation_price" in result["failure_tags"]
    assert "missing_time_stop" in result["failure_tags"]
    assert "missing_give_up_conditions" in result["failure_tags"]


def test_evaluator_scores_silent_missed_opportunity():
    decision = {"action_label": "SILENT", "safety": SAFETY_DECLARATION}
    outcome = {"d1_return_pct": 5.2, "max_adverse_excursion_pct": -1.0, "met_user_pattern": True}

    result = evaluate_decision(decision, outcome)

    assert result["grade"] == "missed_opportunity"
    assert result["scores"]["missed_opportunity"] == 1


def test_evaluator_scores_false_alert():
    decision = {
        "action_label": "ALERT",
        "symbol": "TOY.CUB",
        "invalidation_price": 9.4,
        "time_stop": "D1",
        "give_up_conditions": ["invalidated"],
        "data_source": "toy_strategy",
        "available_at": "2026-06-01T15:30:00+08:00",
        "data_quality_flag": "ok",
        "safety": SAFETY_DECLARATION,
    }
    outcome = {"d1_return_pct": -1.5, "max_adverse_excursion_pct": -3.5}

    result = evaluate_decision(decision, outcome)

    assert result["grade"] == "false_alert"
    assert result["scores"]["false_alert"] == 1


def test_evaluator_scores_useful_alert():
    decision = {
        "action_label": "ALERT",
        "symbol": "TOY.CUB",
        "invalidation_price": 9.4,
        "time_stop": "D1",
        "give_up_conditions": ["invalidated"],
        "data_source": "toy_strategy",
        "available_at": "2026-06-01T15:30:00+08:00",
        "data_quality_flag": "ok",
        "safety": SAFETY_DECLARATION,
    }
    outcome = {"d1_return_pct": 4.0, "max_adverse_excursion_pct": -1.0}

    result = evaluate_decision(decision, outcome)

    assert result["grade"] == "useful_alert"
    assert result["scores"]["valid_contract"] == 1
