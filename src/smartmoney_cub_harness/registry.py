from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from smartmoney_cub_harness.schemas import REGISTRY_SCHEMA, SAFETY_DECLARATION


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def empty_registry() -> dict[str, Any]:
    return {
        "schema": REGISTRY_SCHEMA,
        "safety": SAFETY_DECLARATION,
        "updated_at": None,
        "champions": {},
        "candidates": [],
        "promotion_recommendations": [],
    }


def _load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_registry()
    return json.loads(path.read_text(encoding="utf-8"))


def promotion_blockers(metrics: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if int(metrics.get("sample_count") or 0) < 20:
        reasons.append("sample_count_below_20")
    if float(metrics.get("false_alert_rate") or 0) > 0.2:
        reasons.append("false_alert_rate_above_0.2")
    if float(metrics.get("missed_opportunity_rate") or 0) > 0.25:
        reasons.append("missed_opportunity_rate_above_0.25")
    if int(metrics.get("future_leakage_count") or 0) > 0:
        reasons.append("future_leakage_detected")
    if float(metrics.get("risk_contract_violation_rate") or 0) > 0:
        reasons.append("risk_contract_violations_detected")
    return reasons


def register_candidate(
    registry_path: str | Path,
    candidate: dict[str, Any],
    confirm_promote: bool = False,
) -> dict[str, Any]:
    path = Path(registry_path)
    registry = _load_registry(path)
    family = candidate.get("family")
    rule_id = candidate.get("rule_id")
    if not family or not rule_id:
        raise ValueError("candidate requires family and rule_id")

    metrics = candidate.get("metrics") or {}
    reasons = promotion_blockers(metrics)
    eligible = not reasons
    status = "promoted" if eligible and confirm_promote else ("promotion_recommended" if eligible else "challenger")

    stored = deepcopy(candidate)
    stored["candidate_role"] = stored.get("candidate_role") or "challenger"
    stored["promotion_status"] = status
    stored["promotion_reasons"] = reasons
    stored["registered_at"] = _now_iso()
    stored["safety"] = SAFETY_DECLARATION

    registry["schema"] = REGISTRY_SCHEMA
    registry["safety"] = SAFETY_DECLARATION
    registry["candidates"] = [
        item
        for item in registry.get("candidates", [])
        if not (item.get("family") == family and item.get("rule_id") == rule_id)
    ]
    registry.setdefault("candidates", []).append(stored)
    registry.setdefault("champions", {})
    registry["promotion_recommendations"] = [
        item
        for item in registry.get("promotion_recommendations", [])
        if not (item.get("family") == family and item.get("rule_id") == rule_id)
    ]
    if eligible:
        registry["promotion_recommendations"].append(
            {
                "family": family,
                "rule_id": rule_id,
                "registered_at": stored["registered_at"],
                "confirm_required": not confirm_promote,
            }
        )
    if status == "promoted":
        registry["champions"][family] = rule_id
    registry["updated_at"] = stored["registered_at"]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": status, "reasons": reasons, "registry_path": str(path), "safety": SAFETY_DECLARATION}
