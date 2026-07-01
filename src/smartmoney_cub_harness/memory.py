from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from smartmoney_cub_harness.safety import redact
from smartmoney_cub_harness.schemas import MEMORY_SCHEMA, SAFETY_DECLARATION


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def render_memory_markdown(case_record: dict[str, Any]) -> str:
    record = redact(case_record)
    payloads = record.get("payloads") if isinstance(record.get("payloads"), dict) else {}
    decision = payloads.get("decision") if isinstance(payloads.get("decision"), dict) else {}
    outcome = payloads.get("outcome") if isinstance(payloads.get("outcome"), dict) else {}
    evaluation = payloads.get("evaluation") if isinstance(payloads.get("evaluation"), dict) else {}

    failure_tags = ", ".join(str(item) for item in _as_list(evaluation.get("failure_tags"))) or "none"
    give_up = "; ".join(str(item) for item in _as_list(decision.get("give_up_conditions"))) or "none"
    return "\n".join(
        [
            "# Smartmoney Cub Local Memory",
            "",
            f"schema: {MEMORY_SCHEMA}",
            f"safety: {SAFETY_DECLARATION}",
            "network_required: false",
            "telemetry: false",
            "champion_mutated: false",
            "",
            "## Case",
            "",
            f"- case_id: {record.get('case_id')}",
            f"- source: {record.get('source')}",
            f"- status: {record.get('status')}",
            f"- symbol: {record.get('symbol')}",
            f"- action_label: {record.get('action_label')}",
            "",
            "## Decision Memory",
            "",
            f"- thesis: {decision.get('thesis', 'toy offline observation')}",
            f"- invalidation_price: {decision.get('invalidation_price')}",
            f"- time_stop: {decision.get('time_stop')}",
            f"- give_up_conditions: {give_up}",
            f"- data_source: {decision.get('data_source')}",
            f"- available_at: {decision.get('available_at')}",
            f"- data_quality_flag: {decision.get('data_quality_flag')}",
            "",
            "## Outcome Memory",
            "",
            f"- horizon: {outcome.get('horizon')}",
            f"- d1_return_pct: {outcome.get('d1_return_pct')}",
            f"- d3_return_pct: {outcome.get('d3_return_pct')}",
            f"- max_adverse_excursion_pct: {outcome.get('max_adverse_excursion_pct')}",
            f"- met_user_pattern: {outcome.get('met_user_pattern')}",
            "",
            "## Evaluation Memory",
            "",
            f"- grade: {evaluation.get('grade')}",
            f"- failure_tags: {failure_tags}",
            f"- challenger_only: true",
            f"- champion_mutated: false",
            "",
            "## Privacy Boundary",
            "",
            "- This memory is a local artifact only.",
            "- It contains toy offline data in the public demo.",
            "- It must not contain credentials, cookies, account identifiers, private watchlists, or local absolute paths.",
            "",
        ]
    )


def save_memory_record(case_record: str | Path | dict[str, Any], output_path: str | Path | None = None) -> dict[str, Any]:
    if isinstance(case_record, (str, Path)):
        case_path = Path(case_record)
        record = json.loads(case_path.read_text(encoding="utf-8"))
        target = Path(output_path) if output_path else case_path.with_name("memory.md")
    else:
        record = case_record
        target = Path(output_path) if output_path else Path("memory.md")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_memory_markdown(record), encoding="utf-8")
    return {
        "status": "ok",
        "memory_record_path": str(target),
        "schema": MEMORY_SCHEMA,
        "safety": SAFETY_DECLARATION,
        "champion_mutated": False,
    }
