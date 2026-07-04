from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Any

from smartmoney_cub_harness.manifest import parse_timestamp
from smartmoney_cub_harness.safety import redact
from smartmoney_cub_harness.schemas import (
    DECISION_SCHEMA,
    OUTCOME_SCHEMA,
    PRIVATE_CASE_CSV_SCHEMA,
    SAFETY_DECLARATION,
    VALID_ACTION_LABELS,
    VALID_DATA_QUALITY_FLAGS,
    VALID_HORIZONS,
)

REQUIRED_PRIVATE_CASE_FIELDS = (
    "case_id",
    "decision_time",
    "action_label",
    "thesis",
    "invalidation_price",
    "time_stop",
    "give_up_conditions",
    "data_source",
    "available_at",
    "data_quality_flag",
    "horizon",
    "return_pct",
    "max_adverse_excursion_pct",
    "met_user_pattern",
)

NON_SILENT_LABELS = {"ALERT", "WATCH", "AVOID"}


def fingerprint_file(path: str | Path) -> dict[str, Any]:
    input_path = Path(path).expanduser().resolve()
    digest = hashlib.sha256()
    with input_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = input_path.stat()
    return redact(
        {
            "path": str(input_path),
            "name": input_path.name,
            "sha256": digest.hexdigest(),
            "bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "safety": SAFETY_DECLARATION,
        }
    )


def _required_header_errors(fieldnames: list[str] | None) -> list[str]:
    fields = set(fieldnames or [])
    return [f"missing_column:{field}" for field in REQUIRED_PRIVATE_CASE_FIELDS if field not in fields]


def _parse_float(value: str, field: str, row_number: int, errors: list[str]) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        errors.append(f"row_{row_number}:invalid_float:{field}")
        return 0.0


def _parse_bool(value: str, field: str, row_number: int, errors: list[str]) -> bool:
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    errors.append(f"row_{row_number}:invalid_bool:{field}")
    return False


def _split_give_up_conditions(value: str) -> list[str]:
    raw = str(value or "")
    separators = ["|", ";", "\n"]
    parts = [raw]
    for separator in separators:
        next_parts: list[str] = []
        for part in parts:
            next_parts.extend(part.split(separator))
        parts = next_parts
    return [part.strip() for part in parts if part.strip()]


def _validate_timestamp(value: str, field: str, row_number: int, errors: list[str]) -> str:
    text = str(value or "").strip()
    if parse_timestamp(text) is None:
        errors.append(f"row_{row_number}:invalid_{field}")
    return text


