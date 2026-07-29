# Plugin Host and Catalog

SmartMoney-Cub core stays lightweight and offline. Heavy open-source finance
projects (TradingAgents, Qlib, Chronos, AKShare, ...) are **optional plugins**
installed on demand into isolated virtual environments. The core never imports
them directly.

Safety: every plugin result is review-only evidence.
`READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE` — no orders, no cancels, no trades.

## Plugin matrix

| Plugin | Capability | Output kind | Integration | License | Install |
|---|---|---|---|---|---|
| `akshare` | A-share stock/index/sector OHLCV data | `market_data` | runtime_integrated | MIT | pip |
| `tradingagents` | Multi-agent LLM analysis narrative | `llm_interpretation` | runtime_integrated | Apache-2.0 | git |
| `qlib` | Cross-sectional model scores (pre-trained) | `uncalibrated_score` | runtime_integrated | MIT | pip |
| `chronos2` | Zero-shot quantile forecast on transformed series | `numeric_model_forecast` | runtime_integrated | Apache-2.0 | pip |
| `timesfm` | Time-series foundation model | — | catalog_available | Apache-2.0 | — |
| `neuralforecast` | Classical + neural forecasting library | — | catalog_available | Apache-2.0 | — |
| `finrobot` | Multi-agent financial analysis platform | — | adapter_planned | Apache-2.0 | — |

`catalog_available` / `adapter_planned` entries are listed for discovery only;
they cannot be executed until a runtime adapter ships.

## Directory layout

Everything lives under `~/.smartmoney-cub` (override with the
`SMARTMONEY_CUB_HOME` environment variable):

```
~/.smartmoney-cub/
  config/                     # per-plugin non-sensitive config (registry.json, <id>.json)
  plugins/<plugin_id>/
    .venv/                    # isolated virtualenv (removed on uninstall)
    manifest.json             # copy of the catalog manifest at install time
    install_state.json        # smartmoney_cub_plugin_install_state.v1
    logs/                     # removed on uninstall
    cache/                    # removed on uninstall
    source/                   # git-based installs only; removed on uninstall
    results/                  # user analysis output — NEVER removed on uninstall
```

## CLI quick start

```bash
# discover
smcub plugin list
smcub plugin info tradingagents

# install (explicit consent gates required)
smcub plugin install akshare --yes --allow-network --ack-third-party
smcub plugin install chronos2 --yes --allow-network --ack-third-party --ack-model-download

# health check (credential values are never printed)
smcub plugin doctor
smcub plugin doctor qlib

# configure non-sensitive keys; credentials go in environment variables
smcub plugin configure qlib --key data_dir --value /path/to/qlib_data
export OPENAI_API_KEY=...   # never stored in config files

# lifecycle
smcub plugin update akshare --yes --allow-network --ack-third-party
smcub plugin disable tradingagents
smcub plugin enable tradingagents
smcub plugin uninstall chronos2 --yes   # user results are preserved

# multi-plugin review-only analysis
smcub analyze --target 600519.SS --target-type stock --horizon d5 \
  --data-provider akshare --plugins tradingagents,chronos2 \
  --allow-network --ack-third-party
```

## Plugin statuses

`not_installed`, `installing`, `installed_unconfigured`, `ready`, `disabled`,
`update_available`, `dependency_error`, `credentials_missing`, `data_missing`,
`model_missing`, `incompatible`, `error`.

Typical paths:

- `tradingagents`: installed but no LLM API key in the environment →
  `credentials_missing` / `installed_unconfigured`.
- `qlib`: installed but no `data_dir` → `installed_unconfigured`; `data_dir`
  set but missing → `data_missing`; data present but no predictions →
  `model_missing`.
- `chronos2`: refuses to download model weights until
  `--ack-model-download` (or a `local_model_path`) is provided.

## How results are aggregated

`smcub analyze` produces a `smartmoney_cub_multi_plugin_analysis.v1` report:

- every plugin's `smartmoney_cub_forecast_evidence_packet.v1` is preserved
  **verbatim** — no blending, no averaging;
- the summary only lists agreements, conflicts, and missing information;
- `calibrated_probability_available` is always `false` — the host never
  invents a "probability of rising" that no plugin produced;
- LLM narratives are labeled `llm_interpretation`, model scores are
  `uncalibrated_score`, numeric forecasts are `numeric_model_forecast`. They
  are different kinds of evidence and are never merged into one number.

## Disclaimers

- Plugins run third-party code. Review upstream projects before installing.
- Chronos/TimesFM are general-purpose time-series models, not trained
  specifically for financial markets; their intervals are evidence, not truth.
- Nothing here is investment advice. The system never places, modifies, or
  cancels orders.
