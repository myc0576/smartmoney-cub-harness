from __future__ import annotations

import json

import pytest

from smartmoney_cub.plugins import environment as env
from smartmoney_cub.plugins import installer, manager, runner
from smartmoney_cub.plugins.installer import CommandResult
from smartmoney_cub.plugins.protocol import (
    build_analysis_request,
    build_evidence_packet,
    build_market_data_packet,
)
from smartmoney_cub.schemas import SAFETY_DECLARATION


@pytest.fixture()
def plugin_home(tmp_path, monkeypatch):
    monkeypatch.setenv(env.HOME_ENV_VAR, str(tmp_path))
    return tmp_path


def _install_fake(plugin_id: str) -> None:
    def fake_cmd(argv, **kwargs):
        if "-m" in argv and "venv" in argv:
            for rel in (("Scripts", "python.exe"), ("bin", "python")):
                target = env.plugin_venv_dir(plugin_id).joinpath(*rel)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("", encoding="utf-8")
        return CommandResult(returncode=0, stdout="", stderr="")

    result = installer.install_plugin(
        plugin_id,
        yes=True,
        allow_network=True,
        ack_third_party=True,
        ack_model_download=True,
        command_runner=fake_cmd,
    )
    assert result["status"] == "ok", result


# --- category 10: running a not-installed plugin ---


def test_run_plugin_not_installed_returns_structured_error(plugin_home):
    request = build_analysis_request(symbol="600519.SS", target_type="stock")
    result = runner.run_plugin("akshare", request)
    assert result["status"] == "error"
    assert result["error"]["code"] == "plugin_not_installed"
    assert "install" in result["error"]["message"]
    assert result["safety"] == SAFETY_DECLARATION


def test_run_catalog_only_plugin_rejected(plugin_home):
    request = build_analysis_request(symbol="600519.SS", target_type="stock")
    result = runner.run_plugin("timesfm", request)
    assert result["status"] == "error"


def test_run_disabled_plugin_rejected(plugin_home):
    _install_fake("akshare")
    manager.set_enabled("akshare", False)
    request = build_analysis_request(symbol="600519.SS", target_type="stock")
    result = runner.run_plugin("akshare", request)
    assert result["status"] == "error"
    assert "disabled" in json.dumps(result).lower()


# --- category 11: installed but unconfigured ---


def test_tradingagents_installed_unconfigured_status(plugin_home, monkeypatch):
    for var in (
        "OPENAI_API_KEY",
        "GOOGLE_API_KEY",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
        "DASHSCOPE_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)
    _install_fake("tradingagents")
    from smartmoney_cub.plugins.catalog import get_manifest

    status = manager.compute_plugin_status(
        "tradingagents", get_manifest("tradingagents"), environ={}
    )
    assert status in {"installed_unconfigured", "credentials_missing"}


def test_status_becomes_ready_with_credentials(plugin_home):
    _install_fake("tradingagents")
    from smartmoney_cub.plugins.catalog import get_manifest

    manifest = get_manifest("tradingagents")
    environ = {var: "x" for var in manifest.get("required_environment_variables", [])}
    if not environ:
        environ = {"OPENAI_API_KEY": "x"}
    status = manager.compute_plugin_status("tradingagents", manifest, environ=environ)
    assert status == "ready"


# --- category 12: credential redaction ---


def test_doctor_never_shows_credential_values(plugin_home):
    _install_fake("tradingagents")
    secret = "sk-verysecret1234567890"
    report = manager.plugin_doctor(
        "tradingagents", environ={"OPENAI_API_KEY": secret}
    )
    dumped = json.dumps(report)
    assert secret not in dumped
    assert report.get("credential_values_visible") is False or all(
        r.get("credential_values_visible", False) is False for r in report.get("reports", [])
    )


def test_configure_rejects_secret_keys(plugin_home):
    for key in ("api_key", "openai_api_key", "token", "secret", "password"):
        result = manager.configure_plugin("tradingagents", key, "value")
        assert result["status"] == "error", key


# --- category 17: multi-plugin independence, no blending ---


def _packet(plugin_id: str, kind: str, direction: str) -> dict:
    return build_evidence_packet(
        plugin_id=plugin_id,
        plugin_version="1.0",
        upstream_repo=f"https://github.com/example/{plugin_id}",
        upstream_license="MIT",
        target={"symbol": "600519.SS", "type": "stock", "market": "CN"},
        as_of="2026-07-01",
        horizon="d5",
        input_data={"bars": []},
        data_sources=[{"name": plugin_id, "available_at": "2026-07-01T00:00:00+08:00"}],
        data_quality="ok",
        model_identifier=f"{plugin_id}-test",
        forecast={"direction": direction},
        evidence=[f"{plugin_id} evidence"],
        output_kind=kind,
    )


def test_multi_plugin_results_stay_independent(plugin_home):
    request = build_analysis_request(
        symbol="600519.SS",
        target_type="stock",
        plugins=["p_alpha", "p_beta"],
        data_provider=None,
    )
    packets = {
        "p_alpha": {"status": "ok", "evidence_packet": _packet("p_alpha", "numeric_model_forecast", "up")},
        "p_beta": {"status": "ok", "evidence_packet": _packet("p_beta", "llm_interpretation", "down")},
    }

    def fake_plugin_runner(plugin_id, req):
        return packets[plugin_id]

    report = runner.run_analysis(request, plugin_runner=fake_plugin_runner)

    results = report["plugin_results"]
    assert [p["plugin_id"] for p in results] == ["p_alpha", "p_beta"]
    # packets preserved verbatim - no blending
    assert results[0] == packets["p_alpha"]["evidence_packet"]
    assert results[1] == packets["p_beta"]["evidence_packet"]
    summary = report["summary"]
    assert summary["calibrated_probability_available"] is False
    assert summary["conflicts"], "opposite directions must surface as conflicts"
    dumped = json.dumps(report)
    assert "probability_of_rising" not in dumped
    assert report["safety"] == SAFETY_DECLARATION


def test_analysis_fails_when_data_provider_fails(plugin_home):
    request = build_analysis_request(
        symbol="600519.SS",
        target_type="stock",
        data_provider="akshare",
        plugins=["p_alpha"],
    )

    def fake_plugin_runner(plugin_id, req):
        return {"status": "error", "error": {"code": "boom", "message": "x"}}

    report = runner.run_analysis(request, plugin_runner=fake_plugin_runner)
    assert report["status"] == "error"
    assert report["error"]["code"] == "data_provider_failed"


def test_plugin_error_does_not_hide_other_results(plugin_home):
    request = build_analysis_request(
        symbol="600519.SS", target_type="stock", plugins=["ok_one", "bad_one"]
    )
    good = {"status": "ok", "evidence_packet": _packet("ok_one", "numeric_model_forecast", "up")}

    def fake_plugin_runner(plugin_id, req):
        if plugin_id == "ok_one":
            return good
        return {"status": "error", "error": {"code": "plugin_not_installed", "message": "x"}}

    report = runner.run_analysis(request, plugin_runner=fake_plugin_runner)
    assert len(report["plugin_results"]) == 1
    assert len(report["plugin_errors"]) == 1
