from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from smartmoney_cub_harness.decision import derive_decision
from smartmoney_cub_harness.manifest import validate_run_manifest
from smartmoney_cub_harness.safety import redact
from smartmoney_cub_harness.schemas import MANIFEST_SCHEMA, SAFETY_DECLARATION

SELECTION_SYSTEM_VERSION = "toy_offline_v0.1"
SELECTION_SYSTEM_REFS = ["examples/toy_strategy/README.md"]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned.strip("._") or "command"


def parse_command(value: str) -> dict[str, Any]:
    if "=" in value and not value.split("=", 1)[0].strip().count(" "):
        name, raw_argv = value.split("=", 1)
        argv = [part for part in raw_argv.split("|") if part]
        if not name or not argv:
            raise ValueError("command must include name and at least one argv part")
        return {"name": safe_name(name), "argv": argv}
    argv = shlex.split(value)
    if not argv:
        raise ValueError("command cannot be empty")
    name = Path(argv[1]).stem if len(argv) > 1 else Path(argv[0]).stem
    return {"name": safe_name(name), "argv": argv}


def get_command_preset(name: str) -> list[dict[str, Any]]:
    if name in {"toy", "after-close"}:
        return [
            {
                "name": "toy_strategy",
                "argv": [sys.executable, "examples/toy_strategy/leader_pullback_demo.py"],
            }
        ]
    raise ValueError(f"unknown command preset: {name}")


def normalize_argv(argv: list[str]) -> list[str]:
    if argv and argv[0].lower() in {"python", "python3"}:
        return [sys.executable, *argv[1:]]
    return argv


def run_command(root: Path, command: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    name = safe_name(str(command["name"]))
    argv = normalize_argv([str(part) for part in command["argv"]])
    started_at = now_iso()
    try:
        completed = subprocess.run(
            argv,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return {
            "name": name,
            "argv": argv,
            "started_at": started_at,
            "finished_at": now_iso(),
            "returncode": completed.returncode,
            "stdout": completed.stdout or "",
            "stderr": completed.stderr or "",
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "name": name,
            "argv": argv,
            "started_at": started_at,
            "finished_at": now_iso(),
            "returncode": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or f"command timed out after {timeout_seconds}s",
            "timed_out": True,
        }


def unique_run_dir(root: Path, decision_time: str, mode: str, sandbox: bool = False) -> Path:
    dt = parse_iso(decision_time)
    day = dt.strftime("%Y%m%d")
    stem = f"{dt.strftime('%Y%m%d_%H%M%S')}-{safe_name(mode)}"
    parent = root / "tmp" / "sandbox" / day if sandbox else root / "runs" / day
    base = parent / stem
    if not base.exists():
        return base
    for index in range(2, 1000):
        candidate = parent / f"{stem}-{index}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"too many run directories for {stem}")


def capture_run(
    root: str | Path,
    mode: str,
    commands: list[dict[str, Any]],
    decision_time: str | None = None,
    timeout_seconds: int = 300,
    sandbox: bool = False,
) -> dict[str, Any]:
    root_path = Path(root).expanduser().resolve()
    command_results = [run_command(root_path, command, timeout_seconds) for command in commands]
    effective_decision_time = decision_time or now_iso()
    run_dir = unique_run_dir(root_path, effective_decision_time, mode, sandbox=sandbox)
    artifact_dir = run_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    for result in command_results:
        name = result["name"]
        stored_stdout = redact(result["stdout"])
        stored_stderr = redact(result["stderr"])
        (artifact_dir / f"{name}.stdout.txt").write_text(str(stored_stdout), encoding="utf-8")
        (artifact_dir / f"{name}.stderr.txt").write_text(str(stored_stderr), encoding="utf-8")
        meta = {k: v for k, v in result.items() if k not in {"stdout", "stderr"}}
        (artifact_dir / f"{name}.meta.json").write_text(
            json.dumps(redact(meta), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "run_id": run_dir.name,
        "decision_time": effective_decision_time,
        "mode": mode,
        "safety": SAFETY_DECLARATION,
        "selection_system_version": SELECTION_SYSTEM_VERSION,
        "selection_system_refs": SELECTION_SYSTEM_REFS,
        "data_sources": [
            {
                "name": item["name"],
                "fetch_time": effective_decision_time,
                "available_at": effective_decision_time,
                "data_quality_flag": "ok" if item["returncode"] == 0 else "error",
                "artifact_stdout": f"artifacts/{item['name']}.stdout.txt",
                "artifact_stderr": f"artifacts/{item['name']}.stderr.txt",
                "artifact_meta": f"artifacts/{item['name']}.meta.json",
            }
            for item in command_results
        ],
    }
    manifest_validation = validate_run_manifest(manifest)
    decision = derive_decision(mode, command_results, effective_decision_time)
    decision["run_id"] = manifest["run_id"]
    decision["decision_time"] = effective_decision_time

    (run_dir / "run_manifest.json").write_text(
        json.dumps(redact(manifest), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_dir / "manifest_validation.json").write_text(
        json.dumps(redact(manifest_validation), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_dir / "decision.json").write_text(
        json.dumps(redact(decision), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "run_dir": str(run_dir),
        "manifest": redact(manifest),
        "manifest_validation": redact(manifest_validation),
        "decision": redact(decision),
        "commands": [redact({k: v for k, v in item.items() if k not in {"stdout", "stderr"}}) for item in command_results],
    }
