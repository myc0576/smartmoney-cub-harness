from __future__ import annotations

SAFETY_DECLARATION = "READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE"

PACKAGE_NAME = "smartmoney-cub-harness"
PACKAGE_IMPORT_NAME = "smartmoney_cub_harness"

MANIFEST_SCHEMA = "smartmoney_cub_run_manifest.v1"
DECISION_SCHEMA = "smartmoney_cub_decision.v1"
OUTCOME_SCHEMA = "smartmoney_cub_outcome.v1"
REGISTRY_SCHEMA = "smartmoney_cub_rule_registry.v1"
CASE_SCHEMA = "smartmoney_cub_case_record.v1"
LEDGER_SCHEMA = "smartmoney_cub_evolution_ledger.v1"

VALID_ACTION_LABELS = {"SILENT", "ALERT", "ERROR", "WATCH", "AVOID", "EMPTY_POSITION"}
VALID_DATA_QUALITY_FLAGS = {"ok", "stale", "partial", "missing", "error"}
VALID_HORIZONS = {"d1": 1, "d3": 3}

REQUIRED_MANIFEST_FIELDS = ("schema", "run_id", "decision_time", "mode", "data_sources")
REQUIRED_SOURCE_FIELDS = ("name", "fetch_time", "available_at", "data_quality_flag")

REQUIRED_ALERT_DECISION_FIELDS = (
    "invalidation_price",
    "time_stop",
    "give_up_conditions",
    "data_source",
    "available_at",
    "data_quality_flag",
)
