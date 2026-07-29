"""Qlib quantitative prediction adapter.

Reads user-prepared Qlib data directories, existing model predictions, and
Recorder outputs. It never retrains models during a normal analysis request.
Scores are reported as uncalibrated cross-sectional signals, never as
deterministic price targets.

Readiness states surfaced to the manager:
- installed but no data      -> data_missing
- data but no model          -> model_missing
- model available            -> ready (predictions readable)
- only historical backtests  -> backtest_only
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from smartmoney_cub.plugins.protocol import build_evidence_packet
from smartmoney_cub.schemas import SAFETY_DECLARATION

PLUGIN_ID = "qlib"
UPSTREAM_REPO = "https://github.com/microsoft/qlib"
UPSTREAM_LICENSE = "MIT"


def _error(code: str, message: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "error",
        "plugin_id": PLUGIN_ID,
        "error": {"code": code, "message": message},
        "safety": SAFETY_DECLARATION,
    }
    payload.update(extra)
    return payload


def check_data_health(data_dir: str | None) -> dict[str, Any]:
    """Lightweight offline health check of a Qlib data directory."""

    if not data_dir:
        return {"state": "unconfigured", "detail": "no data_dir configured"}
    path = Path(data_dir)
    if not path.exists():
        return {"state": "data_missing", "detail": "configured data_dir does not exist"}
    calendars = path / "calendars"
    features = path / "features"
    if not calendars.exists() or not features.exists():
        return {
            "state": "data_incomplete",
            "detail": "data_dir lacks calendars/ or features/ subdirectories",
        }
    return {"state": "ok", "detail": "calendars and features directories present"}


def resolve_readiness(config: dict[str, Any]) -> dict[str, Any]:
    data_health = check_data_health(config.get("data_dir"))
    predictions_path = config.get("predictions_path")
    recorder_dir = config.get("recorder_dir")
    backtest_report = config.get("backtest_report_path")

    has_predictions = bool(predictions_path) and Path(str(predictions_path)).exists()
    has_recorder = bool(recorder_dir) and Path(str(recorder_dir)).exists()
    has_backtest = bool(backtest_report) and Path(str(backtest_report)).exists()

    if data_health["state"] in ("unconfigured",):
        state = "installed_unconfigured"
    elif data_health["state"] in ("data_missing", "data_incomplete"):
        state = "data_missing"
    elif has_predictions or has_recorder:
        state = "ready"
    elif has_backtest:
        state = "backtest_only"
    else:
        state = "model_missing"

    return {
        "state": state,
        "data_health": data_health,
        "has_predictions": has_predictions,
        "has_recorder_output": has_recorder,
        "has_backtest_report": has_backtest,
    }


def _load_predictions(predictions_path: str) -> list[dict[str, Any]]:
    """Load a predictions file (JSON list or CSV with instrument,score)."""

    path = Path(predictions_path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if isinstance(data, list):
            return [dict(row) for row in data]
        raise ValueError("predictions JSON must be a list of objects")
    rows: list[dict[str, Any]] = []
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return rows
    header = [cell.strip() for cell in lines[0].split(",")]
    for line in lines[1:]:
        cells = [cell.strip() for cell in line.split(",")]
        rows.append(dict(zip(header, cells)))
    return rows


def run_request(request: dict[str, Any], *, deps: dict[str, Any] | None = None) -> dict[str, Any]:
    config = dict(request.get("plugin_config") or {})
    readiness = resolve_readiness(config)

    if readiness["state"] == "installed_unconfigured":
        return _error(
            "qlib_unconfigured",
            "Qlib is installed but no data_dir is configured. Run: "
            "smcub plugin configure qlib --set data_dir=/path/to/qlib_data",
            readiness=readiness,
        )
    if readiness["state"] == "data_missing":
        return _error(
            "qlib_data_missing",
            "The configured Qlib data directory is missing or incomplete. "
            "Prepare it with the upstream qlib data tooling first.",
            readiness=readiness,
        )
    if readiness["state"] == "model_missing":
        return _error(
            "qlib_model_missing",
            "Qlib data is present but no predictions/recorder output is configured. "
            "Train a workflow upstream (e.g. Alpha158 + LightGBM), then run: "
            "smcub plugin configure qlib --set predictions_path=/path/to/pred.json",
            readiness=readiness,
        )

    target = request.get("target") or {}
    symbol = str(target.get("symbol", ""))

    rows: list[dict[str, Any]] = []
    if readiness["has_predictions"]:
        try:
            rows = _load_predictions(str(config["predictions_path"]))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return _error(
                "qlib_predictions_unreadable",
                f"Could not read predictions file: {exc.__class__.__name__}",
            )

    def _score_of(row: dict[str, Any]) -> float:
        try:
            return float(row.get("score", 0.0))
        except (TypeError, ValueError):
            return 0.0

    ranked = sorted(rows, key=_score_of, reverse=True)
    instrument_key = "instrument" if any("instrument" in r for r in ranked) else "symbol"
    bare_symbol = symbol.split(".")[0]
    target_rank = None
    target_score = None
    for index, row in enumerate(ranked, start=1):
        row_symbol = str(row.get(instrument_key, ""))
        if bare_symbol and bare_symbol in row_symbol:
            target_rank = index
            target_score = _score_of(row)
            break

    metrics = {}
    for key in ("ic", "rank_ic", "annualized_return", "max_drawdown"):
        if key in config:
            metrics[key] = config[key]

    packet = build_evidence_packet(
        plugin_id=PLUGIN_ID,
        plugin_version=str(config.get("plugin_version", "unknown")),
        upstream_repo=UPSTREAM_REPO,
        upstream_license=UPSTREAM_LICENSE,
        target=target,
        as_of=str(request.get("as_of", "")),
        horizon=str(request.get("horizon", "d5")),
        input_data={"predictions_rows": len(rows)},
        data_sources=[
            {
                "name": "qlib_local_data",
                "data_dir_configured": bool(config.get("data_dir")),
                "note": "user-prepared local Qlib data; no network access",
            }
        ],
        data_quality=readiness["data_health"]["state"],
        model_identifier=str(config.get("model_identifier", "user_trained_qlib_model")),
        forecast={
            "direction": "unstated",
            "cross_section_rank": target_rank,
            "cross_section_size": len(ranked),
            "score": target_score,
            "score_semantics": "uncalibrated relative signal, not a price target",
            "quantiles": {},
            "calibrated": False,
            "metrics": metrics,
        },
        evidence=(
            [f"target ranked {target_rank}/{len(ranked)} by model score"]
            if target_rank is not None
            else ["target not found in the current prediction cross-section"]
        ),
        output_kind="uncalibrated_score",
        risks=["model may be stale relative to current market regime"],
        missing_information=(
            [] if target_rank is not None else ["prediction row for the requested symbol"]
        ),
        limitations=[
            "Scores are relative cross-sectional signals and must not be read as "
            "deterministic price targets.",
            "No retraining is performed during analysis requests.",
        ],
        raw_output={"readiness": readiness, "rank": target_rank, "score": target_score},
    )
    return {
        "status": "ok",
        "plugin_id": PLUGIN_ID,
        "evidence_packet": packet,
        "readiness": readiness,
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
