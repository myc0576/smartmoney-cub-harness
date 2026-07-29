"""Chronos-2 zero-shot forecasting adapter.

Consumes a unified market data packet (usually produced by the AKShare data
provider), transforms the raw series into a forecastable target (log returns
by default -- never raw prices presented as reliable), and produces multi-step
quantile forecasts (q10/q25/q50/q75/q90).

Chronos is a general-purpose time-series foundation model. It is NOT trained
specifically for any single market; every packet carries that warning.
"""

from __future__ import annotations

import json
import math
import sys
from typing import Any

from smartmoney_cub.plugins.protocol import build_evidence_packet
from smartmoney_cub.schemas import SAFETY_DECLARATION

PLUGIN_ID = "chronos2"
UPSTREAM_REPO = "https://github.com/amazon-science/chronos-forecasting"
UPSTREAM_LICENSE = "Apache-2.0"

DEFAULT_MODEL_ID = "amazon/chronos-t5-small"
QUANTILE_LEVELS = (0.1, 0.25, 0.5, 0.75, 0.9)
QUANTILE_KEYS = ("q10", "q25", "q50", "q75", "q90")

HORIZON_STEPS = {"intraday": 1, "d1": 1, "d3": 3, "d5": 5, "d10": 10, "d20": 20}

TRANSFORMATIONS = ("log_return", "cumulative_return", "normalized_close", "volatility", "volume")

GENERIC_MODEL_WARNING = (
    "Chronos is a general-purpose time-series model and was not trained "
    "specifically for this market; treat quantiles as rough uncertainty "
    "bands, not calibrated market probabilities."
)


def _error(code: str, message: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "error",
        "plugin_id": PLUGIN_ID,
        "error": {"code": code, "message": message},
        "safety": SAFETY_DECLARATION,
    }
    payload.update(extra)
    return payload


def _extract_closes_volumes(packet: dict[str, Any]) -> tuple[list[float], list[float]]:
    closes: list[float] = []
    volumes: list[float] = []
    for bar in packet.get("bars", []):
        try:
            closes.append(float(bar["close"]))
        except (KeyError, TypeError, ValueError):
            continue
        try:
            volumes.append(float(bar.get("volume", 0.0)))
        except (TypeError, ValueError):
            volumes.append(0.0)
    return closes, volumes


def transform_series(
    closes: list[float], volumes: list[float], transformation: str, window: int = 20
) -> list[float]:
    if transformation == "log_return":
        return [
            math.log(b / a)
            for a, b in zip(closes[:-1], closes[1:])
            if a > 0 and b > 0
        ]
    if transformation == "cumulative_return":
        if not closes or closes[0] <= 0:
            return []
        return [c / closes[0] - 1.0 for c in closes]
    if transformation == "normalized_close":
        if not closes:
            return []
        first = closes[0]
        return [c / first for c in closes] if first > 0 else []
    if transformation == "volatility":
        returns = transform_series(closes, volumes, "log_return")
        out: list[float] = []
        for idx in range(window, len(returns) + 1):
            chunk = returns[idx - window : idx]
            mean = sum(chunk) / len(chunk)
            var = sum((r - mean) ** 2 for r in chunk) / len(chunk)
            out.append(math.sqrt(var))
        return out
    if transformation == "volume":
        return [v for v in volumes if v >= 0]
    raise ValueError(f"unsupported transformation: {transformation}")


def _inverse_description(transformation: str, last_close: float | None) -> str:
    if transformation == "log_return":
        return (
            "price_estimate = last_close * exp(cumulative_forecast_log_return); "
            f"last_close={last_close}"
        )
    if transformation == "cumulative_return":
        return f"price_estimate = base_close * (1 + value); base_close relates to first bar"
    if transformation == "normalized_close":
        return f"price_estimate = value * first_close"
    return "no price inversion; series is not a price transform"


def _load_pipeline(options: dict[str, Any], deps: dict[str, Any] | None):
    if deps is not None and "pipeline" in deps:
        return deps["pipeline"], str(options.get("model_id", DEFAULT_MODEL_ID)), "injected"
    if not options.get("ack_model_download") and not options.get("local_model_path"):
        return None, None, None
    try:  # pragma: no cover - requires real chronos install
        from chronos import BaseChronosPipeline  # type: ignore[import-not-found]  # noqa: PLC0415
    except ImportError:
        return None, None, "not_installed"
    model_id = str(options.get("local_model_path") or options.get("model_id", DEFAULT_MODEL_ID))
    device = "cuda" if options.get("device") == "cuda" else "cpu"
    pipeline = BaseChronosPipeline.from_pretrained(model_id, device_map=device)
    return pipeline, model_id, device


