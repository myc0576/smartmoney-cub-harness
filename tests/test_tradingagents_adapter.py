from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import smartmoney_cub_harness.tradingagents_adapter as adapter
from smartmoney_cub_harness.cli import doctor
from smartmoney_cub_harness.schemas import SAFETY_DECLARATION, TRADINGAGENTS_REVIEW_PACKET_SCHEMA
from smartmoney_cub_harness.tradingagents_adapter import (
    check_tradingagents_environment,
    ingest_tradingagents_report,
    run_tradingagents_local_bridge,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-m", "smartmoney_cub_harness.cli", *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_report_only_ingest_generates_review_packet(tmp_path: Path):
    report = tmp_path / "tradingagents_report.md"
    report.write_text(
        "\n".join(
            [
                "Toy/demo only TradingAgents report.",
                "Candidate thesis: monitor evidence quality, not execution.",
                "Risk: provenance may be incomplete.",
            ]
        ),
        encoding="utf-8",
    )

    packet = ingest_tradingagents_report(
        report=report,
        ticker="TOY.SS",
        analysis_date="2026-07-06",
    )

    assert packet["schema"] == TRADINGAGENTS_REVIEW_PACKET_SCHEMA
    assert packet["source"] == "tradingagents"
    assert packet["mode"] == "report_only"
    assert packet["ticker"] == "TOY.SS"
    assert packet["external_llm_required"] is False
    assert packet["network_required"] is False
    assert packet["credentials_captured"] is False
    assert packet["broker_execution"] is False
    assert packet["actionability"] == "review_only"
    assert packet["safety"] == SAFETY_DECLARATION
    assert packet["risk_notes"]


def test_report_packet_redacts_fake_api_key(tmp_path: Path):
    fake_key = "sk-" + "test-secret-1234567890"
    key_name = "OPENAI" + "_API_KEY"
    report = tmp_path / "report.md"
    report.write_text(
        f"Toy/demo only. {key_name}={fake_key}\nRisk: redact accidental secrets.",
        encoding="utf-8",
    )

    packet = ingest_tradingagents_report(
        report=report,
        ticker="TOY.SZ",
        analysis_date="2026-07-06",
    )

    assert fake_key not in json.dumps(packet, ensure_ascii=False)
    assert packet["credentials_captured"] is False


def test_tradingagents_run_requires_allow_network():
    result = run_cli(
        "tradingagents-run",
        "--ticker",
        "TOY.SS",
        "--analysis-date",
        "2026-07-06",
        "--ack-external-llm",
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "network_not_allowed"
    assert payload["safety"] == SAFETY_DECLARATION
    assert "Traceback" not in result.stderr


def test_tradingagents_run_requires_external_llm_ack():
    result = run_cli(
        "tradingagents-run",
        "--ticker",
        "TOY.SS",
        "--analysis-date",
        "2026-07-06",
        "--allow-network",
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "external_llm_not_acknowledged"
    assert payload["safety"] == SAFETY_DECLARATION
    assert "Traceback" not in result.stderr


def test_tradingagents_missing_returns_structured_disabled(monkeypatch):
    monkeypatch.setattr(adapter.importlib.util, "find_spec", lambda name: None)

    payload = run_tradingagents_local_bridge(
        ticker="TOY.SS",
        analysis_date="2026-07-06",
        allow_network=True,
        ack_external_llm=True,
    )

    assert payload["status"] == "disabled"
    assert payload["error"]["code"] == "tradingagents_not_installed"
    assert payload["broker_execution"] is False
    assert payload["safety"] == SAFETY_DECLARATION


def test_tradingagents_doctor_does_not_print_key_values():
    fake_key = "sk-" + "test-secret-1234567890"
    key_name = "OPENAI" + "_API_KEY"
    result = run_cli("tradingagents-doctor", extra_env={key_name: fake_key})

    assert result.returncode == 0
    assert fake_key not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["llm_providers_configured"]["openai"] is True
    assert payload["credential_values_visible"] is False
    assert payload["credentials_captured"] is False
    assert payload["safety"] == SAFETY_DECLARATION


def test_tradingagents_environment_check_is_optional(monkeypatch):
    monkeypatch.setattr(adapter.importlib.util, "find_spec", lambda name: None)

    result = check_tradingagents_environment(env={})

    assert result["adapter_status"] == "optional"
    assert result["tradingagents_installed"] is False
    assert result["network_required"] is False
    assert result["external_api_required"] is False
    assert result["broker_api_required"] is False


def test_default_doctor_keeps_offline_external_api_boundary():
    result = doctor()

    assert result["network_required"] is False
    assert result["external_api_required"] is False
    assert result["broker_api_required"] is False
    assert result["execution_integrations"] == "disabled"
    assert result["safety"] == SAFETY_DECLARATION


def test_docs_do_not_use_execution_phrases_without_negation():
    files = [
        "README.md",
        "README.zh-CN.md",
        "docs/integrations.md",
        "docs/tradingagents-adapter.md",
        "docs/privacy.md",
        "docs/safety.md",
        "docs/agent-integration.md",
    ]
    phrases = ["auto trade", "place order", "broker execution enabled"]
    negations = ("no ", "not ", "never ", "do not ", "must not ", "不得", "不能", "不")

    for relative in files:
        text = (REPO_ROOT / relative).read_text(encoding="utf-8").lower()
        for phrase in phrases:
            start = 0
            while True:
                index = text.find(phrase, start)
                if index == -1:
                    break
                window = text[max(0, index - 100) : index + len(phrase) + 100]
                assert any(negation in window for negation in negations), (relative, phrase, window)
                start = index + len(phrase)
