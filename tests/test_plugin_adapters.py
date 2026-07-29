from __future__ import annotations

import json
from pathlib import Path

from smartmoney_cub.plugins.adapters import (
    akshare_adapter,
    chronos2_adapter,
    qlib_adapter,
    tradingagents_adapter,
)
from smartmoney_cub.plugins.protocol import build_analysis_request
from smartmoney_cub.schemas import (
    FORECAST_EVIDENCE_PACKET_SCHEMA,
    MARKET_DATA_PACKET_SCHEMA,
    SAFETY_DECLARATION,
)


def _request(**overrides) -> dict:
    request = build_analysis_request(
        symbol="600519.SS",
        target_type="stock",
        horizon="d5",
        as_of="2026-07-01",
        network_allowed=True,
        options=overrides.pop("options", {}),
    )
    request.update(overrides)
    return request


# --- category 14: AKShare mock produces the unified packet ---


class _FakeFrame:
    def __init__(self, records):
        self._records = records

    def to_dict(self, orient="records"):
        assert orient == "records"
        return self._records


class _FakeAkshare:
    def stock_zh_a_hist(self, symbol, period, adjust):
        assert symbol == "600519"
        return _FakeFrame(
            [
                {
                    "日期": "2026-06-30",
                    "开盘": 1500.0,
                    "最高": 1520.0,
                    "最低": 1490.0,
                    "收盘": 1510.0,
                    "成交量": 12345,
                },
                {
                    "日期": "2026-07-01",
                    "开盘": 1510.0,
                    "最高": 1530.0,
                    "最低": 1500.0,
                    "收盘": 1525.0,
                    "成交量": 23456,
                },
            ]
        )


def test_akshare_mock_returns_unified_market_data_packet():
    result = akshare_adapter.fetch_market_data(
        _request(), deps={"akshare": _FakeAkshare()}
    )
    assert result["status"] == "ok", result
    packet = result["market_data"]
    assert packet["schema"] == MARKET_DATA_PACKET_SCHEMA
    bars = packet["bars"]
    assert len(bars) == 2
    assert set(bars[0]) >= {"date", "open", "high", "low", "close", "volume"}
    assert bars[1]["close"] == 1525.0
    assert result["safety"] == SAFETY_DECLARATION


def test_akshare_not_installed_is_structured_error():
    result = akshare_adapter.fetch_market_data(_request(), deps={"akshare": None})
    assert result["status"] == "error"
    assert result["error"]["code"] == "akshare_not_installed"
    assert "Traceback" not in json.dumps(result)


def test_akshare_upstream_api_change_is_structured_error():
    class _Broken:
        def __getattr__(self, name):
            raise AttributeError(name)

    result = akshare_adapter.fetch_market_data(_request(), deps={"akshare": _Broken()})
    assert result["status"] == "error"
    assert result["error"]["code"] == "akshare_api_changed"


# --- category 13: TradingAgents official API mock ---


class _FakeGraph:
    created_with: dict | None = None

    def __init__(self, debug=False, config=None):
        _FakeGraph.created_with = dict(config or {})

    def propagate(self, symbol, analysis_date):
        assert symbol == "600519.SS"
        assert analysis_date == "2026-07-01"
        return {"state": "final"}, "Comprehensive analysis suggests BUY based on momentum."


def test_tradingagents_uses_official_api():
    result = tradingagents_adapter.run_request(
        _request(options={"provider": "deepseek"}),
        deps={
            "trading_agents_graph_cls": _FakeGraph,
            "default_config": {"llm_provider": "openai", "deep_think_llm": "gpt"},
        },
    )
    assert result["status"] == "ok", result
    packet = result["evidence_packet"]
    assert packet["schema"] == FORECAST_EVIDENCE_PACKET_SCHEMA
    assert packet["output_kind"] == "llm_interpretation"
    assert packet["api_path"] == "official"
    assert packet["forecast"]["direction"] == "up"
    assert packet["forecast"]["calibrated"] is False
    # BUY wording must remain review-only, never an order intent
    assert packet["actionability"] == "review_only"
    dumped = json.dumps(result)
    assert "place_order" not in dumped and "submit_order" not in dumped


