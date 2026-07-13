from __future__ import annotations

import pytest

from smartmoney_cub_harness.run_envelope import build_run_envelope, validate_run_envelope
from smartmoney_cub_harness.schemas import RUN_ENVELOPE_SCHEMA, SAFETY_DECLARATION


def test_build_run_envelope_records_normalized_success_provenance():
    envelope = build_run_envelope(
        run_id="20260601_153000-after-close",
        decision_time="2026-06-01T15:30:00+08:00",
        mode="after-close",
        commands=[{"name": "signal", "argv": ["python", "toy.py"]}],
        command_results=[
            {
                "name": "signal",
                "argv": ["python", "toy.py"],
                "started_at": "2026-06-01T07:30:00+00:00",
                "finished_at": "2026-06-01T07:30:01+00:00",
                "returncode": 0,
                "timed_out": False,
            }
        ],
        agent_name="Toy Agent",
        agent_version="1.0",
        agent_interface="cli",
    )

    assert envelope["schema"] == RUN_ENVELOPE_SCHEMA
    assert envelope["safety"] == SAFETY_DECLARATION
    assert envelope["agent"] == {"name": "Toy Agent", "version": "1.0", "interface": "cli"}
    assert len(envelope["input_snapshot_sha256"]) == 64
    assert envelope["tool_calls"][0]["evidence"] == {
        "stdout": "artifacts/signal.stdout.txt",
        "stderr": "artifacts/signal.stderr.txt",
        "metadata": "artifacts/signal.meta.json",
    }
    assert envelope["tool_calls"][0]["status"] == "succeeded"
    assert envelope["output_evidence"] == [
        "artifacts/signal.stdout.txt",
        "artifacts/signal.stderr.txt",
        "artifacts/signal.meta.json",
    ]
    assert envelope["failure_count"] == 0
    assert envelope["trailing_consecutive_failure_count"] == 0
    assert envelope["status"] == "completed"
    assert envelope["permission_scope"] == {
        "network": False,
        "broker_access": False,
        "account_mutation": False,
        "order": False,
        "cancel": False,
        "trade": False,
        "embedded_llm": False,
        "writes": "run_directory_only",
    }
    assert envelope["champion_mutated"] is False
    assert envelope["core_rules_mutated"] is False


def test_build_run_envelope_marks_one_trailing_failure_pending_review():
    envelope = build_run_envelope(
        run_id="toy-run",
        decision_time="2026-06-01T15:30:00+08:00",
        mode="after-close",
        commands=[{"name": "ok", "argv": ["toy"]}, {"name": "fail", "argv": ["toy"]}],
        command_results=[
            {
                "name": "ok",
                "started_at": "2026-06-01T07:30:00+00:00",
                "finished_at": "2026-06-01T07:30:01+00:00",
                "returncode": 0,
                "timed_out": False,
            },
            {
                "name": "fail",
                "started_at": "2026-06-01T07:30:01+00:00",
                "finished_at": "2026-06-01T07:30:02+00:00",
                "returncode": 7,
                "timed_out": False,
            },
        ],
    )

    assert envelope["failure_count"] == 1
    assert envelope["trailing_consecutive_failure_count"] == 1
    assert envelope["status"] == "pending_review"


def test_build_run_envelope_marks_three_trailing_failures_blocked():
    results = [
        {
            "name": f"fail-{index}",
            "started_at": "2026-06-01T07:30:00+00:00",
            "finished_at": "2026-06-01T07:30:01+00:00",
            "returncode": 1,
            "timed_out": False,
        }
        for index in range(3)
    ]
    envelope = build_run_envelope(
        run_id="toy-run",
        decision_time="2026-06-01T15:30:00+08:00",
        mode="after-close",
        commands=[{"name": item["name"], "argv": ["toy"]} for item in results],
        command_results=results,
    )

    assert envelope["failure_count"] == 3
    assert envelope["trailing_consecutive_failure_count"] == 3
    assert envelope["status"] == "blocked"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("network", True),
        ("broker_access", True),
        ("account_mutation", True),
        ("order", True),
        ("cancel", True),
        ("trade", True),
        ("embedded_llm", True),
        ("writes", "anywhere"),
    ],
)
def test_validate_run_envelope_rejects_enabled_permissions(field: str, value: object):
    envelope = build_run_envelope(
        run_id="toy-run",
        decision_time="2026-06-01T15:30:00+08:00",
        mode="after-close",
        commands=[],
        command_results=[],
    )
    envelope["permission_scope"][field] = value

    validation = validate_run_envelope(envelope)

    assert validation["valid"] is False
    assert any(error.startswith(f"permission_scope.{field} ") for error in validation["errors"])
    assert validation["safety"] == SAFETY_DECLARATION


