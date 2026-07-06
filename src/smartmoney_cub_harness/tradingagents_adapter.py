from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from smartmoney_cub_harness.safety import redact
from smartmoney_cub_harness.schemas import SAFETY_DECLARATION, TRADINGAGENTS_REVIEW_PACKET_SCHEMA

SOURCE = "tradingagents"
ACTIONABILITY = "review_only"
SUPPORTED_MODES = {"report_only", "optional_local_bridge"}

LLM_PROVIDER_ENV = {
    "openai": ("OPENAI" + "_API_KEY",),
    "anthropic": ("ANTHROPIC" + "_API_KEY",),
    "deepseek": ("DEEPSEEK" + "_API_KEY",),
    "google": ("GOOGLE" + "_API_KEY", "GEMINI" + "_API_KEY"),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_report(path: str | Path) -> tuple[str, str]:
    report_path = Path(path)
    if not report_path.exists():
        raise FileNotFoundError(f"TradingAgents report not found: {report_path}")
    raw = report_path.read_text(encoding="utf-8")
    if report_path.suffix.lower() == ".json":
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return raw, raw
        return raw, _report_text_from_json(parsed)
    return raw, raw


def _report_text_from_json(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        preferred = (
            "report",
            "analysis",
            "summary",
            "decision",
            "debate_summary",
            "risk_notes",
            "watchlist_rationale",
        )
        chunks: list[str] = []
        for key in preferred:
            if key in value:
                chunks.append(f"{key}: {_report_text_from_json(value[key])}")
        if chunks:
            return "\n".join(chunks)
        return "\n".join(f"{key}: {_report_text_from_json(nested)}" for key, nested in value.items())
    if isinstance(value, list):
        return "\n".join(_report_text_from_json(item) for item in value)
    return str(value)


def _short_lines(text: str, *, limit: int = 4) -> list[str]:
    lines = []
    for line in text.splitlines():
        stripped = line.strip(" -#\t")
        if stripped:
            lines.append(stripped)
        if len(lines) >= limit:
            break
    return lines


def _risk_lines(text: str, *, limit: int = 5) -> list[str]:
    markers = (
        "risk",
        "uncertain",
        "uncertainty",
        "drawdown",
        "invalid",
        "invalidation",
        "volatility",
        "风险",
        "不确定",
        "回撤",
        "失效",
        "撤回",
    )
    hits = []
    for line in text.splitlines():
        stripped = line.strip(" -#\t")
        lowered = stripped.lower()
        if stripped and any(marker in lowered for marker in markers):
            hits.append(stripped)
        if len(hits) >= limit:
            break
    return hits or ["No explicit risk notes found in the imported report; reviewer must ask for missing risks."]


def _safe_excerpt(text: str, *, limit: int = 900) -> str:
    compact = "\n".join(_short_lines(text, limit=12))
    return compact[:limit]


def _report_sha256(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _provider_status(env: Mapping[str, str] | None = None) -> dict[str, bool]:
    source_env = os.environ if env is None else env
    return {
        provider: any(bool(source_env.get(name)) for name in names)
        for provider, names in LLM_PROVIDER_ENV.items()
    }


def build_tradingagents_review_packet(
    *,
    ticker: str,
    analysis_date: str,
    report_text: str,
    mode: str,
    report_path: str | Path | None = None,
    raw_report_text: str | None = None,
    provider: str | None = None,
    network_required: bool | None = None,
    external_llm_required: bool | None = None,
    status: str = "ok",
) -> dict[str, Any]:
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported TradingAgents adapter mode: {mode}")
    llm_required = mode == "optional_local_bridge" if external_llm_required is None else external_llm_required
    network = mode == "optional_local_bridge" if network_required is None else network_required
    raw_text = raw_report_text if raw_report_text is not None else report_text
    packet = {
        "schema": TRADINGAGENTS_REVIEW_PACKET_SCHEMA,
        "status": status,
        "source": SOURCE,
        "ticker": ticker,
        "analysis_date": analysis_date,
        "generated_at": _utc_now(),
        "mode": mode,
        "external_llm_required": bool(llm_required),
        "network_required": bool(network),
        "credentials_captured": False,
        "broker_execution": False,
        "actionability": ACTIONABILITY,
        "safety": SAFETY_DECLARATION,
        "report_path": Path(report_path).name if report_path else None,
        "report_sha256": _report_sha256(raw_text),
        "report_excerpt": _safe_excerpt(report_text),
        "evidence_summary": _short_lines(report_text),
        "risk_notes": _risk_lines(report_text),
        "reviewer_questions": [
            "Which claims are evidence-backed, and which need provenance before review?",
            "What data was available at the analysis date, and what may be future leakage?",
            "What D1/D3 outcome would confirm or weaken this thesis in a review-only workflow?",
        ],
        "challenger_questions": [
            "What opposing thesis would make this candidate report fail?",
            "Which missing risk would block a challenger rule from promotion?",
            "What evidence should be logged before any human considers rule evolution?",
        ],
        "human_gate": {
            "review_packet_only": True,
            "champion_promotion": "explicit_human_confirmation_required",
            "order_or_broker_action": "forbidden",
        },
    }
    if provider:
        packet["provider"] = provider
    return redact(packet)


def ingest_tradingagents_report(
    *,
    report: str | Path,
    ticker: str,
    analysis_date: str,
) -> dict[str, Any]:
    raw, report_text = _read_report(report)
    return build_tradingagents_review_packet(
        ticker=ticker,
        analysis_date=analysis_date,
        report_text=report_text,
        raw_report_text=raw,
        report_path=report,
        mode="report_only",
        network_required=False,
        external_llm_required=False,
    )


def check_tradingagents_environment(
    *,
    env: Mapping[str, str] | None = None,
    module_name: str = "tradingagents",
) -> dict[str, Any]:
    providers_configured = _provider_status(env)
    return {
        "status": "ok",
        "adapter": "tradingagents",
        "adapter_status": "optional",
        "tradingagents_installed": importlib.util.find_spec(module_name) is not None,
        "llm_providers_configured": providers_configured,
        "any_llm_provider_configured": any(providers_configured.values()),
        "credential_values_visible": False,
        "credentials_captured": False,
        "network_required": False,
        "external_api_required": False,
        "broker_api_required": False,
        "broker_execution": False,
        "default_mode": "report_only",
        "safety": SAFETY_DECLARATION,
    }


def _bridge_error(
    *,
    code: str,
    message: str,
    ticker: str,
    analysis_date: str,
    status: str = "error",
) -> dict[str, Any]:
    return redact(
        {
            "schema": TRADINGAGENTS_REVIEW_PACKET_SCHEMA,
            "status": status,
            "source": SOURCE,
            "ticker": ticker,
            "analysis_date": analysis_date,
            "generated_at": _utc_now(),
            "mode": "optional_local_bridge",
            "external_llm_required": True,
            "network_required": True,
            "credentials_captured": False,
            "broker_execution": False,
            "actionability": ACTIONABILITY,
            "error": {"code": code, "message": message},
            "safety": SAFETY_DECLARATION,
        }
    )


def _call_tradingagents_entrypoint(module: Any, **kwargs: Any) -> Any:
    for name in ("generate_report", "run_analysis", "analyze", "run"):
        candidate = getattr(module, name, None)
        if callable(candidate):
            try:
                return candidate(**kwargs)
            except TypeError:
                minimal = {
                    "ticker": kwargs["ticker"],
                    "analysis_date": kwargs["analysis_date"],
                }
                return candidate(**minimal)
    raise AttributeError("No supported TradingAgents entrypoint found")


def _bridge_result_to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return _report_text_from_json(value)


def run_tradingagents_local_bridge(
    *,
    ticker: str,
    analysis_date: str,
    allow_network: bool,
    ack_external_llm: bool,
    provider: str | None = None,
    deep_model: str | None = None,
    quick_model: str | None = None,
    max_debate_rounds: int | None = None,
    module_name: str = "tradingagents",
) -> dict[str, Any]:
    if not allow_network:
        return _bridge_error(
            code="network_not_allowed",
            message="TradingAgents local bridge is disabled until --allow-network is provided.",
            ticker=ticker,
            analysis_date=analysis_date,
        )
    if not ack_external_llm:
        return _bridge_error(
            code="external_llm_not_acknowledged",
            message="TradingAgents local bridge requires --ack-external-llm because the user-configured upstream may call an external LLM provider.",
            ticker=ticker,
            analysis_date=analysis_date,
        )

    if importlib.util.find_spec(module_name) is None:
        return _bridge_error(
            code="tradingagents_not_installed",
            message="TradingAgents is not installed in this environment; install and configure it locally before using optional bridge mode.",
            ticker=ticker,
            analysis_date=analysis_date,
            status="disabled",
        )

    try:
        module = importlib.import_module(module_name)
        bridge_output = _call_tradingagents_entrypoint(
            module,
            ticker=ticker,
            analysis_date=analysis_date,
            provider=provider,
            deep_model=deep_model,
            quick_model=quick_model,
            max_debate_rounds=max_debate_rounds,
            read_only=True,
        )
    except Exception as exc:  # pragma: no cover - depends on optional third-party runtime
        return _bridge_error(
            code="tradingagents_bridge_failed",
            message=f"TradingAgents optional bridge failed before producing a review packet: {exc.__class__.__name__}",
            ticker=ticker,
            analysis_date=analysis_date,
            status="error",
        )

    report_text = _bridge_result_to_text(bridge_output)
    return build_tradingagents_review_packet(
        ticker=ticker,
        analysis_date=analysis_date,
        report_text=report_text,
        raw_report_text=report_text,
        report_path=None,
        mode="optional_local_bridge",
        provider=provider,
        network_required=True,
        external_llm_required=True,
    )
