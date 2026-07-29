from __future__ import annotations

import json
from pathlib import Path

import pytest

from smartmoney_cub.plugins.catalog import (
    MANIFESTS_DIR,
    load_catalog,
    load_manifest_file,
    validate_plugin_manifest,
)
from smartmoney_cub.plugins.exceptions import ManifestValidationError
from smartmoney_cub.plugins.status import (
    INTEGRATION_CATALOG,
    INTEGRATION_RUNTIME,
)
from smartmoney_cub.schemas import SAFETY_DECLARATION


def _valid_manifest() -> dict:
    return json.loads((MANIFESTS_DIR / "akshare.json").read_text(encoding="utf-8"))


# --- category 1: manifest schema validation ---


def test_bundled_manifests_are_all_valid():
    for path in sorted(MANIFESTS_DIR.glob("*.json")):
        manifest = load_manifest_file(path)
        result = validate_plugin_manifest(manifest)
        assert result["ok"] is True, f"{path.name}: {result['errors']}"
        assert manifest["safety"] == SAFETY_DECLARATION


def test_manifest_missing_required_field_rejected():
    manifest = _valid_manifest()
    del manifest["upstream_repo"]
    result = validate_plugin_manifest(manifest)
    assert result["ok"] is False
    assert "missing_upstream_repo" in result["errors"]


def test_manifest_wrong_schema_rejected():
    manifest = _valid_manifest()
    manifest["schema"] = "totally_wrong.v9"
    result = validate_plugin_manifest(manifest)
    assert result["ok"] is False
    assert "invalid_schema" in result["errors"]


def test_manifest_invalid_id_rejected():
    manifest = _valid_manifest()
    manifest["id"] = "../evil"
    result = validate_plugin_manifest(manifest)
    assert result["ok"] is False
    assert "invalid_id" in result["errors"]


# --- category 2: catalog loading ---


def test_catalog_loads_first_batch_plugins():
    catalog = load_catalog()
    for expected in (
        "akshare",
        "tradingagents",
        "qlib",
        "chronos2",
        "timesfm",
        "neuralforecast",
        "finrobot",
    ):
        assert expected in catalog
    for plugin_id, manifest in catalog.items():
        assert manifest["id"] == plugin_id


def test_catalog_only_plugins_are_not_runtime_integrated():
    catalog = load_catalog()
    assert catalog["timesfm"]["integration_level"] == INTEGRATION_CATALOG
    assert catalog["neuralforecast"]["integration_level"] == INTEGRATION_CATALOG
    assert catalog["finrobot"]["integration_level"] != INTEGRATION_RUNTIME


# --- category 3: duplicate plugin id ---


def test_duplicate_plugin_id_raises(tmp_path: Path):
    manifest = _valid_manifest()
    (tmp_path / "a.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ManifestValidationError):
        load_catalog(tmp_path)


# --- category 4: license allowlist / integrity rules ---


def test_unsupported_license_rejected():
    manifest = _valid_manifest()
    manifest["upstream_license"] = "Proprietary-EULA"
    result = validate_plugin_manifest(manifest)
    assert result["ok"] is False
    assert any(e.startswith("unsupported_license") for e in result["errors"])


def test_catalog_only_manifest_cannot_claim_runtime_integration():
    manifest = _valid_manifest()
    manifest["id"] = "timesfm"
    manifest["integration_level"] = INTEGRATION_CATALOG
    manifest["runtime_status"] = "runtime_integrated"
    result = validate_plugin_manifest(manifest)
    assert result["ok"] is False
    assert "catalog_only_plugin_claims_runtime_integration" in result["errors"]


def test_all_manifests_declare_read_only_safety():
    for path in sorted(MANIFESTS_DIR.glob("*.json")):
        manifest = load_manifest_file(path)
        assert manifest["safety"] == "READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE"
        assert manifest.get("actionability", "review_only") == "review_only"
