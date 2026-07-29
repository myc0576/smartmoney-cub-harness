from __future__ import annotations

import json

import pytest

from smartmoney_cub.cli import main
from smartmoney_cub.plugins import environment as env


@pytest.fixture()
def plugin_home(tmp_path, monkeypatch):
    monkeypatch.setenv(env.HOME_ENV_VAR, str(tmp_path))
    return tmp_path


def _run(capsys, argv: list[str]) -> tuple[int, dict]:
    code = main(argv)
    out = capsys.readouterr().out
    return code, json.loads(out)


def test_cli_plugin_list_shows_catalog(plugin_home, capsys):
    code, payload = _run(capsys, ["plugin", "list"])
    assert code == 0
    ids = {p["id"] for p in payload["plugins"]}
    assert {"akshare", "tradingagents", "qlib", "chronos2", "timesfm"} <= ids
    for plugin in payload["plugins"]:
        if plugin["integration_level"] != "runtime_integrated":
            assert plugin["status"] != "ready"


def test_cli_plugin_install_requires_consent(plugin_home, capsys):
    code, payload = _run(capsys, ["plugin", "install", "akshare"])
    assert code == 2
    assert payload["error"]["code"] == "confirmation_required"


def test_cli_analyze_requires_third_party_ack(plugin_home, capsys):
    code, payload = _run(
        capsys,
        [
            "analyze",
            "--target",
            "600519.SS",
            "--data-provider",
            "akshare",
            "--plugins",
            "chronos2",
        ],
    )
    assert code == 2
    assert payload["error"]["code"] == "consent_required"


def test_cli_analyze_not_installed_plugin_fails_cleanly(plugin_home, capsys):
    code, payload = _run(
        capsys,
        [
            "analyze",
            "--target",
            "600519.SS",
            "--data-provider",
            "akshare",
            "--ack-third-party",
        ],
    )
    assert code == 2
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "data_provider_failed"
    assert payload["safety"] == "READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE"


def test_cli_plugin_doctor_hides_credentials(plugin_home, capsys, monkeypatch):
    secret = "sk-cli-secret-98765"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    code, payload = _run(capsys, ["plugin", "doctor"])
    assert code == 0
    assert secret not in json.dumps(payload)


def test_cli_existing_doctor_still_works(capsys):
    code, payload = _run(capsys, ["doctor"])
    assert code == 0
    assert payload["safety"] == "READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE"
