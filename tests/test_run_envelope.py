from __future__ import annotations

import copy

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
        "enforcement": "declarative",
        "verified": False,
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
        ("enforcement", "enforced"),
        ("verified", True),
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
    assert validation["permission_scope_verified"] is False


def test_validate_run_envelope_rejects_non_object_permission_scope_without_raising():
    envelope = _single_success_call_envelope()
    envelope["permission_scope"] = []

    validation = validate_run_envelope(envelope)

    assert validation["valid"] is False
    assert "permission_scope must be an object" in validation["errors"]
    assert validation["permission_scope_verified"] is False


def test_validate_run_envelope_rejects_non_object_top_level_without_raising():
    validation = validate_run_envelope([])

    assert validation["valid"] is False
    assert validation["errors"] == ["run envelope must be an object"]
    assert validation["permission_scope_verified"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        "top_extra",
        "agent_missing_version",
        "agent_extra",
        "tool_extra",
        "evidence_extra",
        "permission_extra",
        "invalid_agent_version",
        "boolean_failure_count",
    ],
)
def test_validate_run_envelope_matches_strict_object_schema(mutation: str):
    envelope = copy.deepcopy(_single_success_call_envelope())
    if mutation == "top_extra":
        envelope["unexpected"] = True
    elif mutation == "agent_missing_version":
        envelope["agent"].pop("version")
    elif mutation == "agent_extra":
        envelope["agent"]["unexpected"] = True
    elif mutation == "tool_extra":
        envelope["tool_calls"][0]["unexpected"] = True
    elif mutation == "evidence_extra":
        envelope["tool_calls"][0]["evidence"]["unexpected"] = "artifact.txt"
    elif mutation == "permission_extra":
        envelope["permission_scope"]["unexpected"] = False
    elif mutation == "invalid_agent_version":
        envelope["agent"]["version"] = 1
    else:
        envelope["failure_count"] = False

    validation = validate_run_envelope(envelope)

    assert validation["valid"] is False
    assert validation["errors"]


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


@pytest.mark.parametrize(
    ("field", "invalid_value", "expected_error"),
    [
        ("schema", "wrong.v1", f"schema must be {RUN_ENVELOPE_SCHEMA}"),
        ("run_id", "", "run_id must be a non-empty string"),
        ("decision_time", "not-a-time", "decision_time must be an ISO-8601 timestamp"),
        ("mode", "", "mode must be a non-empty string"),
        ("agent", {}, "agent must contain non-empty name and interface strings"),
        (
            "input_snapshot_sha256",
            "not-a-hash",
            "input_snapshot_sha256 must be 64 hexadecimal characters",
        ),
        ("tool_calls", (), "tool_calls must be a list"),
        ("output_evidence", (), "output_evidence must be a list"),
    ],
)
@pytest.mark.parametrize("missing", [False, True], ids=["invalid", "missing"])
def test_validate_run_envelope_rejects_invalid_required_provenance(
    field: str,
    invalid_value: object,
    expected_error: str,
    missing: bool,
):
    envelope = build_run_envelope(
        run_id="toy-run",
        decision_time="2026-06-01T15:30:00+08:00",
        mode="after-close",
        commands=[],
        command_results=[],
    )
    if missing:
        envelope.pop(field)
    else:
        envelope[field] = invalid_value

    validation = validate_run_envelope(envelope)

    assert validation["valid"] is False
    assert expected_error in validation["errors"]


@pytest.mark.parametrize(
    "decision_time",
    ["2026-01-01", "2026-01-01T00:00:00"],
)
def test_validate_run_envelope_requires_rfc3339_time_and_timezone(decision_time: str):
    envelope = _single_success_call_envelope()
    envelope["decision_time"] = decision_time

    validation = validate_run_envelope(envelope)

    assert validation["valid"] is False
    assert "decision_time must be an ISO-8601 timestamp" in validation["errors"]
    assert validation["safety"] == SAFETY_DECLARATION


def _single_success_call_envelope() -> dict[str, object]:
    return build_run_envelope(
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
                "timed_out": False,
            }
        ],
    )


def test_validate_run_envelope_rejects_returncode_status_mismatch_using_actual_outcome():
    envelope = _single_success_call_envelope()
    envelope["tool_calls"][0]["status"] = "failed"

    validation = validate_run_envelope(envelope)

    assert validation["valid"] is False
    assert "tool_calls[0].status does not match returncode/timed_out" in validation["errors"]
    assert "failure counts and status do not match tool calls" not in validation["errors"]


def test_validate_run_envelope_rejects_timeout_status_mismatch_using_actual_outcome():
    envelope = _single_success_call_envelope()
    envelope["tool_calls"][0]["timed_out"] = True

    validation = validate_run_envelope(envelope)

    assert validation["valid"] is False
    assert "tool_calls[0].status does not match returncode/timed_out" in validation["errors"]
    assert "failure counts and status do not match tool calls" in validation["errors"]


def test_validate_run_envelope_rejects_non_object_tool_call_without_raising():
    envelope = _single_success_call_envelope()
    envelope["tool_calls"] = ["not-an-object"]

    try:
        validation = validate_run_envelope(envelope)
    except Exception as exc:  # pragma: no cover - the assertion documents the regression
        pytest.fail(f"validator raised for malformed tool call: {exc}")

    assert validation["valid"] is False
    assert "tool_calls[0] must be an object" in validation["errors"]


def test_validate_run_envelope_rejects_malformed_tool_evidence():
    envelope = _single_success_call_envelope()
    envelope["tool_calls"][0]["evidence"] = {
        "stdout": "artifacts/signal.stdout.txt",
        "stderr": 42,
    }

    validation = validate_run_envelope(envelope)

    assert validation["valid"] is False
    assert (
        "tool_calls[0].evidence must contain relative string stdout, stderr, and metadata paths"
        in validation["errors"]
    )


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../private/file",
        "samples/../private/file",
        r"\rooted\private",
        r"\\server\share\private",
        r"C:\private\file",
        42,
        "",
    ],
)
def test_validate_run_envelope_rejects_unsafe_or_non_string_evidence_paths(
    unsafe_path: object,
):
    envelope = _single_success_call_envelope()
    envelope["tool_calls"][0]["evidence"]["stdout"] = unsafe_path
    envelope["output_evidence"][0] = unsafe_path

    validation = validate_run_envelope(envelope)

    assert validation["valid"] is False
    assert any("relative" in error for error in validation["errors"])


def test_validate_run_envelope_reconciles_output_evidence_with_tool_calls():
    envelope = _single_success_call_envelope()
    envelope["output_evidence"] = []

    validation = validate_run_envelope(envelope)

    assert validation["valid"] is False
    assert "output_evidence must exactly match tool call evidence paths" in validation["errors"]


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("name", ""),
        ("started_at", ""),
        ("finished_at", ""),
        ("returncode", "0"),
        ("timed_out", 0),
        ("attempt", 0),
        ("status", []),
    ],
)
def test_validate_run_envelope_rejects_malformed_normalized_tool_fields(
    field: str,
    invalid_value: object,
):
    envelope = _single_success_call_envelope()
    envelope["tool_calls"][0][field] = invalid_value

    try:
        validation = validate_run_envelope(envelope)
    except Exception as exc:  # pragma: no cover - the assertion documents the regression
        pytest.fail(f"validator raised for malformed tool field: {exc}")

    assert validation["valid"] is False
    assert f"tool_calls[0].{field} is invalid" in validation["errors"]
