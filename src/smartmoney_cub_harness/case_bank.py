from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from smartmoney_cub_harness.safety import redact
from smartmoney_cub_harness.schemas import CASE_SCHEMA, SAFETY_DECLARATION


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def collect_offline_case(run_dir: str | Path, output_path: str | Path | None = None) -> dict[str, Any]:
    run_path = Path(run_dir)
    decision_path = run_path / "decision.json"
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    outcome_path = next((run_path / name for name in ("outcome_d1.json", "outcome_d3.json") if (run_path / name).exists()), None)
    eval_path = run_path / "eval.json"
    outcome = json.loads(outcome_path.read_text(encoding="utf-8")) if outcome_path else None
    evaluation = json.loads(eval_path.read_text(encoding="utf-8")) if eval_path.exists() else None
    symbol = decision.get("symbol") or (outcome or {}).get("symbol") or "TOY.UNKNOWN"
    case_id = f"offline_{run_path.name}_{symbol}"
    record = {
        "schema": CASE_SCHEMA,
        "case_id": case_id,
        "source": "offline_run",
        "captured_at": _now_iso(),
        "status": "normalized" if outcome else "raw",
        "symbol": symbol,
        "action_label": decision.get("action_label", ""),
        "source_paths": {
            "decision": str(decision_path),
            "outcome": str(outcome_path) if outcome_path else None,
            "evaluation": str(eval_path) if eval_path.exists() else None,
        },
        "payloads": redact({"decision": decision, "outcome": outcome, "evaluation": evaluation}),
        "safety": SAFETY_DECLARATION,
    }
    target = Path(output_path) if output_path else run_path / "case_record.json"
    target.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": record["status"], "case_id": case_id, "case_record_path": str(target), "safety": SAFETY_DECLARATION}