def test_tradingagents_not_installed_is_structured_error():
    result = tradingagents_adapter.run_request(
        _request(),
        deps={"trading_agents_graph_cls": None, "default_config": None, "legacy_module": None},
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "tradingagents_not_installed"


def test_tradingagents_failure_never_leaks_api_key(monkeypatch):
    secret = "sk-super-secret-value-42"
    monkeypatch.setenv("OPENAI_API_KEY", secret)

    class _Exploding:
        def __init__(self, debug=False, config=None):
            raise RuntimeError(f"auth failed for key {secret}")

    result = tradingagents_adapter.run_request(
        _request(),
        deps={"trading_agents_graph_cls": _Exploding, "default_config": {}},
    )
    assert result["status"] == "error"
    assert secret not in json.dumps(result)


# --- category 15: Chronos quantile forecast on transformed target ---


class _FakePipeline:
    def predict_quantiles(self, context, prediction_length, quantile_levels):
        assert prediction_length == 5
        # tensor-like: [batch, steps, num_quantiles]
        step = [[-0.02, -0.01, 0.0, 0.01, 0.02] for _ in range(prediction_length)]
        return ([step], None)


def _market_data(num_bars: int = 60) -> dict:
    bars = []
    close = 100.0
    for i in range(num_bars):
        close *= 1.001 if i % 2 == 0 else 0.999
        bars.append(
            {
                "date": f"2026-01-{(i % 28) + 1:02d}",
                "open": close * 0.99,
                "high": close * 1.01,
                "low": close * 0.98,
                "close": round(close, 4),
                "volume": 1000 + i,
            }
        )
    return {"schema": MARKET_DATA_PACKET_SCHEMA, "bars": bars}


def test_chronos_quantile_forecast_on_log_returns():
    result = chronos2_adapter.run_request(
        _request(
            input_data=_market_data(),
            options={"transformation": "log_return", "ack_model_download": True},
        ),
        deps={"pipeline": _FakePipeline()},
    )
    assert result["status"] == "ok", result
    packet = result["evidence_packet"]
    assert packet["output_kind"] == "numeric_model_forecast"
    quantiles = packet["forecast"]["quantiles"]
    assert set(quantiles) == {"q10", "q25", "q50", "q75", "q90"}
    assert len(quantiles["q50"]) == 5
    # forecast target must be the transformed series, not a raw price claim
    assert packet["forecast"]["transformation"] == "log_return"
    dumped = json.dumps(packet)
    assert "general-purpose" in dumped or "not specifically trained" in dumped.lower() or "generic" in dumped.lower()


def test_chronos_requires_model_download_ack():
    result = chronos2_adapter.run_request(
        _request(input_data=_market_data(), options={"transformation": "log_return"}),
        deps=None,
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "model_download_not_acknowledged"


def test_chronos_requires_market_data_packet():
    result = chronos2_adapter.run_request(
        _request(options={"ack_model_download": True}), deps={"pipeline": _FakePipeline()}
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "input_data_missing"


def test_chronos_transformations_produce_expected_shapes():
    closes = [100.0, 101.0, 102.01, 100.99, 102.0]
    volumes = [10.0, 11.0, 12.0, 13.0, 14.0]
    log_returns = chronos2_adapter.transform_series(closes, volumes, "log_return")
    assert len(log_returns) == len(closes) - 1
    normalized = chronos2_adapter.transform_series(closes, volumes, "normalized_close")
    assert abs(normalized[0] - 1.0) < 1e-9
    volume_series = chronos2_adapter.transform_series(closes, volumes, "volume")
    assert volume_series == volumes


# --- category 16: Qlib data/model readiness states ---


def test_qlib_unconfigured_state():
    readiness = qlib_adapter.resolve_readiness({})
    assert readiness["state"] == "installed_unconfigured"


def test_qlib_data_missing_state(tmp_path: Path):
    readiness = qlib_adapter.resolve_readiness({"data_dir": str(tmp_path / "nope")})
    assert readiness["state"] == "data_missing"


def test_qlib_data_incomplete_state(tmp_path: Path):
    readiness = qlib_adapter.resolve_readiness({"data_dir": str(tmp_path)})
    assert readiness["state"] == "data_missing"
    assert readiness["data_health"]["state"] == "data_incomplete"


def test_qlib_model_missing_then_ready(tmp_path: Path):
    (tmp_path / "calendars").mkdir()
    (tmp_path / "features").mkdir()
    config = {"data_dir": str(tmp_path)}
    assert qlib_adapter.resolve_readiness(config)["state"] == "model_missing"

    predictions = tmp_path / "pred.json"
    predictions.write_text(
        json.dumps([{"instrument": "SH600519", "score": 0.12}]), encoding="utf-8"
    )
    config["predictions_path"] = str(predictions)
    assert qlib_adapter.resolve_readiness(config)["state"] == "ready"


def test_qlib_scores_are_uncalibrated_rank_evidence(tmp_path: Path):
    (tmp_path / "calendars").mkdir()
    (tmp_path / "features").mkdir()
    predictions = tmp_path / "pred.json"
    predictions.write_text(
        json.dumps(
            [
                {"instrument": "SH600519", "score": 0.35},
                {"instrument": "SH600036", "score": -0.10},
                {"instrument": "SZ000001", "score": 0.05},
            ]
        ),
        encoding="utf-8",
    )
    result = qlib_adapter.run_request(
        _request(
            plugin_config={
                "data_dir": str(tmp_path),
                "predictions_path": str(predictions),
            }
        )
    )
    assert result["status"] == "ok", result
    packet = result["evidence_packet"]
    assert packet["output_kind"] == "uncalibrated_score"
    assert packet["forecast"].get("calibrated") is False
    # scores are relative rank evidence, never a numeric price target field
    assert "price_target" not in packet["forecast"]
    assert packet["actionability"] == "review_only"
