# CLAUDE.md

This file mirrors `AGENTS.md` for agent compatibility. The canonical contract is `docs/harness-contract.md`.

## Project Shape

`smartmoney-cub-harness` is a small, offline Python package:

- `src/smartmoney_cub_harness/manifest.py` validates provenance and anti-future-leakage rules.
- `src/smartmoney_cub_harness/run_capture.py` captures stdout, stderr, metadata, manifests, and decisions from offline commands.
- `src/smartmoney_cub_harness/outcome.py` builds D1/D3 toy outcomes from JSON fixtures.
- `src/smartmoney_cub_harness/evaluator.py` scores decisions against outcomes and risk contracts.
- `src/smartmoney_cub_harness/registry.py` keeps challenger/champion rule state.
- `src/smartmoney_cub_harness/safety.py` redacts sensitive strings and local paths.

## Non-Negotiables

- No trading execution.
- No real account data.
- No private local paths.
- No live data source as a default dependency.
- No financial advice language.
- Toy examples only.

## Commands

```bash
pip install -e ".[dev]"
smcub doctor
pytest -q
```
