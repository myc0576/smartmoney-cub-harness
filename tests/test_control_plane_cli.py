from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from smartmoney_cub_harness import cli
from smartmoney_cub_harness.evidence_pack import build_evidence_pack
from smartmoney_cub_harness.run_envelope import build_run_envelope
from smartmoney_cub_harness.schemas import (
    EVIDENCE_PACK_SCHEMA,
    RUN_ENVELOPE_SCHEMA,
    SAFETY_DECLARATION,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = REPO_ROOT / "schemas"
SCHEMA_ID_ROOT = "https://github.com/myc0576/smartmoney-cub-harness/schemas/"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_stdout(capsys: pytest.CaptureFixture[str]) -> dict:
    return json.loads(capsys.readouterr().out)


def _envelope() -> dict:
    return build_run_envelope(
        run_id="toy-run",
        decision_time="2026-07-10T09:30:00+08:00",
        mode="after-close",
        commands=[],
        command_results=[],
    )


def _make_sample(tmp_path: Path) -> Path:
    run_dir = tmp_path / "toy-run"
    _write_json(
        run_dir / "run_manifest.json",
        {
            "schema": "smartmoney_cub_run_manifest.v1",
            "run_id": "toy-run",
            "decision_time": "2026-07-10T09:30:00+08:00",
            "mode": "offline",
            "data_sources": [
                {
                    "name": "toy_source",
                    "fetch_time": "2026-07-10T09:00:00+08:00",
                    "available_at": "2026-07-10T09:00:00+08:00",
                    "data_quality_flag": "ok",
                }
            ],
            "safety": SAFETY_DECLARATION,
        },
    )
    _write_json(run_dir / "decision.json", {"action_label": "SILENT", "safety": SAFETY_DECLARATION})
    _write_json(run_dir / "outcome_d1.json", {"d1_return_pct": 0.0, "safety": SAFETY_DECLARATION})
    return run_dir


@pytest.mark.parametrize(("valid", "expected_exit"), [(True, 0), (False, 2)])
def test_validate_envelope_prints_safe_validation_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    valid: bool,
    expected_exit: int,
) -> None:
    envelope = _envelope()
    if not valid:
        envelope["permission_scope"]["network"] = True
    path = tmp_path / "run_envelope.json"
    _write_json(path, envelope)

    exit_code = cli.main(["validate-envelope", str(path)])
    payload = _read_stdout(capsys)

    assert exit_code == expected_exit
    assert payload["valid"] is valid
    assert payload["safety"] == SAFETY_DECLARATION


