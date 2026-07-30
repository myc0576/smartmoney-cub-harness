# CLAUDE.md

This file mirrors `AGENTS.md` for agent compatibility. The canonical contract is `docs/harness-contract.md`.

## Project Shape

SmartMoney-Cub (Python package `smartmoney_cub`) is a small, offline package implementing the Evidence & Review Core:

- `src/smartmoney_cub/manifest.py` validates provenance and anti-future-leakage rules.
- `src/smartmoney_cub/run_capture.py` captures stdout, stderr, metadata, manifests, and decisions from offline commands.
- `src/smartmoney_cub/outcome.py` builds D1/D3 toy outcomes from JSON fixtures.
- `src/smartmoney_cub/evaluator.py` scores decisions against outcomes and risk contracts.
- `src/smartmoney_cub/registry.py` keeps challenger/champion rule state.
- `src/smartmoney_cub/safety.py` redacts sensitive strings and local paths.

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

