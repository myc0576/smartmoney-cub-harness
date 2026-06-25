from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from smartmoney_cub_harness.schemas import LEDGER_SCHEMA, SAFETY_DECLARATION


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def append_ledger_event(path: str | Path, event: str, payload: dict[str, Any]) -> dict[str, Any]:
    ledger_path = Path(path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "schema": LEDGER_SCHEMA,
        "ledger_id": uuid.uuid4().hex,
        "event": event,
        "created_at": _now_iso(),
        "safety": SAFETY_DECLARATION,
        **payload,
    }
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    return {**entry, "ledger_path": str(ledger_path)}


def read_ledger(path: str | Path) -> list[dict[str, Any]]:
    ledger_path = Path(path)
    if not ledger_path.exists():
        return []
    return [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
