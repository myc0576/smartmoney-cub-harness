from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from smartmoney_cub.plugins import environment as env
from smartmoney_cub.plugins.catalog import load_catalog
from smartmoney_cub.plugins.exceptions import PluginError, UnknownPluginError
from smartmoney_cub.plugins.installer import is_installed, read_install_state
from smartmoney_cub.plugins.status import (
    INTEGRATION_RUNTIME,
    STATUS_CREDENTIALS_MISSING,
    STATUS_DATA_MISSING,
    STATUS_DISABLED,
    STATUS_INSTALLED_UNCONFIGURED,
    STATUS_NOT_INSTALLED,
    STATUS_READY,
)
from smartmoney_cub.safety import looks_sensitive_key, redact
from smartmoney_cub.schemas import PLUGIN_REGISTRY_SCHEMA, SAFETY_DECLARATION


def _load_registry() -> dict[str, Any]:
    path = env.registry_path()
    if not path.exists():
        return {"schema": PLUGIN_REGISTRY_SCHEMA, "plugins": {}, "safety": SAFETY_DECLARATION}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"schema": PLUGIN_REGISTRY_SCHEMA, "plugins": {}, "safety": SAFETY_DECLARATION}


def _save_registry(registry: dict[str, Any]) -> None:
    path = env.registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    registry["schema"] = PLUGIN_REGISTRY_SCHEMA
    registry["safety"] = SAFETY_DECLARATION
    path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_enabled(plugin_id: str) -> bool:
    registry = _load_registry()
    entry = registry.get("plugins", {}).get(plugin_id, {})
    return bool(entry.get("enabled", True))


def set_enabled(plugin_id: str, enabled: bool) -> dict[str, Any]:
    env.validate_plugin_id(plugin_id)
    try:
        catalog = load_catalog()
    except PluginError as exc:
        return redact({"status": "error", "error": exc.to_payload(), "safety": SAFETY_DECLARATION})
    if plugin_id not in catalog:
        return redact(
            {
                "status": "error",
                "error": {
                    "code": "unknown_plugin",
                    "message": f"unknown plugin: {plugin_id}",
                },
                "safety": SAFETY_DECLARATION,
            }
        )
    if not is_installed(plugin_id):
        return redact(
            {
                "status": "error",
                "plugin_id": plugin_id,
                "error": {
                    "code": "plugin_not_installed",
                    "message": (
                        f"Plugin '{plugin_id}' is not installed; "
                        f"run 'smcub plugin install {plugin_id}' first."
                    ),
                },
                "safety": SAFETY_DECLARATION,
            }
        )
    registry = _load_registry()
    registry.setdefault("plugins", {}).setdefault(plugin_id, {})["enabled"] = bool(enabled)
    _save_registry(registry)
    return redact(
        {
            "status": "ok",
            "plugin_id": plugin_id,
            "enabled": bool(enabled),
            "safety": SAFETY_DECLARATION,
        }
    )


