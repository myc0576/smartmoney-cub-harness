from __future__ import annotations

from datetime import datetime
from typing import Any

from smartmoney_cub_harness.schemas import (
    REQUIRED_MANIFEST_FIELDS,
    REQUIRED_SOURCE_FIELDS,
    SAFETY_DECLARATION,
    VALID_DATA_QUALITY_FLAGS,
)


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def validate_run_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    for field in REQUIRED_MANIFEST_FIELDS:
        if field not in manifest:
            errors.append(f"missing_{field}")

    if manifest.get("safety") != SAFETY_DECLARATION:
        errors.append("missing_or_invalid_safety_declaration")

    decision_time = parse_timestamp(manifest.get("decision_time"))
    if "decision_time" in manifest and decision_time is None:
        errors.append("invalid_decision_time")

    sources = manifest.get("data_sources")
    if sources is None:
        sources = []
    if not isinstance(sources, list):
        errors.append("data_sources_not_list")
        sources = []

    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"invalid_data_source:{index}")
            continue

        name = str(source.get("name") or f"source_{index}")
        for field in REQUIRED_SOURCE_FIELDS:
            if field not in source:
                errors.append(f"missing_{field}:{name}")

        fetch_time = parse_timestamp(source.get("fetch_time"))
        available_at = parse_timestamp(source.get("available_at"))
        if "fetch_time" in source and fetch_time is None:
            errors.append(f"invalid_fetch_time:{name}")
        if "available_at" in source and available_at is None:
            errors.append(f"invalid_available_at:{name}")
        if fetch_time is not None and available_at is not None and fetch_time > available_at:
            errors.append(f"fetch_after_available:{name}")
        if decision_time is not None and available_at is not None and available_at > decision_time:
            errors.append(f"future_leakage:{name}")

        flag = source.get("data_quality_flag")
        if flag in VALID_DATA_QUALITY_FLAGS:
            if flag != "ok":
                warnings.append(f"data_source_{flag}:{name}")
        elif "data_quality_flag" in source:
            errors.append(f"invalid_data_quality_flag:{name}")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "source_count": len(sources),
        "safety": SAFETY_DECLARATION,
    }