def _predict_quantiles(
    pipeline: Any, context: list[float], steps: int
) -> dict[str, list[float]]:
    """Call the pipeline and normalize output to {q10: [...], ...}."""

    result = pipeline.predict_quantiles(
        context=context, prediction_length=steps, quantile_levels=list(QUANTILE_LEVELS)
    )
    quantiles = result[0] if isinstance(result, tuple) else result
    normalized: dict[str, list[float]] = {}
    if isinstance(quantiles, dict):
        for key_idx, q_key in enumerate(QUANTILE_KEYS):
            level = QUANTILE_LEVELS[key_idx]
            values = quantiles.get(q_key) or quantiles.get(level) or quantiles.get(str(level))
            normalized[q_key] = [float(v) for v in (values or [])]
        return normalized
    # tensor-like: shape [batch, steps, num_quantiles]
    try:
        data = quantiles.tolist()
    except AttributeError:
        data = quantiles
    series = data[0] if data and isinstance(data[0], list) and isinstance(data[0][0], list) else data
    for q_index, q_key in enumerate(QUANTILE_KEYS):
        normalized[q_key] = [float(step_vals[q_index]) for step_vals in series]
    return normalized


def run_request(request: dict[str, Any], *, deps: dict[str, Any] | None = None) -> dict[str, Any]:
    options = dict(request.get("options") or {})
    horizon = str(request.get("horizon", "d5"))
    steps = HORIZON_STEPS.get(horizon)
    if steps is None:
        return _error("invalid_horizon", f"unsupported horizon: {horizon}")

    transformation = str(options.get("transformation", "log_return"))
    if transformation not in TRANSFORMATIONS:
        return _error(
            "invalid_transformation",
            f"unsupported transformation: {transformation}; "
            f"choose one of {', '.join(TRANSFORMATIONS)}",
        )

    market_data = request.get("input_data")
    if not isinstance(market_data, dict) or not market_data.get("bars"):
        return _error(
            "input_data_missing",
            "Chronos-2 needs a unified market data packet as input. Use "
            "--data-provider akshare or pass --input-data <packet.json>.",
        )

    closes, volumes = _extract_closes_volumes(market_data)
    series = transform_series(closes, volumes, transformation)
    min_context = int(options.get("min_context", 30))
    if len(series) < min_context:
        return _error(
            "insufficient_history",
            f"Only {len(series)} usable points after '{transformation}' transform; "
            f"need at least {min_context}.",
        )

    pipeline, model_id, device = _load_pipeline(options, deps)
    if pipeline is None:
        if device == "not_installed":
            return _error(
                "chronos_not_installed",
                "chronos-forecasting is not importable inside this plugin environment.",
            )
        return _error(
            "model_download_not_acknowledged",
            "Chronos downloads model weights on first use. Re-run with the "
            "option ack_model_download=true (CLI: --ack-model-download) or "
            "configure local_model_path.",
        )

    input_window = int(options.get("input_window", 512))
    context = series[-input_window:]
    try:
        quantiles = _predict_quantiles(pipeline, context, steps)
    except Exception as exc:
        return _error(
            "chronos_prediction_failed",
            f"Chronos prediction failed: {exc.__class__.__name__}. The upstream "
            "API may have changed; try 'smcub plugin update chronos2'.",
        )

    median_path = quantiles.get("q50", [])
    point_forecast = median_path[-1] if median_path else None
    cumulative = sum(median_path) if transformation == "log_return" else point_forecast
    direction = "unstated"
    if transformation in ("log_return", "cumulative_return") and cumulative is not None:
        if cumulative > 0:
            direction = "up"
        elif cumulative < 0:
            direction = "down"
        else:
            direction = "flat"

    last_close = closes[-1] if closes else None
    freshness = {
        "as_of": market_data.get("as_of"),
        "fetch_time": market_data.get("fetch_time"),
        "available_at": market_data.get("available_at"),
        "data_quality_flag": market_data.get("data_quality_flag"),
    }

    packet = build_evidence_packet(
        plugin_id=PLUGIN_ID,
        plugin_version=str(options.get("plugin_version", "unknown")),
        upstream_repo=UPSTREAM_REPO,
        upstream_license=UPSTREAM_LICENSE,
        target=dict(request.get("target") or {}),
        as_of=str(request.get("as_of", "")),
        horizon=horizon,
        input_data=market_data,
        data_sources=[
            {
                "name": str(market_data.get("source", "unknown")),
                "fetch_time": market_data.get("fetch_time"),
                "available_at": market_data.get("available_at"),
                "data_quality_flag": market_data.get("data_quality_flag"),
            }
        ],
        data_quality=str(market_data.get("data_quality_flag", "unknown")),
        model_identifier=str(model_id),
        forecast={
            "direction": direction,
            "forecast_horizon": horizon,
            "forecast_steps": steps,
            "point_forecast": point_forecast,
            "quantiles": quantiles,
            "input_window": len(context),
            "model_identifier": str(model_id),
            "model_revision": str(options.get("model_revision", "default")),
            "device": device,
            "transformation": transformation,
            "inverse_transformation": _inverse_description(transformation, last_close),
            "data_freshness": freshness,
            "calibrated": False,
        },
        evidence=[
            f"median {transformation} forecast over {steps} step(s): "
            + ", ".join(f"{v:.6f}" for v in median_path)
        ],
        output_kind="numeric_model_forecast",
        risks=[GENERIC_MODEL_WARNING],
        missing_information=[],
        limitations=[
            GENERIC_MODEL_WARNING,
            "Raw price levels are intentionally not forecast by default; "
            "the target series is a transformed quantity.",
        ],
        raw_output=quantiles,
        extra={"warning": GENERIC_MODEL_WARNING},
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