def _normalize_row(row: dict[str, str], row_number: int, errors: list[str]) -> dict[str, Any]:
    case_id = str(row.get("case_id") or "").strip()
    if not case_id:
        errors.append(f"row_{row_number}:missing_case_id")

    action_label = str(row.get("action_label") or "").strip().upper()
    if action_label not in VALID_ACTION_LABELS:
        errors.append(f"row_{row_number}:invalid_action_label:{action_label or 'blank'}")

    data_quality_flag = str(row.get("data_quality_flag") or "").strip().lower()
    if data_quality_flag not in VALID_DATA_QUALITY_FLAGS:
        errors.append(f"row_{row_number}:invalid_data_quality_flag:{data_quality_flag or 'blank'}")

    horizon = str(row.get("horizon") or "").strip().lower()
    if horizon not in VALID_HORIZONS:
        errors.append(f"row_{row_number}:invalid_horizon:{horizon or 'blank'}")

    decision_time = _validate_timestamp(row.get("decision_time", ""), "decision_time", row_number, errors)
    available_at = _validate_timestamp(row.get("available_at", ""), "available_at", row_number, errors)
    decision_dt = parse_timestamp(decision_time)
    available_dt = parse_timestamp(available_at)
    if decision_dt is not None and available_dt is not None and available_dt > decision_dt:
        errors.append(f"row_{row_number}:future_leakage:{case_id or 'blank'}")

    invalidation_value = str(row.get("invalidation_price") or "").strip()
    time_stop = str(row.get("time_stop") or "").strip()
    give_up_conditions = _split_give_up_conditions(row.get("give_up_conditions", ""))
    if action_label in NON_SILENT_LABELS:
        if not invalidation_value:
            errors.append(f"row_{row_number}:missing_invalidation_price")
        if not time_stop:
            errors.append(f"row_{row_number}:missing_time_stop")
        if not give_up_conditions:
            errors.append(f"row_{row_number}:missing_give_up_conditions")

    invalidation_price = _parse_float(invalidation_value or "0", "invalidation_price", row_number, errors)
    return_pct = _parse_float(row.get("return_pct", ""), "return_pct", row_number, errors)
    adverse_pct = _parse_float(
        row.get("max_adverse_excursion_pct", ""),
        "max_adverse_excursion_pct",
        row_number,
        errors,
    )
    met_user_pattern = _parse_bool(row.get("met_user_pattern", ""), "met_user_pattern", row_number, errors)

    symbol = str(row.get("symbol") or case_id or f"PRIVATE.{row_number}").strip()
    decision = {
        "schema": DECISION_SCHEMA,
        "case_id": case_id,
        "symbol": symbol,
        "action_label": action_label,
        "thesis": str(row.get("thesis") or "").strip(),
        "invalidation_price": invalidation_price,
        "time_stop": time_stop,
        "give_up_conditions": give_up_conditions,
        "data_source": str(row.get("data_source") or "").strip(),
        "available_at": available_at,
        "data_quality_flag": data_quality_flag,
        "decision_time": decision_time,
        "safety": SAFETY_DECLARATION,
    }
    outcome = {
        "schema": OUTCOME_SCHEMA,
        "case_id": case_id,
        "symbol": symbol,
        "horizon": horizon,
        "decision_time": decision_time,
        f"{horizon}_return_pct": return_pct,
        "return_pct": return_pct,
        "max_adverse_excursion_pct": adverse_pct,
        "met_user_pattern": met_user_pattern,
        "price_source_type": "private_csv_local",
        "safety": SAFETY_DECLARATION,
    }
    return redact(
        {
            "schema": PRIVATE_CASE_CSV_SCHEMA,
            "case_id": case_id,
            "row_number": row_number,
            "horizon": horizon,
            "decision": decision,
            "outcome": outcome,
            "source": "private_csv_local",
            "network_required": False,
            "telemetry": False,
            "champion_mutated": False,
            "safety": SAFETY_DECLARATION,
        }
    )


def load_private_cases(input_csv: str | Path, *, horizon: str) -> dict[str, Any]:
    if horizon not in VALID_HORIZONS:
        raise ValueError("horizon must be one of: d1, d3")

    input_path = Path(input_csv).expanduser()
    if not input_path.exists():
        raise ValueError(f"input_csv_not_found:{input_path}")

    errors: list[str] = []
    cases: list[dict[str, Any]] = []
    skipped_horizon = 0
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        errors.extend(_required_header_errors(reader.fieldnames))
        if errors:
            return {"ok": False, "errors": errors, "cases": [], "safety": SAFETY_DECLARATION}

        for row_number, row in enumerate(reader, start=2):
            row_errors_before = len(errors)
            normalized = _normalize_row(row, row_number, errors)
            if normalized.get("horizon") != horizon:
                skipped_horizon += 1
                continue
            if len(errors) == row_errors_before:
                cases.append(normalized)

    if not cases and not errors:
        errors.append(f"no_cases_for_horizon:{horizon}")
    return {
        "ok": not errors,
        "errors": errors,
        "cases": cases,
        "case_count": len(cases),
        "skipped_horizon": skipped_horizon,
        "input_fingerprint": fingerprint_file(input_path),
        "network_required": False,
        "telemetry": False,
        "safety": SAFETY_DECLARATION,
    }
