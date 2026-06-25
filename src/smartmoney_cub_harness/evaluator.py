from __future__ import annotations

from typing import Any

from smartmoney_cub_harness.schemas import REQUIRED_ALERT_DECISION_FIELDS, SAFETY_DECLARATION


def _return_pct(outcome: dict[str, Any]) -> float:
    for key in ("d1_return_pct", "d3_return_pct", "return_pct"):
        if key in outcome:
            return float(outcome.get(key) or 0)
    return 0.0


def evaluate_decision(decision: dict[str, Any], outcome: dict[str, Any]) -> dict[str, Any]:
    action_label = str(decision.get("action_label", "")).upper()
    failure_tags: list[str] = []
    scores = {
        "valid_contract": 1,
        "false_alert": 0,
        "missed_opportunity": 0,
        "risk_contract_violation": 0,
    }

    if decision.get("safety") != SAFETY_DECLARATION:
        failure_tags.append("missing_or_invalid_safety_declaration")

    if action_label == "SILENT":
        if outcome.get("met_user_pattern") is True and _return_pct(outcome) >= 3:
            scores["missed_opportunity"] = 1
            return {
                "grade": "missed_opportunity",
                "failure_tags": ["silent_on_valid_pattern", *failure_tags],
                "scores": scores,
                "safety": SAFETY_DECLARATION,
            }
        return {"grade": "true_silent", "failure_tags": failure_tags, "scores": scores, "safety": SAFETY_DECLARATION}

    if action_label == "ERROR":
        return {
            "grade": "not_evaluated",
            "failure_tags": ["source_error", *failure_tags],
            "scores": scores,
            "safety": SAFETY_DECLARATION,
        }

    for field in REQUIRED_ALERT_DECISION_FIELDS:
        value = decision.get(field)
        if value in (None, "", []):
            failure_tags.append(f"missing_{field}")

    if failure_tags:
        scores["valid_contract"] = 0
        scores["risk_contract_violation"] = 1
        return {"grade": "invalid", "failure_tags": failure_tags, "scores": scores, "safety": SAFETY_DECLARATION}

    return_pct = _return_pct(outcome)
    max_adverse = float(outcome.get("max_adverse_excursion_pct") or 0)
    if return_pct < 0 and max_adverse <= -3:
        scores["false_alert"] = 1
        return {
            "grade": "false_alert",
            "failure_tags": ["adverse_without_fast_feedback"],
            "scores": scores,
            "safety": SAFETY_DECLARATION,
        }

    return {"grade": "useful_alert", "failure_tags": failure_tags, "scores": scores, "safety": SAFETY_DECLARATION}
