from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from smartmoney_cub.plugins.environment import PLUGIN_ID_RE
from smartmoney_cub.plugins.exceptions import ManifestValidationError, UnknownPluginError
from smartmoney_cub.plugins.status import CATALOG_ONLY_LEVELS, INTEGRATION_LEVELS
from smartmoney_cub.schemas import (
    PLUGIN_MANIFEST_SCHEMA,
    SAFETY_DECLARATION,
    VALID_ANALYSIS_HORIZONS,
    VALID_TARGET_TYPES,
)

MANIFESTS_DIR = Path(__file__).resolve().parent / "manifests"

REQUIRED_MANIFEST_FIELDS = (
    "schema",
    "id",
    "display_name",
    "description",
    "upstream_repo",
    "upstream_license",
    "capabilities",
    "supported_targets",
    "supported_horizons",
    "install_type",
    "install_spec",
    "requires_network",
    "requires_model_download",
    "requires_credentials",
    "required_environment_variables",
    "resource_profile",
    "runtime_status",
    "integration_level",
    "actionability",
    "safety",
)

ALLOWED_INSTALL_TYPES = frozenset({"pip", "git", "docker", "external", "none"})

# OSI-style licenses this catalog is willing to reference. Anything else must
# be reviewed by a human before it can be listed.
ALLOWED_LICENSES = frozenset(
    {
        "Apache-2.0",
        "MIT",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "MPL-2.0",
        "LGPL-2.1",
        "LGPL-3.0",
        "GPL-3.0",
        "AGPL-3.0",
    }
)

ALLOWED_ACTIONABILITY = frozenset({"review_only"})

CAPABILITY_VALUES = frozenset(
    {
        "market_data",
        "ohlcv_packet",
        "multi_agent_analysis",
        "llm_report",
        "quant_prediction",
        "cross_section_ranking",
        "zero_shot_forecast",
        "quantile_forecast",
        "backtest_readout",
        "data_health_check",
    }
)


def validate_plugin_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(manifest, dict):
        return {"ok": False, "errors": ["manifest_not_object"], "warnings": []}

    for field in REQUIRED_MANIFEST_FIELDS:
        if field not in manifest:
            errors.append(f"missing_{field}")

    if manifest.get("schema") != PLUGIN_MANIFEST_SCHEMA:
        errors.append("invalid_schema")

    plugin_id = manifest.get("id")
    if plugin_id is not None and (
        not isinstance(plugin_id, str) or not PLUGIN_ID_RE.match(plugin_id)
    ):
        errors.append("invalid_id")

    license_value = manifest.get("upstream_license")
    if "upstream_license" in manifest:
        if not license_value:
            errors.append("missing_upstream_license_value")
        elif license_value not in ALLOWED_LICENSES:
            errors.append(f"unsupported_license:{license_value}")

    if "install_type" in manifest and manifest.get("install_type") not in ALLOWED_INSTALL_TYPES:
        errors.append(f"invalid_install_type:{manifest.get('install_type')}")

    integration = manifest.get("integration_level")
    if "integration_level" in manifest and integration not in INTEGRATION_LEVELS:
        errors.append(f"invalid_integration_level:{integration}")

    if manifest.get("safety") != SAFETY_DECLARATION:
        errors.append("missing_or_invalid_safety_declaration")

    if "actionability" in manifest and manifest.get("actionability") not in ALLOWED_ACTIONABILITY:
        errors.append("invalid_actionability")

    targets = manifest.get("supported_targets")
    if targets is not None:
        if not isinstance(targets, list) or not targets:
            errors.append("invalid_supported_targets")
        else:
            for target in targets:
                if target not in VALID_TARGET_TYPES:
                    errors.append(f"invalid_target:{target}")

    horizons = manifest.get("supported_horizons")
    if horizons is not None:
        if not isinstance(horizons, list) or not horizons:
            errors.append("invalid_supported_horizons")
        else:
            for horizon in horizons:
                if horizon not in VALID_ANALYSIS_HORIZONS:
                    errors.append(f"invalid_horizon:{horizon}")

    capabilities = manifest.get("capabilities")
    if capabilities is not None:
        if not isinstance(capabilities, list) or not capabilities:
            errors.append("invalid_capabilities")
        else:
            for capability in capabilities:
                if capability not in CAPABILITY_VALUES:
                    warnings.append(f"unknown_capability:{capability}")

    resource_profile = manifest.get("resource_profile")
    if resource_profile is not None and not isinstance(resource_profile, dict):
        errors.append("invalid_resource_profile")

    env_vars = manifest.get("required_environment_variables")
    if env_vars is not None and not isinstance(env_vars, list):
        errors.append("invalid_required_environment_variables")

    for flag in ("requires_network", "requires_model_download", "requires_credentials"):
        if flag in manifest and not isinstance(manifest.get(flag), bool):
            errors.append(f"invalid_{flag}")

    if integration in CATALOG_ONLY_LEVELS and manifest.get("runtime_status") == "runtime_integrated":
        errors.append("catalog_only_plugin_claims_runtime_integration")

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def load_manifest_file(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(
            f"manifest is not valid JSON: {path.name}: {exc}",
        ) from exc
    result = validate_plugin_manifest(manifest)
    if not result["ok"]:
        raise ManifestValidationError(
            f"manifest {path.name} failed validation: {', '.join(result['errors'])}",
        )
    return manifest


def load_catalog(manifests_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    directory = manifests_dir or MANIFESTS_DIR
    catalog: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.json")):
        manifest = load_manifest_file(path)
        plugin_id = manifest["id"]
        if plugin_id in catalog:
            raise ManifestValidationError(
                f"duplicate plugin id in catalog: {plugin_id}",
                code="duplicate_plugin_id",
            )
        catalog[plugin_id] = manifest
    return catalog


def get_manifest(plugin_id: str, manifests_dir: Path | None = None) -> dict[str, Any]:
    catalog = load_catalog(manifests_dir)
    if plugin_id not in catalog:
        known = ", ".join(sorted(catalog))
        raise UnknownPluginError(
            f"unknown plugin: {plugin_id}; known plugins: {known}",
        )
    return catalog[plugin_id]
