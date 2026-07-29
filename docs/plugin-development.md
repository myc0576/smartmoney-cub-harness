# Plugin Development Guide

This guide explains how to add a new plugin to the SmartMoney-Cub catalog.

Contract: plugins produce **review-only evidence**. The safety declaration
`READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE` must appear on every manifest and
every output. Trading execution of any kind is rejected at review.

## 1. Write a manifest

Add `src/smartmoney_cub/plugins/manifests/<plugin_id>.json`:

```json
{
  "schema": "smartmoney_cub_plugin_manifest.v1",
  "id": "myplugin",
  "display_name": "My Plugin",
  "description": "What it does and what it does not do.",
  "upstream_repo": "https://github.com/org/project",
  "upstream_license": "Apache-2.0",
  "capabilities": ["zero_shot_forecast"],
  "supported_targets": ["stock", "index"],
  "supported_horizons": ["d1", "d3", "d5"],
  "install_type": "pip",
  "install_spec": "myplugin>=1.0",
  "python_requires": ">=3.10",
  "requires_network": true,
  "requires_credentials": false,
  "requires_model_download": false,
  "required_environment_variables": [],
  "integration_level": "runtime_integrated",
  "resource_profile": {"disk": "small", "memory": "small", "gpu": "optional"},
  "output_kind": "numeric_model_forecast",
  "actionability": "review_only",
  "safety": "READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE"
}
```

Rules enforced by `catalog.validate_plugin_manifest`:

- `id` matches `^[a-z][a-z0-9_]{0,39}$` and must be unique in the catalog;
- `upstream_license` must be on the open-source allowlist;
- `install_type` is one of `pip | git | docker | external | none`;
- a `catalog_available` / `adapter_planned` entry must NOT claim
  `runtime_integrated` status;
- never vendor upstream source into this repository.

## 2. Write an adapter (runtime plugins only)

Create `src/smartmoney_cub/plugins/adapters/<plugin_id>_adapter.py`:

- expose `run_request(request, *, deps=None) -> dict` and a `main()` that
  reads one JSON request from stdin and writes one JSON response to stdout;
- import the heavy upstream package **lazily inside functions**, never at
  module top level — the adapter runs inside the plugin's own venv;
- accept a `deps` dict so tests can inject fakes without installing anything;
- return structured errors (`{"status": "error", "error": {"code", "message"}}`),
  never raw tracebacks, and never echo credential values;
- on success return `{"status": "ok", "evidence_packet": ...}` built with
  `protocol.build_evidence_packet` (data providers return
  `{"status": "ok", "market_data": ...}` via `build_market_data_packet`);
- register the module path in `runner.ADAPTER_MODULES`.

## 3. Choose the right output kind

| output_kind | Meaning |
|---|---|
| `market_data` | OHLCV packets from a data provider |
| `numeric_model_forecast` | statistical forecast with quantiles |
| `llm_interpretation` | narrative produced by an LLM |
| `uncalibrated_score` | relative rank/score, not a probability |

Do not upgrade an LLM narrative to a numeric forecast, and never emit a
calibrated probability the upstream model did not produce.

## 4. Security requirements

- subprocess calls only via list argv, `shell=False`, validated by
  `environment.validate_install_spec` / `validate_plugin_id` / `validate_symbol`;
- all paths under the plugin home must go through `environment.safe_child_path`;
- credentials come from environment variables only; `manager.configure_plugin`
  rejects secret-looking keys;
- network access and model downloads happen only behind explicit CLI gates.

## 5. Test it offline

Add tests that use `deps` injection and a fake command runner — no network,
no real installs. See `tests/test_plugin_adapters.py` and
`tests/test_plugin_environment_installer.py` for patterns. Run:

```bash
pytest -q
```
