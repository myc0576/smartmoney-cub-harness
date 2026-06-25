from __future__ import annotations

import json
from typing import Any

from smartmoney_cub_harness.schemas import DECISION_SCHEMA, SAFETY_DECLARATION


def parse_json_stdout(result: dict[str, Any]) -> dict[str, Any] | None:
    stdout = (result.get("stdout") or "").strip()
    if not stdout:
        return None
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def first_candidate(payload: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("selected_candidate", "decision_candidate", "signal_candidate", "observation_candidate"):
        candidate = payload.get(key)
        if isinstance(candidate, dict):
            return candidate
    for key in ("signal_candidates", "top_pool_candidates", "candidates", "observation_candidates"):
        candidates = payload.get(key)
        if not isinstance(candidates, list):
            continue
        for candidate in candidates:
            if isinstance(candidate, dict):
                return candidate
    return None


def candidate_decision_fields(candidate: dict[str, Any], source_name: str, decision_time: str) -> dict[str, Any]:
    symbol = candidate.get("symbol") or candidate.get("code")
    invalidation = candidate.get("invalidation_price") or candidate.get("invalid") or candidate.get("hard_stop")
    fields: dict[str, Any] = {
        "data_source": source_name,
        "available_at": decision_time,
        "data_quality_flag": "ok",
    }
    if symbol:
        fields["symbol"] = str(symbol)
    if invalidation is not None:
        fields["invalidation_price"] = float(invalidation)
        fields["time_stop"] = "D1/D3 review"
        fields["give_up_conditions"] = [
            "observation thesis is no longer supported by recorded evidence",
            f"price below invalidation_price {float(invalidation):.4f}",
        ]
    if candidate.get("thesis"):
        fields["thesis"] = str(candidate["thesis"])
    return fields


def derive_decision(mode: str, results: list[dict[str, Any]], decision_time: str) -> dict[str, Any]:
    failed = [item["name"] for item in results if int(item.get("returncode") or 0) != 0]
    signal_sources = [
        item["name"]
        for item in results
        if int(item.get("returncode") or 0) == 0 and (item.get("stdout") or "").strip()
    ]
    if failed:
        action_label = "ERROR"
    elif signal_sources:
        action_label = "ALERT"
    else:
        action_label = "SILENT"

    decision = {
        "schema": DECISION_SCHEMA,
        "mode": mode,
        "action_label": action_label,
        "signal_sources": signal_sources,
        "failed_sources": failed,
        "safety": SAFETY_DECLARATION,
    }
    if signal_sources:
        decision["data_source"] = signal_sources[0]
        decision["available_at"] = decision_time
        decision["data_quality_flag"] = "ok"
        for result in results:
            if result["name"] not in signal_sources:
                continue
            payload = parse_json_stdout(result)
            if payload is None:
                continue
            candidate = first_candidate(payload)
            if candidate is not None:
                decision.update(candidate_decision_fields(candidate, result["name"], decision_time))
                break
    return decision
