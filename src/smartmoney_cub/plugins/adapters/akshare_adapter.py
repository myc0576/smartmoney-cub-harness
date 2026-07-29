"""AKShare data-provider adapter.

Produces a unified ``smartmoney_cub_market_data_packet.v1`` for stocks,
indexes, and industry/concept sectors. AKShare is a data provider, not a
forecasting model. Upstream API changes must surface as structured errors,
never as raw tracebacks.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any

from smartmoney_cub.plugins.protocol import build_market_data_packet
from smartmoney_cub.schemas import SAFETY_DECLARATION

PLUGIN_ID = "akshare"
UPSTREAM_REPO = "https://github.com/akfamily/akshare"

_COLUMN_ALIASES = {
    "日期": "date",
    "date": "date",
    "开盘": "open",
    "open": "open",
    "最高": "high",
    "high": "high",
    "最低": "low",
    "low": "low",
    "收盘": "close",
    "close": "close",
    "成交量": "volume",
    "volume": "volume",
}

OHLCV_FIELDS = ("date", "open", "high", "low", "close", "volume")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _error(code: str, message: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "error",
        "plugin_id": PLUGIN_ID,
        "error": {"code": code, "message": message},
        "safety": SAFETY_DECLARATION,
    }
    payload.update(extra)
    return payload


def _load_akshare(deps: dict[str, Any] | None):
    if deps is not None and "akshare" in deps:
        return deps["akshare"]
    try:
        import akshare  # type: ignore[import-not-found]  # noqa: PLC0415
    except ImportError:
        return None
    return akshare


def _normalize_symbol(symbol: str, target_type: str) -> tuple[str, str]:
    """Return (bare_symbol, exchange) from formats like 600519.SS / 000001.SZ."""

    upper = symbol.upper()
    if upper.endswith(".SS"):
        return upper[:-3], "SSE"
    if upper.endswith(".SZ"):
        return upper[:-3], "SZSE"
    if upper.endswith(".BJ"):
        return upper[:-3], "BSE"
    return upper, "UNKNOWN"


def _frame_to_bars(frame: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """Convert an AKShare DataFrame-like object to normalized OHLCV bars."""

    try:
        records = frame.to_dict(orient="records")
    except Exception:
        if isinstance(frame, list):
            records = frame
        else:
            raise TypeError("unsupported frame type") from None

    bars: list[dict[str, Any]] = []
    missing: set[str] = set()
    for record in records:
        normalized: dict[str, Any] = {}
        for key, value in dict(record).items():
            alias = _COLUMN_ALIASES.get(str(key))
            if alias:
                normalized[alias] = str(value) if alias == "date" else value
        for field in OHLCV_FIELDS:
            if field not in normalized:
                missing.add(field)
        bars.append(normalized)
    return bars, sorted(missing)


def fetch_market_data(
    request: dict[str, Any], *, deps: dict[str, Any] | None = None
) -> dict[str, Any]:
    akshare = _load_akshare(deps)
    if akshare is None:
        return _error(
            "akshare_not_installed",
            "The akshare package is not importable inside this plugin environment.",
        )

    target = request.get("target") or {}
    symbol = str(target.get("symbol", ""))
    target_type = str(target.get("type", "stock"))
    options = request.get("options") or {}
    interval = str(options.get("interval", "daily"))
    adjustment = str(options.get("adjustment", "qfq"))
    bare_symbol, exchange = _normalize_symbol(symbol, target_type)

    try:
        if target_type == "stock":
            frame = akshare.stock_zh_a_hist(
                symbol=bare_symbol, period=interval, adjust=adjustment
            )
        elif target_type == "index":
            frame = akshare.stock_zh_index_daily(symbol=bare_symbol.lower())
        elif target_type == "sector":
            frame = akshare.stock_board_industry_hist_em(symbol=bare_symbol)
        else:
            return _error("unsupported_target_type", f"unsupported target type: {target_type}")
    except AttributeError as exc:
        return _error(
            "akshare_api_changed",
            "The installed AKShare version does not expose the expected function. "
            f"Missing attribute: {exc}. Try 'smcub plugin update akshare'.",
        )
    except Exception as exc:  # upstream network / data errors
        return _error(
            "akshare_fetch_failed",
            "AKShare could not fetch data for "
            f"{symbol!r} ({target_type}): {exc.__class__.__name__}. "
            "Check the symbol, your network, and the upstream service status.",
        )

    try:
        bars, missing_fields = _frame_to_bars(frame)
    except TypeError:
        return _error(
            "akshare_output_format_changed",
            "AKShare returned an unexpected data structure; the upstream API "
            "may have changed. Try 'smcub plugin update akshare'.",
        )

    if not bars:
        return _error(
            "akshare_empty_result",
            f"AKShare returned no rows for {symbol!r} ({target_type}).",
        )

    quality = "ok" if not missing_fields else "partial"
    packet = build_market_data_packet(
        symbol=symbol,
        target_type=target_type,
        exchange=exchange,
        interval=interval,
        adjustment=adjustment,
        source="akshare",
        as_of=str(request.get("as_of") or _utc_now()),
        available_at=_utc_now(),
        bars=bars,
        data_quality_flag=quality,
        missing_fields=missing_fields,
        provenance={
            "upstream_repo": UPSTREAM_REPO,
            "fetch_function": {
                "stock": "stock_zh_a_hist",
                "index": "stock_zh_index_daily",
                "sector": "stock_board_industry_hist_em",
            }.get(target_type, "unknown"),
        },
    )
    return {
        "status": "ok",
        "plugin_id": PLUGIN_ID,
        "market_data": packet,
        "safety": SAFETY_DECLARATION,
    }


def run_request(request: dict[str, Any], *, deps: dict[str, Any] | None = None) -> dict[str, Any]:
    return fetch_market_data(request, deps=deps)


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
