from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from smartmoney_cub_harness.safety import redact
from smartmoney_cub_harness.schemas import SAFETY_DECLARATION

FORBIDDEN_PUBLIC_DATA = [
    "real_trades",
    "real_watchlists",
    "account_identifiers",
    "credentials",
    "cookies",
    "private_notes",
    "local_absolute_paths",
]

REQUIRED_LOOP_ARTIFACTS = [
    "run_manifest.json",
    "decision.json",
    "outcome_d1.json",
    "eval.json",
    "case_record.json",
    "memory.md",
    "evolution_ledger.jsonl",
    "proposed_challenger_rule.json",
    "loop_report.md",
    "trace.jsonl",
]

PRIVATE_TEXT_MARKERS = [
    "cookie=",
    "token=",
    "api_key=",
    "password=",
    "passwd=",
    "secret=",
    "account=",
    "G:\\",
    "C:\\Users\\",
    "/Users/",
    "/home/",
    "/usr/",
    "/opt/",
    "/tmp/",
    "/var/",
]


def privacy_audit() -> dict[str, Any]:
    return {
        "network_required": False,
        "telemetry": False,
        "upload": False,
        "default_data_mode": "offline_json_fixtures",
        "execution_integrations": "disabled",
        "redaction": "enabled",
        "forbidden_public_data": FORBIDDEN_PUBLIC_DATA,
        "safety": SAFETY_DECLARATION,
    }


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def inspect_run_artifacts(run_dir: str | Path) -> dict[str, Any]:
    run_path = Path(run_dir)
    artifacts: dict[str, dict[str, Any]] = {}
    private_hits: list[str] = []
    missing_safety: list[str] = []

    for relative in REQUIRED_LOOP_ARTIFACTS:
        path = run_path / relative
        exists = path.exists()
        artifacts[relative] = {"exists": exists, "bytes": path.stat().st_size if exists else 0}
        if not exists:
            continue
        text = _read_text(path)
        if SAFETY_DECLARATION not in text:
            missing_safety.append(relative)
        lowered = text.lower()
        for marker in PRIVATE_TEXT_MARKERS:
            if marker.lower() in lowered:
                private_hits.append(f"{relative}:{redact(marker)}")

    status = "ok" if all(item["exists"] for item in artifacts.values()) and not private_hits and not missing_safety else "needs_review"
    return {
        "status": status,
        "run_dir": str(redact(str(run_path))),
        "artifacts": artifacts,
        "missing_required": [name for name, item in artifacts.items() if not item["exists"]],
        "missing_safety": missing_safety,
        "private_pattern_hits": private_hits,
        "privacy": privacy_audit(),
        "safety": SAFETY_DECLARATION,
    }


def load_payload_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("payload JSON must be an object")
    return payload
