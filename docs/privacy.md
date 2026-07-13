# Privacy

`smartmoney-cub-harness` is local-first and offline by default.

The project does not collect, upload, sell, or learn a user's trading logic. The public core has no server, no telemetry, no remote database, and no real account connection.

## Defaults

- `network_required`: `false`
- `telemetry`: `false`
- `upload`: `false`
- `default_data_mode`: `offline_json_fixtures`
- `execution_integrations`: `disabled`
- `redaction`: `enabled`
- `safety`: `READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE`

Run:

```bash
smcub privacy-audit
```

## What Stays Local

Private trading plans, journals, screenshots, exports, rule notes, and review memories should stay in local artifacts. They should not be committed to this public repository.

The CLI redacts common sensitive strings before printing JSON output, including email, phone, token, cookie, account-like keys, Windows paths, and Unix home paths.

The TradingAgents adapter is optional and user-configured. External LLM/API credentials remain outside this repository and must never be committed or captured in artifacts.

## What Public Examples May Contain

Public examples must use toy offline data only. They may demonstrate schemas, case records, memory files, and ledger events, but not real trades, private watchlists, credentials, cookies, account identifiers, or local private paths.
