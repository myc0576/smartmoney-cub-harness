"""TradingAgents adapter using the official Python API.

Preferred path::

    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.default_config import DEFAULT_CONFIG

    config = DEFAULT_CONFIG.copy()
    ta = TradingAgentsGraph(debug=False, config=config)
    _, decision = ta.propagate(symbol, analysis_date)

A legacy entrypoint fallback is retained for older installs. API keys are read
only from the user's environment by the upstream package; this adapter never
logs or embeds them. The upstream BUY/SELL text is preserved verbatim as an
LLM interpretation for review, never converted into any order intent, and
never wrapped into a calibrated probability.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from smartmoney_cub.plugins.protocol import build_evidence_packet
from smartmoney_cub.schemas import SAFETY_DECLARATION

PLUGIN_ID = "tradingagents"
UPSTREAM_REPO = "https://github.com/TauricResearch/TradingAgents"
UPSTREAM_LICENSE = "Apache-2.0"

# Providers the upstream project supports via its config. Values are the
# config keys used by TradingAgents' DEFAULT_CONFIG.
SUPPORTED_PROVIDERS = (
    "openai",
    "google",
    "anthropic",
    "deepseek",
    "qwen",
    "glm",
    "minimax",
    "openrouter",
    "ollama",
    "openai_compatible",
)

LEGACY_ENTRYPOINTS = ("generate_report", "run_analysis", "analyze", "run")


def _error(code: str, message: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "error",
        "plugin_id": PLUGIN_ID,
        "error": {"code": code, "message": message},
        "safety": SAFETY_DECLARATION,
    }
    payload.update(extra)
    return payload


def _build_config(default_config: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    config = dict(default_config)
    provider = options.get("provider")
    if provider:
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"unsupported provider: {provider}")
        config["llm_provider"] = provider
    if options.get("backend_url"):
        config["backend_url"] = str(options["backend_url"])
    if options.get("deep_model"):
        config["deep_think_llm"] = str(options["deep_model"])
    if options.get("quick_model"):
        config["quick_think_llm"] = str(options["quick_model"])
    if options.get("max_debate_rounds") is not None:
        config["max_debate_rounds"] = int(options["max_debate_rounds"])
    config["online_tools"] = bool(options.get("online_tools", True))
    return config


def _decision_to_text(decision: Any) -> str:
    if isinstance(decision, str):
        return decision
    try:
        return json.dumps(decision, ensure_ascii=False, default=str)
    except TypeError:
        return str(decision)


def _direction_from_text(text: str) -> str:
    lowered = text.lower()
    has_buy = "buy" in lowered or "bullish" in lowered
    has_sell = "sell" in lowered or "bearish" in lowered
    if has_buy and not has_sell:
        return "up"
    if has_sell and not has_buy:
        return "down"
    if "hold" in lowered or "neutral" in lowered:
        return "flat"
    return "mixed" if (has_buy and has_sell) else "unstated"


def _run_official_api(
    ta_graph_cls: Any,
    default_config: dict[str, Any],
    symbol: str,
    analysis_date: str,
    options: dict[str, Any],
) -> tuple[Any, Any]:
    config = _build_config(default_config, options)
    graph = ta_graph_cls(debug=False, config=config)
    return graph.propagate(symbol, analysis_date)


def _run_legacy(module: Any, symbol: str, analysis_date: str) -> Any:
    for name in LEGACY_ENTRYPOINTS:
        candidate = getattr(module, name, None)
        if callable(candidate):
            try:
                return candidate(ticker=symbol, analysis_date=analysis_date)
            except TypeError:
                return candidate(symbol, analysis_date)
    raise AttributeError("no legacy TradingAgents entrypoint found")


def run_request(request: dict[str, Any], *, deps: dict[str, Any] | None = None) -> dict[str, Any]:
    target = request.get("target") or {}
    symbol = str(target.get("symbol", ""))
    analysis_date = str(request.get("as_of", ""))[:10]
    options = dict(request.get("options") or {})

    graph_cls = None
    default_config: dict[str, Any] | None = None
    legacy_module = None

    if deps is not None:
        graph_cls = deps.get("trading_agents_graph_cls")
        default_config = deps.get("default_config")
        legacy_module = deps.get("legacy_module")
    else:  # pragma: no cover - requires real upstream install
        try:
            from tradingagents.graph.trading_graph import (  # type: ignore[import-not-found]  # noqa: PLC0415
                TradingAgentsGraph,
            )
            from tradingagents.default_config import (  # type: ignore[import-not-found]  # noqa: PLC0415
                DEFAULT_CONFIG,
            )

            graph_cls = TradingAgentsGraph
            default_config = dict(DEFAULT_CONFIG)
        except ImportError:
            try:
                import tradingagents as legacy_module  # type: ignore[import-not-found]  # noqa: PLC0415
            except ImportError:
                return _error(
                    "tradingagents_not_installed",
                    "TradingAgents is not importable inside this plugin environment.",
                )

    raw_output: Any = None
    api_path = "official"
    if graph_cls is not None and default_config is not None:
        try:
            _, decision = _run_official_api(
                graph_cls, default_config, symbol, analysis_date, options
            )
            raw_output = decision
        except ValueError as exc:
            return _error("invalid_options", str(exc))
        except Exception as exc:
            return _error(
                "tradingagents_run_failed",
                "TradingAgents official API failed before producing a decision: "
                f"{exc.__class__.__name__}. Check provider configuration and "
                "environment variables (values are never logged).",
            )
    elif legacy_module is not None:
        api_path = "legacy"
        try:
            raw_output = _run_legacy(legacy_module, symbol, analysis_date)
        except Exception as exc:
            return _error(
                "tradingagents_legacy_failed",
                f"Legacy TradingAgents entrypoint failed: {exc.__class__.__name__}",
            )
    else:
        return _error(
            "tradingagents_not_installed",
            "TradingAgents is not importable inside this plugin environment.",
        )

    decision_text = _decision_to_text(raw_output)
    packet = build_evidence_packet(
        plugin_id=PLUGIN_ID,
        plugin_version=str(options.get("plugin_version", "unknown")),
        upstream_repo=UPSTREAM_REPO,
        upstream_license=UPSTREAM_LICENSE,
        target=target,
        as_of=str(request.get("as_of", "")),
        horizon=str(request.get("horizon", "d5")),
        input_data={"symbol": symbol, "analysis_date": analysis_date},
        data_sources=[
            {
                "name": "tradingagents_upstream_tools",
                "note": "data access is managed by the upstream framework",
            }
        ],
        data_quality="unverified_by_host",
        model_identifier=str(
            options.get("deep_model") or options.get("provider") or "user_configured_llm"
        ),
        forecast={
            "direction": _direction_from_text(decision_text),
            "decision_text": decision_text[:4000],
            "quantiles": {},
            "calibrated": False,
        },
        evidence=[line.strip() for line in decision_text.splitlines() if line.strip()][:8]
        or ["decision text was empty"],
        output_kind="llm_interpretation",
        counter_evidence=[],
        risks=[
            "LLM narratives can be fluent but wrong; verify every claim against data.",
        ],
        missing_information=["upstream data provenance is not independently verified"],
        limitations=[
            "This is an LLM interpretation, not a calibrated statistical forecast.",
            "BUY/SELL wording is preserved for review only and is never an order intent.",
        ],
        raw_output=decision_text,
        extra={"api_path": api_path},
    )
    return {
        "status": "ok",
        "plugin_id": PLUGIN_ID,
        "evidence_packet": packet,
        "safety": SAFETY_DECLARATION,
    }


def main() -> int:
    try:
        request = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        print(json.dumps(_error("invalid_request_json", "stdin was not valid JSON")))
        return 2
    result = run_request(request)
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
