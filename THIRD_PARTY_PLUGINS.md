# Third-Party Plugins

SmartMoney-Cub can optionally integrate the following open-source projects as
isolated plugins. The core ships **none** of their code and none of their
dependencies. Installation is always explicit, gated, and per-user.

Safety: `READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE`. All plugin output is
review-only evidence, never trading signals or investment advice.

## Runtime-integrated plugins

| Plugin | Upstream | License | What you get | What you must provide |
|---|---|---|---|---|
| AKShare | [akfamily/akshare](https://github.com/akfamily/akshare) | MIT | Unified OHLCV market data packets for A-share stocks, indexes, sectors | network access at fetch time |
| TradingAgents | [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) | Apache-2.0 | Multi-agent LLM research narrative (`llm_interpretation`) | your own LLM API key via environment variables |
| Qlib | [microsoft/qlib](https://github.com/microsoft/qlib) | MIT | Cross-sectional model scores from **your** pre-trained workflow (`uncalibrated_score`) | prepared qlib data dir + trained predictions |
| Chronos-2 | [amazon-science/chronos-forecasting](https://github.com/amazon-science/chronos-forecasting) | Apache-2.0 | Zero-shot quantile forecasts on transformed series (`numeric_model_forecast`) | model download acknowledgement (or local weights) |

## Catalog-only entries (no runtime adapter yet)

| Plugin | Upstream | License | Status |
|---|---|---|---|
| TimesFM | [google-research/timesfm](https://github.com/google-research/timesfm) | Apache-2.0 | catalog_available |
| NeuralForecast | [Nixtla/neuralforecast](https://github.com/Nixtla/neuralforecast) | Apache-2.0 | catalog_available |
| FinRobot | [AI4Finance-Foundation/FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) | Apache-2.0 | adapter_planned |

These appear in `smcub plugin list` for discovery but cannot be executed.

## Legal and usage notes

- Each upstream project keeps its own license and terms; installing a plugin
  means you accept the upstream terms as well.
- Upstream projects are research tools. Their authors explicitly state the
  output is not financial advice — SmartMoney-Cub preserves and reinforces
  that framing.
- SmartMoney-Cub does not redistribute upstream code, models, or data. The
  installer fetches from PyPI or the upstream git repository at your request.
- LLM-based plugins send the analysis target (symbol, date) to the LLM
  provider you configure. Do not use them with confidential information.
- General-purpose forecasting models (Chronos, TimesFM) are not trained
  specifically on financial markets; treat intervals as weak evidence.

See `docs/plugins.md` for usage and `docs/plugin-security.md` for the
security model.
