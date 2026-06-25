# AGENTS.md

This repository is the public, offline core of `smartmoney-cub-harness`.

## Contract

Read `docs/harness-contract.md` first. The project is a read-only decision logging and review harness. It is not a stock picker, broker connector, or financial advice system.

## Safety Rules

1. Keep the safety declaration on every manifest, decision, outcome, and doctor output:
   `READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE`
2. Do not add live trading execution, order placement, order cancellation, account modification, or broker automation.
3. Do not add real personal trading records, private watchlists, local absolute paths, credentials, cookies, or account identifiers.
4. Examples must use toy offline data only.
5. Non-silent observations must carry invalidation, time stop, give-up conditions, data source, available time, and data quality.
6. Any data source with `available_at > decision_time` must fail validation.
7. Rule promotion must go through challenger -> champion, with explicit confirmation before champion mutation.

## Build and Test

```bash
pip install -e ".[dev]"
pytest -q
python -m smartmoney_cub_harness.cli doctor
```
