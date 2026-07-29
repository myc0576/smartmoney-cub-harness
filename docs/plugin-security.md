# Plugin Security Model

SmartMoney-Cub treats every plugin as third-party code with a strict
containment boundary. This document describes the model and the guarantees.

## Threat model

| Threat | Mitigation |
|---|---|
| Heavy/conflicting dependencies breaking core | Each plugin lives in its own venv under `~/.smartmoney-cub/plugins/<id>/.venv`; core never imports plugin packages |
| Command injection via ids/specs/symbols | Strict allowlist regexes (`validate_plugin_id`, `validate_install_spec`, `validate_symbol`); subprocess uses list argv with `shell=False`, never `shell=True` |
| Path traversal (`../`) escaping the plugin home | `safe_child_path` resolves and verifies containment before any file operation |
| Silent network access | Installation and analysis require explicit `--allow-network`; manifests declare `requires_network` |
| Silent large model downloads | `--ack-model-download` gate; Chronos refuses to fetch weights without it |
| Credential leakage | API keys live only in environment variables; `configure` rejects secret-looking keys; doctor/output paths pass through `safety.redact`; credential **values** are never printed or logged |
| Catalog fraud (plugin claims more than it does) | Manifest validation rejects catalog-only entries claiming runtime integration; duplicate ids fail loading |
| Upstream API drift | Adapters convert upstream failures into structured error codes (e.g. `akshare_api_changed`), never raw tracebacks |
| Trading execution sneaking in | `actionability` is fixed to `review_only`; the safety declaration `READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE` is asserted on manifests, packets, and reports; no order/cancel/trade code paths exist |

## Process isolation

Runtime plugins execute as subprocesses:

```
core (host python) --JSON stdin--> plugin venv python -m adapter --JSON stdout--> core
```

- the host passes one JSON request on stdin and reads one JSON response
  from stdout;
- the adapter runs with the plugin venv's interpreter, so heavy imports
  (torch, langgraph, qlib, ...) never load into the host process;
- timeouts kill runaway plugin processes;
- stdout that is not valid JSON becomes a structured `plugin_output_invalid`
  error.

## Consent gates

| Flag | Meaning |
|---|---|
| `--yes` | confirm machine-modifying operations (install/update/uninstall) |
| `--allow-network` | permit network access for this operation |
| `--ack-third-party` | acknowledge third-party code/analysis is involved |
| `--ack-model-download` | acknowledge large model weight downloads |

Defaults are always the safe choice: no consent, no action.

## Uninstall guarantees

`smcub plugin uninstall <id> --yes` removes `.venv/`, `source/`, `cache/`,
`logs/`, and the manifest copy. It **never** deletes user-generated analysis
results stored under the plugin home (e.g. `results/`).

## What plugins can never do

- place, modify, or cancel orders, or talk to broker APIs;
- write outside their plugin home via host-managed paths;
- store credentials in config files;
- present their output as investment advice — everything is review-only
  evidence for human decision review.
