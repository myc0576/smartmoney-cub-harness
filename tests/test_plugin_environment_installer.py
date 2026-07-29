from __future__ import annotations

import json
from pathlib import Path

import pytest

from smartmoney_cub.plugins import environment as env
from smartmoney_cub.plugins import installer
from smartmoney_cub.plugins.exceptions import PluginSecurityError
from smartmoney_cub.plugins.installer import CommandResult


@pytest.fixture()
def plugin_home(tmp_path, monkeypatch):
    monkeypatch.setenv(env.HOME_ENV_VAR, str(tmp_path))
    return tmp_path


def _fake_runner_factory(calls: list[list[str]], venv_python: Path | None = None):
    """Return a command runner that records argv and simulates success."""

    def runner(argv: list[str], **kwargs) -> CommandResult:
        calls.append(list(argv))
        # Simulate `python -m venv <dir>` by creating the venv python file.
        if "-m" in argv and "venv" in argv:
            venv_dir = Path(argv[-1])
            if venv_python is not None:
                target = venv_python
            else:
                target = venv_dir / "Scripts" / "python.exe"
                if not target.parent.name == "Scripts":
                    target = venv_dir / "bin" / "python"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("", encoding="utf-8")
            alt = venv_dir / "bin" / "python"
            alt.parent.mkdir(parents=True, exist_ok=True)
            alt.write_text("", encoding="utf-8")
        return CommandResult(returncode=0, stdout="", stderr="")

    return runner


# --- category 7: injection and traversal hardening ---


def test_plugin_id_rejects_traversal_and_injection():
    for bad in ("../evil", "a;rm -rf /", "UPPER", "a b", "", "a" * 41, "akshare$(x)"):
        with pytest.raises(PluginSecurityError):
            env.validate_plugin_id(bad)
    assert env.validate_plugin_id("akshare") == "akshare"


def test_install_spec_rejects_shell_metacharacters():
    for bad in ("pkg; rm -rf ~", "pkg && curl x", "pkg | sh", "pkg`x`", "pkg$(x)", ""):
        with pytest.raises(PluginSecurityError):
            env.validate_install_spec(bad)
    assert env.validate_install_spec("akshare>=1.0") == "akshare>=1.0"


def test_symbol_validation_rejects_injection():
    for bad in ("600519; ls", "a" * 30, "", "600519|cat"):
        with pytest.raises(PluginSecurityError):
            env.validate_symbol(bad)
    assert env.validate_symbol("600519.SS") == "600519.SS"


def test_safe_child_path_blocks_escape(tmp_path):
    with pytest.raises(PluginSecurityError):
        env.safe_child_path(tmp_path, "..", "escape.txt")
    inside = env.safe_child_path(tmp_path, "logs", "run.log")
    assert str(inside).startswith(str(tmp_path))


def test_installer_argv_never_uses_shell(plugin_home):
    calls: list[list[str]] = []
    runner = _fake_runner_factory(calls)
    installer.install_plugin(
        "akshare",
        yes=True,
        allow_network=True,
        ack_third_party=True,
        command_runner=runner,
    )
    assert calls, "expected at least one subprocess call"
    for argv in calls:
        assert isinstance(argv, list)
        joined = " ".join(argv)
        for token in (";", "&&", "||", "`", "$("):
            assert token not in joined


# --- category 6: venv path convention ---


def test_venv_lives_under_isolated_plugin_home(plugin_home):
    venv = env.plugin_venv_dir("akshare")
    assert venv == plugin_home / "plugins" / "akshare" / ".venv"


# --- categories 8 and 9: consent gates ---


def test_install_requires_yes_flag(plugin_home):
    result = installer.install_plugin("akshare")
    assert result["status"] == "error"
    assert result["error"]["code"] == "confirmation_required"


def test_install_requires_network_consent(plugin_home):
    result = installer.install_plugin("akshare", yes=True, ack_third_party=True)
    assert result["status"] == "error"
    assert result["error"]["code"] == "network_not_allowed"


def test_install_requires_third_party_ack(plugin_home):
    result = installer.install_plugin("akshare", yes=True, allow_network=True)
    assert result["status"] == "error"
    assert "ack" in json.dumps(result).lower() or "third" in json.dumps(result).lower()


def test_model_plugin_requires_model_download_ack(plugin_home):
    result = installer.install_plugin(
        "chronos2", yes=True, allow_network=True, ack_third_party=True
    )
    assert result["status"] == "error"
    assert "model" in json.dumps(result).lower()


# --- category 5: fake plugin lifecycle ---


def test_fake_lifecycle_install_state_uninstall_preserves_results(plugin_home):
    calls: list[list[str]] = []
    runner = _fake_runner_factory(calls)

    result = installer.install_plugin(
        "akshare",
        yes=True,
        allow_network=True,
        ack_third_party=True,
        command_runner=runner,
    )
    assert result["status"] == "ok"
    assert installer.is_installed("akshare") is True

    state = installer.read_install_state("akshare")
    assert state is not None
    assert state["schema"] == "smartmoney_cub_plugin_install_state.v1"

    # user-generated analysis results must survive uninstall
    home = env.plugin_home("akshare")
    results_dir = home / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    keep = results_dir / "analysis_2026.json"
    keep.write_text("{}", encoding="utf-8")

    removed = installer.uninstall_plugin("akshare", yes=True)
    assert removed["status"] == "ok"
    assert removed["user_results_preserved"] is True
    assert installer.is_installed("akshare") is False
    assert keep.exists(), "uninstall must not delete user analysis results"
    assert not (home / ".venv").exists()


def test_uninstall_requires_confirmation(plugin_home):
    result = installer.uninstall_plugin("akshare")
    assert result["status"] == "error"
