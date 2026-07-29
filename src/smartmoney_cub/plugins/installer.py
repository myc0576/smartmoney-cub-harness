from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from smartmoney_cub.plugins import environment as env
from smartmoney_cub.plugins.catalog import get_manifest
from smartmoney_cub.plugins.exceptions import PluginError, PluginSecurityError
from smartmoney_cub.plugins.status import (
    STATUS_INSTALLED_UNCONFIGURED,
    STATUS_NOT_INSTALLED,
)
from smartmoney_cub.safety import redact
from smartmoney_cub.schemas import PLUGIN_INSTALL_STATE_SCHEMA, SAFETY_DECLARATION

CommandRunner = Callable[[Sequence[str]], "CommandResult"]


class CommandResult:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _default_command_runner(argv: Sequence[str]) -> CommandResult:
    """Run a validated argv list. Never uses shell=True."""

    completed = subprocess.run(  # noqa: S603 - argv is validated upstream
        list(argv),
        shell=False,
        capture_output=True,
        text=True,
        check=False,
        timeout=1800,
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def _validate_argv(argv: Sequence[str]) -> list[str]:
    if not argv:
        raise PluginSecurityError("empty command rejected", code="empty_command")
    validated: list[str] = []
    for part in argv:
        if not isinstance(part, str):
            raise PluginSecurityError(
                f"non-string command argument rejected: {part!r}",
                code="invalid_command_argument",
            )
        for banned in (";", "|", "&", "\n", "\r", "`", "$("):
            if banned in part:
                raise PluginSecurityError(
                    f"shell metacharacter rejected in command argument: {part!r}",
                    code="shell_metacharacter_blocked",
                )
        validated.append(part)
    return validated


def _error(code: str, message: str, plugin_id: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "error",
        "plugin_id": plugin_id,
        "error": {"code": code, "message": message},
        "safety": SAFETY_DECLARATION,
    }
    payload.update(extra)
    return redact(payload)


def check_install_consent(
    manifest: dict[str, Any],
    *,
    yes: bool,
    allow_network: bool,
    ack_third_party: bool,
    ack_model_download: bool,
) -> dict[str, Any] | None:
    """Return a structured refusal when consent is missing, else None."""

    plugin_id = manifest["id"]
    if not yes:
        return _error(
            "confirmation_required",
            f"Installing '{plugin_id}' modifies your machine. Re-run with --yes to confirm.",
            plugin_id,
        )
    if not ack_third_party:
        return _error(
            "third_party_not_acknowledged",
            f"'{plugin_id}' is third-party software maintained by its upstream project "
            f"({manifest.get('upstream_repo', 'unknown')}). Re-run with --ack-third-party.",
            plugin_id,
        )
    if manifest.get("requires_network") and not allow_network:
        return _error(
            "network_not_allowed",
            f"Installing '{plugin_id}' requires network access. Re-run with --allow-network.",
            plugin_id,
        )
    if manifest.get("requires_model_download") and not ack_model_download:
        return _error(
            "model_download_not_acknowledged",
            f"'{plugin_id}' downloads large model files on first use. "
            "Re-run with --ack-model-download to acknowledge.",
            plugin_id,
        )
    return None


def _write_install_state(plugin_id: str, state: dict[str, Any]) -> Path:
    path = env.plugin_install_state_path(plugin_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": PLUGIN_INSTALL_STATE_SCHEMA,
        "safety": SAFETY_DECLARATION,
        **state,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def read_install_state(plugin_id: str) -> dict[str, Any] | None:
    path = env.plugin_install_state_path(plugin_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def is_installed(plugin_id: str) -> bool:
    state = read_install_state(plugin_id)
    return bool(state) and state.get("status") not in (None, STATUS_NOT_INSTALLED, "uninstalled")


def install_plugin(
    plugin_id: str,
    *,
    yes: bool = False,
    allow_network: bool = False,
    ack_third_party: bool = False,
    ack_model_download: bool = False,
    upgrade: bool = False,
    command_runner: CommandRunner | None = None,
    base_python: str | None = None,
) -> dict[str, Any]:
    env.validate_plugin_id(plugin_id)
    try:
        manifest = get_manifest(plugin_id)
    except PluginError as exc:
        return _error(exc.code, str(exc), plugin_id)

    refusal = check_install_consent(
        manifest,
        yes=yes,
        allow_network=allow_network,
        ack_third_party=ack_third_party,
        ack_model_download=ack_model_download,
    )
    if refusal is not None:
        return refusal

    if manifest.get("install_type") not in ("pip", "git"):
        return _error(
            "install_type_not_automated",
            f"Plugin '{plugin_id}' uses install_type={manifest.get('install_type')!r}, "
            "which SmartMoney-Cub does not automate. See docs/plugins.md.",
            plugin_id,
        )

    install_spec = env.validate_install_spec(str(manifest.get("install_spec", "")))
    runner = command_runner or _default_command_runner
    python_exe = base_python or sys.executable

    home = env.plugin_home(plugin_id)
    for sub in ("logs", "cache"):
        (home / sub).mkdir(parents=True, exist_ok=True)
    venv_dir = env.plugin_venv_dir(plugin_id)

    _write_install_state(
        plugin_id,
        {
            "status": "installing",
            "install_type": manifest["install_type"],
            "install_spec": install_spec,
            "started_at": _utc_now(),
        },
    )

    if not env.plugin_python_executable(plugin_id).exists():
        venv_cmd = _validate_argv([python_exe, "-m", "venv", str(venv_dir)])
        venv_result = runner(venv_cmd)
        if venv_result.returncode != 0:
            _write_install_state(plugin_id, {"status": "error", "phase": "venv_create"})
            return _error(
                "venv_create_failed",
                f"Could not create the isolated virtual environment for '{plugin_id}'.",
                plugin_id,
            )

    plugin_python = str(env.plugin_python_executable(plugin_id))
    pip_cmd = [plugin_python, "-m", "pip", "install"]
    if upgrade:
        pip_cmd.append("--upgrade")
    pip_cmd.append(install_spec)
    pip_result = runner(_validate_argv(pip_cmd))
    if pip_result.returncode != 0:
        _write_install_state(plugin_id, {"status": "dependency_error", "phase": "pip_install"})
        return _error(
            "pip_install_failed",
            f"pip failed while installing '{install_spec}' for plugin '{plugin_id}'. "
            "Check the plugin logs directory for details.",
            plugin_id,
        )

    manifest_copy = env.plugin_manifest_copy_path(plugin_id)
    manifest_copy.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_install_state(
        plugin_id,
        {
            "status": STATUS_INSTALLED_UNCONFIGURED,
            "install_type": manifest["install_type"],
            "install_spec": install_spec,
            "installed_at": _utc_now(),
            "upgraded": bool(upgrade),
        },
    )
    return redact(
        {
            "status": "ok",
            "plugin_id": plugin_id,
            "installed": True,
            "upgraded": bool(upgrade),
            "venv": str(venv_dir),
            "install_spec": install_spec,
            "next_step": f"Run 'smcub plugin doctor {plugin_id}' to check configuration.",
            "safety": SAFETY_DECLARATION,
        }
    )


def update_plugin(
    plugin_id: str,
    *,
    yes: bool = False,
    allow_network: bool = False,
    ack_third_party: bool = False,
    ack_model_download: bool = False,
    command_runner: CommandRunner | None = None,
    base_python: str | None = None,
) -> dict[str, Any]:
    if not is_installed(plugin_id):
        return _error(
            "plugin_not_installed",
            f"Plugin '{plugin_id}' is not installed; run 'smcub plugin install {plugin_id}' first.",
            plugin_id,
        )
    return install_plugin(
        plugin_id,
        yes=yes,
        allow_network=allow_network,
        ack_third_party=ack_third_party,
        ack_model_download=ack_model_download,
        upgrade=True,
        command_runner=command_runner,
        base_python=base_python,
    )


def uninstall_plugin(
    plugin_id: str,
    *,
    yes: bool = False,
) -> dict[str, Any]:
    env.validate_plugin_id(plugin_id)
    if not yes:
        return _error(
            "confirmation_required",
            f"Uninstalling '{plugin_id}' removes its virtual environment. Re-run with --yes.",
            plugin_id,
        )
    home = env.plugin_home(plugin_id)
    if not home.exists():
        return _error(
            "plugin_not_installed",
            f"Plugin '{plugin_id}' is not installed.",
            plugin_id,
        )
    # Remove only the plugin's own environment and caches. User-generated
    # analysis results live outside the plugin home and are never touched.
    for sub in (".venv", "source", "cache", "logs"):
        target = env.safe_child_path(home, sub)
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
    for name in ("manifest.json",):
        target = env.safe_child_path(home, name)
        if target.exists():
            target.unlink()
    _write_install_state(plugin_id, {"status": "uninstalled", "uninstalled_at": _utc_now()})
    return redact(
        {
            "status": "ok",
            "plugin_id": plugin_id,
            "uninstalled": True,
            "user_results_preserved": True,
            "safety": SAFETY_DECLARATION,
        }
    )
