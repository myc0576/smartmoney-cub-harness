from __future__ import annotations

SAFETY_DECLARATION = "READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE"

PACKAGE_NAME = "smartmoney-cub"
PACKAGE_IMPORT_NAME = "smartmoney_cub"

MANIFEST_SCHEMA = "smartmoney_cub_run_manifest.v1"
DECISION_SCHEMA = "smartmoney_cub_decision.v1"
OUTCOME_SCHEMA = "smartmoney_cub_outcome.v1"
REGISTRY_SCHEMA = "smartmoney_cub_rule_registry.v1"
CASE_SCHEMA = "smartmoney_cub_case_record.v1"
LEDGER_SCHEMA = "smartmoney_cub_evolution_ledger.v1"
MEMORY_SCHEMA = "smartmoney_cub_markdown_memory.v1"
PRIVATE_CASE_CSV_SCHEMA = "smartmoney_cub_private_case_csv.v1"
SELF_EVOLVE_CONTRACT_SCHEMA = "smartmoney_cub_self_evolve_contract.v1"
SELF_EVOLVE_STATE_SCHEMA = "smartmoney_cub_self_evolve_state.v1"
PROMOTION_PACKET_SCHEMA = "smartmoney_cub_promotion_packet.v1"
TRADINGAGENTS_REVIEW_PACKET_SCHEMA = "smartmoney_cub_tradingagents_review_packet.v1"

PLUGIN_MANIFEST_SCHEMA = "smartmoney_cub_plugin_manifest.v1"
PLUGIN_REGISTRY_SCHEMA = "smartmoney_cub_plugin_registry.v1"
PLUGIN_INSTALL_STATE_SCHEMA = "smartmoney_cub_plugin_install_state.v1"
ANALYSIS_REQUEST_SCHEMA = "smartmoney_cub_analysis_request.v1"
MARKET_DATA_PACKET_SCHEMA = "smartmoney_cub_market_data_packet.v1"
FORECAST_EVIDENCE_PACKET_SCHEMA = "smartmoney_cub_forecast_evidence_packet.v1"
MULTI_PLUGIN_ANALYSIS_SCHEMA = "smartmoney_cub_multi_plugin_analysis.v1"

VALID_TARGET_TYPES = {"stock", "index", "sector"}
VALID_ANALYSIS_HORIZONS = {"intraday", "d1", "d3", "d5", "d10", "d20"}

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

