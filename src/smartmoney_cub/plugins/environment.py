from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from smartmoney_cub.plugins.exceptions import PluginSecurityError

HOME_ENV_VAR = "SMARTMONEY_CUB_HOME"

PLUGIN_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")

# Conservative allowlist for values that end up in subprocess argument lists.
SAFE_INSTALL_SPEC_RE = re.compile(r"^[A-Za-z0-9._+:/@=\-\[\],~<>!]+$")
SAFE_SYMBOL_RE = re.compile(r"^[A-Za-z0-9._^\-]{1,24}$")


def smartmoney_home() -> Path:
    override = os.environ.get(HOME_ENV_VAR)
    if override:
        return Path(override)
    return Path.home() / ".smartmoney-cub"


def config_root() -> Path:
    return smartmoney_home() / "config"


def plugins_root() -> Path:
    return smartmoney_home() / "plugins"


def registry_path() -> Path:
    return plugins_root() / "registry.json"


def validate_plugin_id(plugin_id: str) -> str:
    if not isinstance(plugin_id, str) or not PLUGIN_ID_RE.match(plugin_id):
        raise PluginSecurityError(
            f"invalid plugin id: {plugin_id!r}; expected lowercase [a-z0-9_], max 40 chars",
            code="invalid_plugin_id",
        )
    return plugin_id


def validate_install_spec(spec: str) -> str:
    if not isinstance(spec, str) or not spec or not SAFE_INSTALL_SPEC_RE.match(spec):
        raise PluginSecurityError(
            f"install spec contains unsupported characters: {spec!r}",
            code="invalid_install_spec",
        )
    if spec.startswith("-"):
        raise PluginSecurityError(
            f"install spec must not start with '-': {spec!r}",
            code="invalid_install_spec",
        )
    return spec


def validate_symbol(symbol: str) -> str:
    if not isinstance(symbol, str) or not SAFE_SYMBOL_RE.match(symbol):
        raise PluginSecurityError(
            f"invalid target symbol: {symbol!r}",
            code="invalid_symbol",
        )
    return symbol


def safe_child_path(base: Path, *parts: str) -> Path:
    """Join path parts under ``base`` and refuse traversal outside it."""

    base_resolved = base.resolve()
    candidate = base_resolved.joinpath(*parts).resolve()
    try:
        candidate.relative_to(base_resolved)
    except ValueError as exc:
        raise PluginSecurityError(
            f"path escapes plugin root: {candidate}",
            code="path_traversal_blocked",
        ) from exc
    return candidate


def plugin_home(plugin_id: str) -> Path:
    validate_plugin_id(plugin_id)
    return safe_child_path(plugins_root(), plugin_id)


def plugin_venv_dir(plugin_id: str) -> Path:
    return plugin_home(plugin_id) / ".venv"


def plugin_python_executable(plugin_id: str) -> Path:
    venv = plugin_venv_dir(plugin_id)
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def plugin_install_state_path(plugin_id: str) -> Path:
    return plugin_home(plugin_id) / "install_state.json"


def plugin_manifest_copy_path(plugin_id: str) -> Path:
    return plugin_home(plugin_id) / "manifest.json"


def plugin_logs_dir(plugin_id: str) -> Path:
    return plugin_home(plugin_id) / "logs"


def plugin_cache_dir(plugin_id: str) -> Path:
    return plugin_home(plugin_id) / "cache"


def plugin_source_dir(plugin_id: str) -> Path:
    return plugin_home(plugin_id) / "source"


def plugin_config_path(plugin_id: str) -> Path:
    validate_plugin_id(plugin_id)
    return safe_child_path(config_root(), f"{plugin_id}.json")
