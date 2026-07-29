from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from smartmoney_cub.safety import redact
from smartmoney_cub.schemas import SAFETY_DECLARATION, SELF_EVOLVE_STATE_SCHEMA


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def state_path(loop_dir: str | Path) -> Path:
    return Path(loop_dir) / "loop_state.json"


def progress_path(loop_dir: str | Path) -> Path:
    return Path(loop_dir) / "progress.md"


def initial_state(loop_id: str, *, max_iterations: int, horizon: str) -> dict[str, Any]:
    created_at = now_iso()
    return {
        "schema": SELF_EVOLVE_STATE_SCHEMA,
        "loop_id": loop_id,
        "status": "initialized",
        "created_at": created_at,
        "updated_at": created_at,
        "horizon": horizon,
        "max_iterations": max_iterations,
        "current_stage": "initialized",
        "restart_cursor": None,
        "completed_case_ids": [],
        "failed_case_ids": [],
        "last_artifact_paths": {},
        "network_required": False,
        "telemetry": False,
        "champion_mutated": False,
        "safety": SAFETY_DECLARATION,
    }


def load_state(loop_dir: str | Path) -> dict[str, Any]:
    path = state_path(loop_dir)
    if not path.exists():
        raise ValueError(f"missing_loop_state:{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(loop_dir: str | Path, state: dict[str, Any]) -> dict[str, Any]:
    path = state_path(loop_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(state)
    payload["schema"] = SELF_EVOLVE_STATE_SCHEMA
    payload["updated_at"] = now_iso()
    payload["safety"] = SAFETY_DECLARATION
    payload["network_required"] = False
    payload["telemetry"] = False
    payload["champion_mutated"] = bool(payload.get("champion_mutated", False))
    path.write_text(json.dumps(redact(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def append_progress(loop_dir: str | Path, *, stage: str, status: str, message: str) -> None:
    path = progress_path(loop_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = f"- {now_iso()} | {stage} | {status} | {message}\n"
    if not path.exists():
        path.write_text(
            "# Smartmoney Cub Self-Evolve Progress\n\n"
            f"safety: {SAFETY_DECLARATION}\n"
            "network_required: false\n"
            "telemetry: false\n"
            "champion_mutated: false\n\n",
            encoding="utf-8",
        )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(str(redact(line)))


def mark_stage(
    loop_dir: str | Path,
    state: dict[str, Any],
    *,
    stage: str,
    status: str,
    message: str,
    artifact_paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    next_state = dict(state)
    next_state["status"] = status
    next_state["current_stage"] = stage
    if artifact_paths:
        last_paths = dict(next_state.get("last_artifact_paths") or {})
        last_paths.update(artifact_paths)
        next_state["last_artifact_paths"] = last_paths
    append_progress(loop_dir, stage=stage, status=status, message=message)
    return write_state(loop_dir, next_state)

