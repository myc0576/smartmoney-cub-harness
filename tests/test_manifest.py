from __future__ import annotations

from smartmoney_cub_harness.manifest import validate_run_manifest
from smartmoney_cub_harness.schemas import SAFETY_DECLARATION


def valid_manifest() -> dict:
    return {
        "schema": "smartmoney_cub_run_manifest.v1",
        "run_id": "toy-after-close",
        "decision_time": "2026-06-01T15:30:00+08:00",
        "mode": "after-close",
        "safety": SAFETY_DECLARATION,
        "data_sources": [
            {
                "name": "toy_strategy",
                "fetch_time": "2026-06-01T15:29:58+08:00",
                "available_at": "2026-06-01T15:30:00+08:00",
                "data_quality_flag": "ok",
            }
        ],
    }


def test_manifest_accepts_valid_manifest():
    result = validate_run_manifest(valid_manifest())

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["safety"] == SAFETY_DECLARATION


def test_manifest_rejects_future_available_data():
    manifest = valid_manifest()
    manifest["data_sources"][0]["available_at"] = "2026-06-01T15:31:00+08:00"

    result = validate_run_manifest(manifest)

    assert result["ok"] is False
    assert "future_leakage:toy_strategy" in result["errors"]


def test_manifest_rejects_missing_quality_flag():
    manifest = valid_manifest()
    del manifest["data_sources"][0]["data_quality_flag"]

    result = validate_run_manifest(manifest)

    assert result["ok"] is False
    assert "missing_data_quality_flag:toy_strategy" in result["errors"]


def test_manifest_requires_safety_declaration():
    manifest = valid_manifest()
    del manifest["safety"]

    result = validate_run_manifest(manifest)

    assert result["ok"] is False
    assert "missing_or_invalid_safety_declaration" in result["errors"]