def load_plugin_config(plugin_id: str) -> dict[str, Any]:
    path = env.plugin_config_path(plugin_id)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def configure_plugin(plugin_id: str, key: str, value: str) -> dict[str, Any]:
    env.validate_plugin_id(plugin_id)
    if looks_sensitive_key(key):
        return redact(
            {
                "status": "error",
                "plugin_id": plugin_id,
                "error": {
                    "code": "credentials_must_use_environment_variables",
                    "message": (
                        "API keys and other credentials are never stored in "
                        "SmartMoney-Cub config files. Export them as environment "
                        "variables instead."
                    ),
                },
                "safety": SAFETY_DECLARATION,
            }
        )
    config = load_plugin_config(plugin_id)
    config[key] = value
    path = env.plugin_config_path(plugin_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return redact(
        {
            "status": "ok",
            "plugin_id": plugin_id,
            "configured_keys": sorted(config),
            "safety": SAFETY_DECLARATION,
        }
    )


def _credential_status(
    manifest: Mapping[str, Any], environ: Mapping[str, str]
) -> list[dict[str, Any]]:
    entries = []
    for name in manifest.get("required_environment_variables", []) or []:
        entries.append(
            {
                "name": name,
                "configured": bool(environ.get(name)),
                "credential_value_visible": False,
            }
        )
    return entries


def compute_plugin_status(
    plugin_id: str,
    manifest: Mapping[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
) -> str:
    environ = os.environ if environ is None else environ
    if not is_installed(plugin_id):
        return STATUS_NOT_INSTALLED
    if not is_enabled(plugin_id):
        return STATUS_DISABLED
    state = read_install_state(plugin_id) or {}
    raw_status = state.get("status")
    if raw_status in ("installing", "dependency_error", "error", "incompatible"):
        return str(raw_status)
    if manifest.get("requires_credentials"):
        creds = _credential_status(manifest, environ)
        if creds and not any(item["configured"] for item in creds):
            return STATUS_CREDENTIALS_MISSING
    config = load_plugin_config(plugin_id)
    if plugin_id == "qlib":
        data_dir = config.get("data_dir")
        if not data_dir:
            return STATUS_INSTALLED_UNCONFIGURED
        if not Path(str(data_dir)).exists():
            return STATUS_DATA_MISSING
    if raw_status == STATUS_INSTALLED_UNCONFIGURED and manifest.get("requires_credentials"):
        return STATUS_READY
    if raw_status == STATUS_INSTALLED_UNCONFIGURED and plugin_id != "qlib":
        return STATUS_READY
    return STATUS_READY


def list_plugins(*, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    try:
        catalog = load_catalog()
    except PluginError as exc:
        return redact({"status": "error", "error": exc.to_payload(), "safety": SAFETY_DECLARATION})
    rows = []
    for plugin_id, manifest in sorted(catalog.items()):
        rows.append(
            {
                "id": plugin_id,
                "display_name": manifest.get("display_name"),
                "integration_level": manifest.get("integration_level"),
                "capabilities": manifest.get("capabilities", []),
                "install_type": manifest.get("install_type"),
                "requires_network": manifest.get("requires_network"),
                "requires_credentials": manifest.get("requires_credentials"),
                "requires_model_download": manifest.get("requires_model_download"),
                "upstream_license": manifest.get("upstream_license"),
                "status": (
                    compute_plugin_status(plugin_id, manifest, environ=environ)
                    if manifest.get("integration_level") == INTEGRATION_RUNTIME
                    else manifest.get("integration_level")
                ),
            }
        )
    return redact(
        {
            "status": "ok",
            "plugins": rows,
            "count": len(rows),
            "safety": SAFETY_DECLARATION,
        }
    )


def plugin_info(plugin_id: str) -> dict[str, Any]:
    try:
        catalog = load_catalog()
    except PluginError as exc:
        return redact({"status": "error", "error": exc.to_payload(), "safety": SAFETY_DECLARATION})
    manifest = catalog.get(plugin_id)
    if manifest is None:
        return redact(
            {
                "status": "error",
                "error": {"code": "unknown_plugin", "message": f"unknown plugin: {plugin_id}"},
                "known_plugins": sorted(catalog),
                "safety": SAFETY_DECLARATION,
            }
        )
    return redact(
        {
            "status": "ok",
            "manifest": dict(manifest),
            "installed": is_installed(plugin_id),
            "enabled": is_enabled(plugin_id),
            "plugin_status": compute_plugin_status(plugin_id, manifest),
            "install_state": read_install_state(plugin_id),
            "ownership_note": (
                "SmartMoney-Cub does not own or maintain this upstream project. "
                "It is maintained by its own community under its own license."
            ),
            "safety": SAFETY_DECLARATION,
        }
    )


def plugin_doctor(
    plugin_id: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    environ = os.environ if environ is None else environ
    try:
        catalog = load_catalog()
    except PluginError as exc:
        return redact({"status": "error", "error": exc.to_payload(), "safety": SAFETY_DECLARATION})
    if plugin_id is not None and plugin_id not in catalog:
        return redact(
            {
                "status": "error",
                "error": {"code": "unknown_plugin", "message": f"unknown plugin: {plugin_id}"},
                "safety": SAFETY_DECLARATION,
            }
        )
    targets = {plugin_id: catalog[plugin_id]} if plugin_id else catalog
    reports = []
    for pid, manifest in sorted(targets.items()):
        report: dict[str, Any] = {
            "id": pid,
            "integration_level": manifest.get("integration_level"),
            "installed": is_installed(pid),
            "enabled": is_enabled(pid),
            "status": (
                compute_plugin_status(pid, manifest, environ=environ)
                if manifest.get("integration_level") == INTEGRATION_RUNTIME
                else manifest.get("integration_level")
            ),
            "venv_present": env.plugin_python_executable(pid).exists(),
            "credentials": _credential_status(manifest, environ),
            "config_keys": sorted(load_plugin_config(pid)),
        }
        reports.append(report)
    return redact(
        {
            "status": "ok",
            "reports": reports,
            "credential_values_visible": False,
            "safety": SAFETY_DECLARATION,
        }
    )
