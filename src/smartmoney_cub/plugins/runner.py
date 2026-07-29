from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

from smartmoney_cub.plugins import environment as env
from smartmoney_cub.plugins.catalog import load_catalog
from smartmoney_cub.plugins.exceptions import PluginError
from smartmoney_cub.plugins.installer import is_installed
from smartmoney_cub.plugins.manager import is_enabled, load_plugin_config
from smartmoney_cub.plugins.protocol import (
    build_multi_plugin_analysis,
    validate_analysis_request,
)
from smartmoney_cub.plugins.status import INTEGRATION_RUNTIME
from smartmoney_cub.safety import redact
from smartmoney_cub.schemas import SAFETY_DECLARATION

# Adapter entry modules run inside the plugin's own virtual environment via
# `python -m <module>` with the host src directory on PYTHONPATH. Adapters may
# only import stdlib at module import time; heavy upstream imports happen
# lazily inside functions.
ADAPTER_MODULES: dict[str, str] = {
    "akshare": "smartmoney_cub.plugins.adapters.akshare_adapter",
    "tradingagents": "smartmoney_cub.plugins.adapters.tradingagents_adapter",
    "qlib": "smartmoney_cub.plugins.adapters.qlib_adapter",
    "chronos2": "smartmoney_cub.plugins.adapters.chronos2_adapter",
}

SubprocessRunner = Callable[[Sequence[str], str, dict[str, str]], tuple[int, str, str]]

_HOST_SRC = str(Path(__file__).resolve().parents[2])


def _default_subprocess_runner(
    argv: Sequence[str], input_json: str, extra_env: dict[str, str]
) -> tuple[int, str, str]:
    merged_env = dict(os.environ)
    merged_env.update(extra_env)
    completed = subprocess.run(  # noqa: S603 - argv validated by caller
        list(argv),
        shell=False,
        input=input_json,
        capture_output=True,
        text=True,
        check=False,
        timeout=1800,
        env=merged_env,
    )
    return completed.returncode, completed.stdout, completed.stderr


def _error(code: str, message: str, plugin_id: str | None = None, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "error",
        "error": {"code": code, "message": message},
        "safety": SAFETY_DECLARATION,
    }
    if plugin_id:
        payload["plugin_id"] = plugin_id
    payload.update(extra)
    return redact(payload)


def run_plugin(
    plugin_id: str,
    request: dict[str, Any],
    *,
    subprocess_runner: SubprocessRunner | None = None,
) -> dict[str, Any]:
    """Run one plugin adapter in its isolated venv over JSON stdin/stdout."""

    try:
        env.validate_plugin_id(plugin_id)
        catalog = load_catalog()
    except PluginError as exc:
        return _error(exc.code, str(exc), plugin_id)

    manifest = catalog.get(plugin_id)
    if manifest is None:
        return _error("unknown_plugin", f"unknown plugin: {plugin_id}", plugin_id)
    if manifest.get("integration_level") != INTEGRATION_RUNTIME:
        return _error(
            "plugin_not_runtime_integrated",
            f"Plugin '{plugin_id}' is catalog-only ({manifest.get('integration_level')}); "
            "no runtime adapter exists yet.",
            plugin_id,
        )
    if not is_installed(plugin_id):
        return _error(
            "plugin_not_installed",
            f"Plugin '{plugin_id}' is not installed. Install it explicitly with: "
            f"smcub plugin install {plugin_id} --yes --ack-third-party"
            + (" --allow-network" if manifest.get("requires_network") else "")
            + (" --ack-model-download" if manifest.get("requires_model_download") else ""),
            plugin_id,
        )
    if not is_enabled(plugin_id):
        return _error(
            "plugin_disabled",
            f"Plugin '{plugin_id}' is disabled; run 'smcub plugin enable {plugin_id}'.",
            plugin_id,
        )
    if manifest.get("requires_network") and not request.get("network_allowed"):
        return _error(
            "network_not_allowed",
            f"Plugin '{plugin_id}' requires network access; re-run with --allow-network.",
            plugin_id,
        )

    module = ADAPTER_MODULES.get(plugin_id)
    if module is None:
        return _error(
            "adapter_missing",
            f"No adapter module registered for plugin '{plugin_id}'.",
            plugin_id,
        )

    plugin_python = env.plugin_python_executable(plugin_id)
    if not plugin_python.exists():
        return _error(
            "plugin_venv_missing",
            f"Virtual environment for '{plugin_id}' is missing; reinstall the plugin.",
            plugin_id,
        )

    plugin_request = dict(request)
    plugin_request["plugin_config"] = load_plugin_config(plugin_id)

    runner = subprocess_runner or _default_subprocess_runner
    argv = [str(plugin_python), "-m", module]
    extra_env = {
        "PYTHONPATH": _HOST_SRC + os.pathsep + os.environ.get("PYTHONPATH", ""),
        "PYTHONIOENCODING": "utf-8",
    }
    try:
        returncode, stdout, stderr = runner(argv, json.dumps(plugin_request), extra_env)
    except subprocess.TimeoutExpired:
        return _error("plugin_timeout", f"Plugin '{plugin_id}' timed out.", plugin_id)
    except OSError as exc:
        return _error(
            "plugin_process_error",
            f"Failed to start plugin '{plugin_id}': {exc.__class__.__name__}",
            plugin_id,
        )

    if returncode != 0:
        return _error(
            "plugin_execution_failed",
            f"Plugin '{plugin_id}' exited with code {returncode}. "
            "Check plugin logs; stderr is not echoed to avoid leaking secrets.",
            plugin_id,
        )
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return _error(
            "plugin_protocol_error",
            f"Plugin '{plugin_id}' did not return valid JSON on stdout.",
            plugin_id,
        )
    return redact(payload)


def run_analysis(
    request: dict[str, Any],
    *,
    plugin_runner: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the requested data provider and plugins, then aggregate results."""

    check = validate_analysis_request(request)
    if not check["ok"]:
        return _error(
            "invalid_analysis_request",
            "analysis request failed validation: " + ", ".join(check["errors"]),
        )

    runner = plugin_runner or (lambda pid, req: run_plugin(pid, req))
    working_request = dict(request)

    provider = working_request.get("data_provider")
    if provider and "input_data" not in working_request:
        provider_result = runner(provider, working_request)
        if provider_result.get("status") == "ok" and "market_data" in provider_result:
            working_request["input_data"] = provider_result["market_data"]
        else:
            return redact(
                {
                    "status": "error",
                    "error": {
                        "code": "data_provider_failed",
                        "message": f"data provider '{provider}' did not return market data",
                    },
                    "provider_result": provider_result,
                    "safety": SAFETY_DECLARATION,
                }
            )

    packets: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for plugin_id in working_request.get("plugins", []):
        result = runner(plugin_id, working_request)
        if result.get("status") == "ok" and "evidence_packet" in result:
            packets.append(result["evidence_packet"])
        else:
            errors.append(result)

    report = build_multi_plugin_analysis(request, packets, errors)
    return redact(report)
