from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from smartmoney_cub_harness.safety import redact
from smartmoney_cub_harness.schemas import RUN_ENVELOPE_SCHEMA, SAFETY_DECLARATION


PERMISSION_SCOPE = {
    "network": False,
    "broker_access": False,
    "account_mutation": False,
    "order": False,
    "cancel": False,
    "trade": False,
    "embedded_llm": False,
    "writes": "run_directory_only",
}


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_absolute_path(value: object) -> bool:
    return isinstance(value, str) and (
        PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()
    )


def _failure_state(tool_calls: list[dict[str, Any]]) -> tuple[int, int, str]:
    failure_count = sum(call.get("status") == "failed" for call in tool_calls)
    trailing_failure_count = 0
    for call in reversed(tool_calls):
        if call.get("status") != "failed":
            break
        trailing_failure_count += 1
    status = (
        "completed"
        if failure_count == 0
        else "blocked"
        if trailing_failure_count >= 3
        else "pending_review"
    )
    return failure_count, trailing_failure_count, status


def build_run_envelope(
    *,
    run_id: str,
    decision_time: str,
    mode: str,
    commands: list[dict[str, Any]],
    command_results: list[dict[str, Any]],
    agent_name: str = "external-agent",
    agent_version: str | None = None,
    agent_interface: str = "command",
) -> dict[str, Any]:
    redacted_commands = redact(commands)
    agent = {"name": agent_name, "version": agent_version, "interface": agent_interface}
    tool_calls: list[dict[str, Any]] = []
    output_evidence: list[str] = []
    for attempt, result in enumerate(command_results, start=1):
        name = str(redact(str(result["name"])))
        evidence = {
            "stdout": f"artifacts/{name}.stdout.txt",
            "stderr": f"artifacts/{name}.stderr.txt",
            "metadata": f"artifacts/{name}.meta.json",
        }
        tool_calls.append(
            {
                "name": name,
                "started_at": result["started_at"],
                "finished_at": result["finished_at"],
                "returncode": result["returncode"],
                "timed_out": bool(result.get("timed_out", False)),
                "status": "succeeded" if result["returncode"] == 0 else "failed",
                "attempt": attempt,
                "evidence": evidence,
            }
        )
        output_evidence.extend(evidence.values())

    failure_count, trailing_failure_count, status = _failure_state(tool_calls)

    envelope = {
        "schema": RUN_ENVELOPE_SCHEMA,
        "run_id": run_id,
        "decision_time": decision_time,
        "mode": mode,
        "safety": SAFETY_DECLARATION,
        "agent": redact(agent),
        "input_snapshot_sha256": _canonical_sha256(redacted_commands),
        "tool_calls": tool_calls,
        "output_evidence": output_evidence,
        "failure_count": failure_count,
        "trailing_consecutive_failure_count": trailing_failure_count,
        "status": status,
        "permission_scope": dict(PERMISSION_SCOPE),
        "champion_mutated": False,
        "core_rules_mutated": False,
    }
    return envelope


def validate_run_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if envelope.get("safety") != SAFETY_DECLARATION:
        errors.append("safety declaration is missing or invalid")
    if envelope.get("status") not in {"completed", "pending_review", "blocked"}:
        errors.append(f"unsupported workflow status: {envelope.get('status')}")
    for field in ("champion_mutated", "core_rules_mutated"):
        if envelope.get(field) is not False:
            errors.append(f"{field} must be false")
    permissions = envelope.get("permission_scope", {})
    for field in (
        "network",
        "broker_access",
        "account_mutation",
        "order",
        "cancel",
        "trade",
        "embedded_llm",
    ):
        if permissions.get(field) is not False:
            errors.append(f"permission_scope.{field} must be false")
    if permissions.get("writes") != "run_directory_only":
        errors.append("permission_scope.writes must be run_directory_only")
    evidence_paths = [
        path
        for call in envelope.get("tool_calls", [])
        for path in call.get("evidence", {}).values()
    ]
    if any(_is_absolute_path(path) for path in evidence_paths):
        errors.append("tool_calls evidence paths must be relative")
    if any(_is_absolute_path(path) for path in envelope.get("output_evidence", [])):
        errors.append("output_evidence paths must be relative")
    failure_count, trailing_failure_count, status = _failure_state(envelope.get("tool_calls", []))
    if (
        envelope.get("failure_count") != failure_count
        or envelope.get("trailing_consecutive_failure_count") != trailing_failure_count
        or envelope.get("status") != status
    ):
        errors.append("failure counts and status do not match tool calls")
    return {"valid": not errors, "errors": errors, "safety": SAFETY_DECLARATION}