def test_capture_run_forwards_optional_agent_metadata(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict = {}

    def fake_capture_run(**kwargs):
        captured.update(kwargs)
        return {"status": "ok", "safety": SAFETY_DECLARATION}

    monkeypatch.setattr(cli, "capture_run", fake_capture_run)

    exit_code = cli.main(
        [
            "capture-run",
            "--mode",
            "after-close",
            "--preset",
            "toy",
            "--agent-name",
            "Toy Agent",
            "--agent-version",
            "1.2.3",
            "--agent-interface",
            "cli",
        ]
    )

    assert exit_code == 0
    assert captured["agent_name"] == "Toy Agent"
    assert captured["agent_version"] == "1.2.3"
    assert captured["agent_interface"] == "cli"
    assert _read_stdout(capsys)["safety"] == SAFETY_DECLARATION


def test_capture_run_keeps_agent_metadata_defaults(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict = {}

    def fake_capture_run(**kwargs):
        captured.update(kwargs)
        return {"status": "ok", "safety": SAFETY_DECLARATION}

    monkeypatch.setattr(cli, "capture_run", fake_capture_run)

    assert cli.main(["capture-run", "--mode", "after-close", "--preset", "toy"]) == 0

    assert captured["agent_name"] == "external-agent"
    assert captured["agent_version"] is None
    assert captured["agent_interface"] == "command"
    assert _read_stdout(capsys)["safety"] == SAFETY_DECLARATION


def test_build_evidence_pack_requires_samples() -> None:
    with pytest.raises(SystemExit) as error:
        cli.main(["build-evidence-pack", "pack", "--rule-candidate", "rule.json"])

    assert error.value.code == 2


def test_build_evidence_pack_forwards_samples_rule_and_horizon(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rule_path = tmp_path / "rule.json"
    _write_json(rule_path, {"rule_id": "toy-rule", "family": "toy"})
    captured: dict = {}

    def fake_build(output_dir, sample_dirs, rule_candidate, horizon="d1"):
        captured.update(
            output_dir=output_dir,
            sample_dirs=sample_dirs,
            rule_candidate=rule_candidate,
            horizon=horizon,
        )
        return {"schema": EVIDENCE_PACK_SCHEMA, "safety": SAFETY_DECLARATION}

    monkeypatch.setattr(cli, "build_evidence_pack", fake_build, raising=False)

    exit_code = cli.main(
        [
            "build-evidence-pack",
            str(tmp_path / "pack"),
            "--sample",
            "run-a",
            "--sample",
            "run-b",
            "--rule-candidate",
            str(rule_path),
            "--horizon",
            "d3",
        ]
    )

    assert exit_code == 0
    assert captured == {
        "output_dir": str(tmp_path / "pack"),
        "sample_dirs": ["run-a", "run-b"],
        "rule_candidate": {"rule_id": "toy-rule", "family": "toy"},
        "horizon": "d3",
    }
    assert _read_stdout(capsys)["safety"] == SAFETY_DECLARATION


@pytest.mark.parametrize(
    ("evidence_status", "expected_exit"),
    [("verified", 0), ("pending_review", 2), ("blocked", 2)],
)
def test_replay_evidence_pack_exit_code_requires_verified_replay(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    evidence_status: str,
    expected_exit: int,
) -> None:
    def fake_replay(pack_dir):
        assert pack_dir == "toy-pack"
        return {"evidence_status": evidence_status, "safety": SAFETY_DECLARATION}

    monkeypatch.setattr(cli, "replay_evidence_pack", fake_replay, raising=False)

    exit_code = cli.main(["replay-evidence-pack", "toy-pack"])

    assert exit_code == expected_exit
    assert _read_stdout(capsys)["safety"] == SAFETY_DECLARATION


def test_run_envelope_schema_matches_runtime_artifact_and_fixed_contract() -> None:
    schema = json.loads((SCHEMA_ROOT / "run-envelope.schema.json").read_text(encoding="utf-8"))
    artifact = _envelope()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == SCHEMA_ID_ROOT + "run-envelope.schema.json"
    assert set(schema["required"]) == set(artifact)
    properties = schema["properties"]
    assert properties["schema"]["const"] == RUN_ENVELOPE_SCHEMA
    assert properties["safety"]["const"] == SAFETY_DECLARATION
    assert set(properties["status"]["enum"]) == {"completed", "pending_review", "blocked"}
    assert properties["input_snapshot_sha256"]["pattern"] == "^[0-9a-fA-F]{64}$"
    assert properties["champion_mutated"]["const"] is False
    assert properties["core_rules_mutated"]["const"] is False
    assert set(properties["agent"]["required"]) == set(artifact["agent"])
    assert set(properties["tool_calls"]["items"]["required"]) == set(
        {
            "name",
            "started_at",
            "finished_at",
            "returncode",
            "timed_out",
            "status",
            "attempt",
            "evidence",
        }
    )
    permission_properties = properties["permission_scope"]["properties"]
    assert permission_properties["writes"]["const"] == "run_directory_only"
    assert all(
        permission_properties[name]["const"] is False
        for name in (
            "network",
            "broker_access",
            "account_mutation",
            "order",
            "cancel",
            "trade",
            "embedded_llm",
        )
    )
    assert "$defs" in schema and "relativePath" in schema["$defs"]


def test_evidence_pack_schema_matches_runtime_artifact_and_fixed_contract(tmp_path: Path) -> None:
    sample = _make_sample(tmp_path)
    artifact = build_evidence_pack(
        tmp_path / "pack",
        [sample],
        {"rule_id": "toy-rule", "family": "toy"},
    )
    schema = json.loads((SCHEMA_ROOT / "evidence-pack.schema.json").read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == SCHEMA_ID_ROOT + "evidence-pack.schema.json"
    assert set(schema["required"]) == set(artifact)
    properties = schema["properties"]
    assert properties["schema"]["const"] == EVIDENCE_PACK_SCHEMA
    assert properties["safety"]["const"] == SAFETY_DECLARATION
    assert set(properties["horizon"]["enum"]) == {"d1", "d3"}
    assert set(properties["review_status"]["enum"]) == {
        "challenger",
        "ready_for_review",
        "pending_review",
        "blocked",
    }
    assert set(properties["metrics"]["required"]) == {
        "sample_count",
        "false_alert_rate",
        "missed_opportunity_rate",
        "future_leakage_count",
        "risk_contract_violation_rate",
    }
    assert properties["hashes"]["additionalProperties"]["pattern"] == "^[0-9a-fA-F]{64}$"
    gate = properties["promotion_gate"]["properties"]
    assert gate["human_confirmation_required"]["const"] is True
    assert gate["champion_mutated"]["const"] is False
    assert gate["core_rules_mutated"]["const"] is False
    sample_schema = properties["samples"]["items"]
    assert set(sample_schema["required"]) == set(artifact["samples"][0])
    assert "$defs" in schema and "relativePath" in schema["$defs"]


@pytest.mark.parametrize(
    "schema_name",
    ["run-envelope.schema.json", "evidence-pack.schema.json"],
)
@pytest.mark.parametrize(
    ("path", "is_relative"),
    [
        ("artifacts/signal.stdout.txt", True),
        (r"samples\toy-run\decision.json", True),
        ("/abs", False),
        (r"\rooted", False),
        (r"\\server\share\file", False),
        (r"C:\private\file", False),
        ("../private/file", False),
        ("samples/../private/file", False),
    ],
)
def test_schema_relative_path_patterns_reject_rooted_and_traversal_paths(
    schema_name: str,
    path: str,
    is_relative: bool,
) -> None:
    schema = json.loads((SCHEMA_ROOT / schema_name).read_text(encoding="utf-8"))
    pattern = re.compile(schema["$defs"]["relativePath"]["pattern"])

    assert (pattern.fullmatch(path) is not None) is is_relative
