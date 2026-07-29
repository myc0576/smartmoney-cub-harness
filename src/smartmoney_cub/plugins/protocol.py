from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from smartmoney_cub.plugins.environment import validate_symbol
from smartmoney_cub.schemas import (
    ANALYSIS_REQUEST_SCHEMA,
    FORECAST_EVIDENCE_PACKET_SCHEMA,
    MARKET_DATA_PACKET_SCHEMA,
    MULTI_PLUGIN_ANALYSIS_SCHEMA,
    SAFETY_DECLARATION,
    VALID_ANALYSIS_HORIZONS,
    VALID_TARGET_TYPES,
)

ACTIONABILITY = "review_only"

REQUIRED_EVIDENCE_FIELDS = (
    "schema",
    "plugin_id",
    "plugin_version",
    "upstream_repo",
    "upstream_license",
    "target",
    "as_of",
    "horizon",
    "generated_at",
    "input_data_hash",
    "data_sources",
    "data_quality",
    "model_identifier",
    "forecast",
    "evidence",
    "counter_evidence",
    "risks",
    "missing_information",
    "limitations",
    "raw_output_hash",
    "output_kind",
    "actionability",
    "safety",
)

# What kind of output a plugin produced. Used so reviewers can tell numeric
# models, LLM narratives, and uncalibrated scores apart.
OUTPUT_KINDS = frozenset(
    {
        "numeric_model_forecast",
        "llm_interpretation",
        "uncalibrated_score",
        "market_data",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_of(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_analysis_request(
    *,
    symbol: str,
    target_type: str,
    market: str = "CN",
    horizon: str = "d5",
    data_provider: str | None = None,
    plugins: list[str] | None = None,
    as_of: str | None = None,
    network_allowed: bool = False,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_symbol(symbol)
    if target_type not in VALID_TARGET_TYPES:
        raise ValueError(f"invalid target type: {target_type}")
    if horizon not in VALID_ANALYSIS_HORIZONS:
        raise ValueError(f"invalid horizon: {horizon}")
    return {
        "schema": ANALYSIS_REQUEST_SCHEMA,
        "target": {"symbol": symbol, "type": target_type, "market": market},
        "as_of": as_of or _utc_now(),
        "horizon": horizon,
        "data_provider": data_provider,
        "plugins": list(plugins or []),
        "network_allowed": bool(network_allowed),
        "options": dict(options or {}),
        "actionability": ACTIONABILITY,
        "safety": SAFETY_DECLARATION,
    }


def validate_analysis_request(request: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if request.get("schema") != ANALYSIS_REQUEST_SCHEMA:
        errors.append("invalid_schema")
    target = request.get("target")
    if not isinstance(target, dict):
        errors.append("missing_target")
    else:
        if target.get("type") not in VALID_TARGET_TYPES:
            errors.append(f"invalid_target_type:{target.get('type')}")
        symbol = target.get("symbol")
        try:
            validate_symbol(str(symbol))
        except Exception:
            errors.append("invalid_symbol")
    if request.get("horizon") not in VALID_ANALYSIS_HORIZONS:
        errors.append(f"invalid_horizon:{request.get('horizon')}")
    if request.get("safety") != SAFETY_DECLARATION:
        errors.append("missing_or_invalid_safety_declaration")
    return {"ok": not errors, "errors": errors}


def build_market_data_packet(
    *,
    symbol: str,
    target_type: str,
    exchange: str,
    interval: str,
    adjustment: str,
    source: str,
    as_of: str,
    available_at: str,
    bars: list[dict[str, Any]],
    data_quality_flag: str = "ok",
    missing_fields: list[str] | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": MARKET_DATA_PACKET_SCHEMA,
        "symbol": symbol,
        "target_type": target_type,
        "exchange": exchange,
        "as_of": as_of,
        "interval": interval,
        "adjustment": adjustment,
        "source": source,
        "fetch_time": _utc_now(),
        "available_at": available_at,
        "data_quality_flag": data_quality_flag,
        "bars": bars,
        "bar_count": len(bars),
        "missing_fields": list(missing_fields or []),
        "provenance": dict(provenance or {}),
        "safety": SAFETY_DECLARATION,
    }


def build_evidence_packet(
    *,
    plugin_id: str,
    plugin_version: str,
    upstream_repo: str,
    upstream_license: str,
    target: dict[str, Any],
    as_of: str,
    horizon: str,
    input_data: Any,
    data_sources: list[dict[str, Any]],
    data_quality: str,
    model_identifier: str,
    forecast: dict[str, Any],
    evidence: list[str],
    output_kind: str,
    counter_evidence: list[str] | None = None,
    risks: list[str] | None = None,
    missing_information: list[str] | None = None,
    limitations: list[str] | None = None,
    raw_output: Any = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if output_kind not in OUTPUT_KINDS:
        raise ValueError(f"invalid output kind: {output_kind}")
    packet: dict[str, Any] = {
        "schema": FORECAST_EVIDENCE_PACKET_SCHEMA,
        "plugin_id": plugin_id,
        "plugin_version": plugin_version,
        "upstream_repo": upstream_repo,
        "upstream_license": upstream_license,
        "target": target,
        "as_of": as_of,
        "horizon": horizon,
        "generated_at": _utc_now(),
        "input_data_hash": sha256_of(input_data),
        "data_sources": data_sources,
        "data_quality": data_quality,
        "model_identifier": model_identifier,
        "forecast": forecast,
        "evidence": list(evidence),
        "counter_evidence": list(counter_evidence or []),
        "risks": list(risks or []),
        "missing_information": list(missing_information or []),
        "limitations": list(limitations or []),
        "raw_output_hash": sha256_of(raw_output if raw_output is not None else forecast),
        "output_kind": output_kind,
        "actionability": ACTIONABILITY,
        "safety": SAFETY_DECLARATION,
    }
    if extra:
        for key, value in extra.items():
            packet.setdefault(key, value)
    return packet


def validate_evidence_packet(packet: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    for field in REQUIRED_EVIDENCE_FIELDS:
        if field not in packet:
            errors.append(f"missing_{field}")
    if packet.get("schema") != FORECAST_EVIDENCE_PACKET_SCHEMA:
        errors.append("invalid_schema")
    if packet.get("safety") != SAFETY_DECLARATION:
        errors.append("missing_or_invalid_safety_declaration")
    if packet.get("actionability") != ACTIONABILITY:
        errors.append("invalid_actionability")
    if "output_kind" in packet and packet.get("output_kind") not in OUTPUT_KINDS:
        errors.append(f"invalid_output_kind:{packet.get('output_kind')}")
    return {"ok": not errors, "errors": errors}


def _direction_of(packet: dict[str, Any]) -> str:
    forecast = packet.get("forecast") or {}
    direction = forecast.get("direction")
    if direction in ("up", "down", "flat", "mixed"):
        return str(direction)
    return "unstated"


def build_multi_plugin_analysis(
    request: dict[str, Any],
    packets: list[dict[str, Any]],
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Aggregate per-plugin packets without blending or averaging them.

    Each plugin's packet is preserved verbatim. The aggregation layer only
    summarizes agreements, conflicts, and gaps. It never invents a calibrated
    "probability of rising" that no plugin actually produced.
    """

    directions: dict[str, str] = {}
    numeric: list[str] = []
    llm: list[str] = []
    uncalibrated: list[str] = []
    quantile_plugins: list[str] = []
    for packet in packets:
        plugin_id = str(packet.get("plugin_id", "unknown"))
        directions[plugin_id] = _direction_of(packet)
        kind = packet.get("output_kind")
        if kind == "numeric_model_forecast":
            numeric.append(plugin_id)
        elif kind == "llm_interpretation":
            llm.append(plugin_id)
        elif kind == "uncalibrated_score":
            uncalibrated.append(plugin_id)
        forecast = packet.get("forecast") or {}
        if isinstance(forecast.get("quantiles"), dict) and forecast["quantiles"]:
            quantile_plugins.append(plugin_id)

    stated = {p: d for p, d in directions.items() if d != "unstated"}
    unique_directions = set(stated.values())
    agreements: list[str] = []
    conflicts: list[str] = []
    if len(stated) >= 2 and len(unique_directions) == 1:
        agreements.append(
            f"plugins {sorted(stated)} independently lean '{next(iter(unique_directions))}'"
        )
    elif len(unique_directions) > 1:
        conflicts.append(
            "plugins disagree on direction: "
            + ", ".join(f"{p}={d}" for p, d in sorted(stated.items()))
        )

    missing: list[str] = []
    for packet in packets:
        for item in packet.get("missing_information", []) or []:
            missing.append(f"{packet.get('plugin_id')}: {item}")

    return {
        "schema": MULTI_PLUGIN_ANALYSIS_SCHEMA,
        "request": request,
        "generated_at": _utc_now(),
        "plugin_results": packets,
        "plugin_errors": list(errors or []),
        "summary": {
            "directions_by_plugin": directions,
            "agreements": agreements,
            "conflicts": conflicts,
            "missing_information": missing,
            "numeric_model_outputs": numeric,
            "llm_interpretation_outputs": llm,
            "uncalibrated_score_outputs": uncalibrated,
            "plugins_with_quantile_intervals": quantile_plugins,
            "calibrated_probability_available": False,
            "note": (
                "Each plugin result is independent evidence. No blending, "
                "averaging, or synthetic probability is applied."
            ),
        },
        "review_followups": {
            "d1_outcome_fields": ["realized_return_d1", "direction_hit_d1"],
            "d3_outcome_fields": ["realized_return_d3", "direction_hit_d3"],
            "d5_outcome_fields": ["realized_return_d5", "direction_hit_d5", "quantile_coverage_d5"],
        },
        "actionability": ACTIONABILITY,
        "safety": SAFETY_DECLARATION,
    }