@pytest.mark.parametrize("path_style", ["windows", "posix"])
def test_validate_run_envelope_rejects_absolute_evidence_paths(path_style: str):
    absolute_path = "C:" + "\\private\\signal.txt" if path_style == "windows" else "/private/signal.txt"
    envelope = build_run_envelope(
        run_id="toy-run",
        decision_time="2026-06-01T15:30:00+08:00",
        mode="after-close",
        commands=[{"name": "signal", "argv": ["toy"]}],
        command_results=[
            {
                "name": "signal",
                "started_at": "2026-06-01T07:30:00+00:00",
                "finished_at": "2026-06-01T07:30:01+00:00",
                "returncode": 0,
            }
        ],
    )
    envelope["tool_calls"][0]["evidence"]["stdout"] = absolute_path

    validation = validate_run_envelope(envelope)

    assert validation["valid"] is False
    assert "tool_calls evidence paths must be relative" in validation["errors"]
    assert validation["safety"] == SAFETY_DECLARATION


def test_validate_run_envelope_rejects_failure_status_mismatch():
    envelope = build_run_envelope(
        run_id="toy-run",
        decision_time="2026-06-01T15:30:00+08:00",
        mode="after-close",
        commands=[],
        command_results=[],
    )
    envelope["status"] = "pending_review"

    validation = validate_run_envelope(envelope)

    assert validation["valid"] is False
    assert "failure counts and status do not match tool calls" in validation["errors"]
    assert validation["safety"] == SAFETY_DECLARATION


@pytest.mark.parametrize("safety", [None, "unsafe"])
def test_validate_run_envelope_rejects_missing_or_invalid_safety(safety: object):
    envelope = build_run_envelope(
        run_id="toy-run",
        decision_time="2026-06-01T15:30:00+08:00",
        mode="after-close",
        commands=[],
        command_results=[],
    )
    if safety is None:
        envelope.pop("safety")
    else:
        envelope["safety"] = safety

    validation = validate_run_envelope(envelope)

    assert validation["valid"] is False
    assert "safety declaration is missing or invalid" in validation["errors"]
    assert validation["safety"] == SAFETY_DECLARATION


def test_validate_run_envelope_rejects_unsupported_status():
    envelope = build_run_envelope(
        run_id="toy-run",
        decision_time="2026-06-01T15:30:00+08:00",
        mode="after-close",
        commands=[],
        command_results=[],
    )
    envelope["status"] = "running"

    validation = validate_run_envelope(envelope)

    assert validation["valid"] is False
    assert "unsupported workflow status: running" in validation["errors"]


@pytest.mark.parametrize("field", ["champion_mutated", "core_rules_mutated"])
def test_validate_run_envelope_rejects_governed_mutation(field: str):
    envelope = build_run_envelope(
        run_id="toy-run",
        decision_time="2026-06-01T15:30:00+08:00",
        mode="after-close",
        commands=[],
        command_results=[],
    )
    envelope[field] = True

    validation = validate_run_envelope(envelope)

    assert validation["valid"] is False
    assert f"{field} must be false" in validation["errors"]


def test_build_run_envelope_redacts_agent_commands_and_tool_name_before_persistence():
    private_tool_name = "C:" + "\\Users\\Trader\\signal"
    secret_key = "to" + "ken"
    common = {
        "run_id": "toy-run",
        "decision_time": "2026-06-01T15:30:00+08:00",
        "mode": "after-close",
        "command_results": [
            {
                "name": private_tool_name,
                "started_at": "2026-06-01T07:30:00+00:00",
                "finished_at": "2026-06-01T07:30:01+00:00",
                "returncode": 0,
            }
        ],
        "agent_name": f"agent {secret_key}=abc",
    }
    first = build_run_envelope(
        commands=[{"name": "signal", "argv": ["toy", f"{secret_key}=abc"]}],
        **common,
    )
    second = build_run_envelope(
        commands=[{"argv": ["toy", f"{secret_key}=xyz"], "name": "signal"}],
        **common,
    )

    serialized = str(first)
    assert "abc" not in serialized
    assert "Trader" not in serialized
    assert first["tool_calls"][0]["name"] == "[REDACTED]"
    assert first["input_snapshot_sha256"] == second["input_snapshot_sha256"]
