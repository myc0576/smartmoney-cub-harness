from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from smartmoney_cub_harness.manifest import parse_timestamp
from smartmoney_cub_harness.schemas import EXTERNAL_ANALYSIS_SCHEMA, SAFETY_DECLARATION

TRADINGAGENTS_LICENSE = "Apache-2.0"
SUPPORTED_SOURCES = {"tradingagents"}

SECTION_ALIASES = {
    "bull case": "bull_case",
    "bull_case": "bull_case",
    "bear case": "bear_case",
    "bear_case": "bear_case",
    "risk notes": "risk_notes",
    "risk_notes": "risk_notes",
    "risks": "risk_notes",
    "external proposal": "external_proposal",
    "external_proposal": "external_proposal",
    "proposal": "external_proposal",
    "confidence": "confidence",
}


def _require_timestamp(value: str, field: str) -> datetime:
    parsed = parse_timestamp(value)
    if parsed is None:
        raise ValueError(f"{field} must be a valid ISO8601 timestamp")
    return parsed


def _assert_comparable(left: datetime, right: datetime) -> None:
    left_has_tz = left.tzinfo is not None and left.tzinfo.utcoffset(left) is not None
    right_has_tz = right.tzinfo is not None and right.tzinfo.utcoffset(right) is not None
    if left_has_tz != right_has_tz:
        raise ValueError("available_at and decision_time must both include timezone offsets or both omit them")


def _normalize_heading(text: str) -> str:
    return re.sub(r"[^a-z0-9_ ]+", "", text.strip().lower()).replace("-", " ")


def extract_report_sections(report_text: str) -> dict[str, Any]:
    sections: dict[str, list[str]] = {
        "bull_case": [],
        "bear_case": [],
        "risk_notes": [],
        "external_proposal": [],
        "confidence": [],
    }
    current: str | None = None

    for line in report_text.splitlines():
        heading = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", line)
        if heading:
            current = SECTION_ALIASES.get(_normalize_heading(heading.group(1)))
            continue
        if current:
            sections[current].append(line)

    flattened = {key: "\n".join(value).strip() for key, value in sections.items()}
    if not flattened["external_proposal"]:
        flattened["external_proposal"] = report_text.strip()
    return flattened


def _artifact_id(source: str, report_text: str, decision_time: str, available_at: str) -> str:
    digest = hashlib.sha256(f"{source}\n{decision_time}\n{available_at}\n{report_text}".encode("utf-8")).hexdigest()
    return f"external_{source}_{digest[:16]}"


def _source_license(source: str) -> str:
    if source == "tradingagents":
        return TRADINGAGENTS_LICENSE
    raise ValueError(f"unsupported source: {source}")


def ingest_external_report(
    *,
    source: str,
    input_path: str | Path,
    decision_time: str,
    output_dir: str | Path = "artifacts/external",
    available_at: str | None = None,
    market: str = "unknown",
    ticker: str = "UNKNOWN",
    source_url: str = "",
    analysis_date: str | None = None,
    generated_at: str | None = None,
    data_quality_notes: str = "Imported from external Markdown report; review evidence only.",
) -> dict[str, Any]:
    source = source.lower()
    if source not in SUPPORTED_SOURCES:
        raise ValueError(f"unsupported source: {source}")

    report_path = Path(input_path)
    report_text = report_path.read_text(encoding="utf-8")
    effective_available_at = available_at or decision_time
    effective_generated_at = generated_at or effective_available_at

    decision_dt = _require_timestamp(decision_time, "decision_time")
    available_dt = _require_timestamp(effective_available_at, "available_at")
    _require_timestamp(effective_generated_at, "generated_at")
    _assert_comparable(available_dt, decision_dt)

    future_ok = available_dt <= decision_dt
    sections = extract_report_sections(report_text)
    artifact_id = _artifact_id(source, report_text, decision_time, effective_available_at)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    raw_report_path = output_path / f"{artifact_id}_raw_report.md"
    artifact_path = output_path / f"{artifact_id}.json"
    raw_report_path.write_text(report_text, encoding="utf-8")

    artifact = {
        "schema_version": EXTERNAL_ANALYSIS_SCHEMA,
        "artifact_id": artifact_id,
        "source_project": source,
        "source_license": _source_license(source),
        "source_url": source_url,
        "market": market,
        "ticker": ticker,
        "analysis_date": analysis_date or decision_dt.date().isoformat(),
        "generated_at": effective_generated_at,
        "available_at": effective_available_at,
        "decision_time": decision_time,
        "raw_report_path": raw_report_path.name,
        "bull_case": sections["bull_case"],
        "bear_case": sections["bear_case"],
        "risk_notes": sections["risk_notes"],
        "external_proposal": sections["external_proposal"],
        "confidence": sections["confidence"] or None,
        "data_quality_notes": data_quality_notes,
        "future_leakage_check": {
            "available_at_lte_decision_time": future_ok,
            "status": "passed" if future_ok else "failed",
            "reason": "available_at <= decision_time"
            if future_ok
            else "available_at is later than decision_time; external report is not admissible review evidence",
        },
        "read_only_invariant": {
            "no_order": True,
            "no_cancel": True,
            "no_trade": True,
            "no_broker_connection": True,
            "champion_mutated": False,
            "network_required": False,
            "telemetry": False,
            "broker_execution": False,
        },
        "safety": SAFETY_DECLARATION,
    }
    artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "status": "ok" if future_ok else "failed",
        "artifact_path": str(artifact_path),
        "raw_report_path": str(raw_report_path),
        "future_leakage_check": artifact["future_leakage_check"],
        "read_only_invariant": artifact["read_only_invariant"],
        "safety": SAFETY_DECLARATION,
    }
