# smartmoney-cub-harness

![smartmoney-cub-harness cover](assets/smartmoney-cub-harness-cover.png)

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-pytest-informational)](tests/)
[![Read-only](https://img.shields.io/badge/mode-read--only-brightgreen)](docs/safety.md)
[![Local-first](https://img.shields.io/badge/local--first-no%20telemetry-success)](docs/privacy.md)
[![Agent-ready](https://img.shields.io/badge/agent--ready-loop%20artifacts-blueviolet)](docs/agent-loop.md)

Local-first AI review harness for subjective traders. It records decisions, reviews D1/D3 outcomes, and evolves rules without touching execution.

`smartmoney-cub-harness` is the public, offline core for a "smart money cub / AI review self-evolution harness." It is built for read-only review, decision records, delayed outcome checks, local Markdown memory, challenger -> champion rule governance, and agent-ready workflows.

It is not a stock picker, broker connector, trading execution bot, or financial advice system.

## 5-Second Demo

```bash
git clone https://github.com/myc0576/smartmoney-cub-harness.git
cd smartmoney-cub-harness
pip install -e ".[dev]"
smcub loop --preset toy --agent-trigger "自进化"
```

The demo uses toy offline JSON fixtures only. It creates a local run directory with:

- `loop_report.md`
- `trace.jsonl`
- `case_record.json`
- `memory.md`
- `evolution_ledger.jsonl`

Expected summary shape:

```json
{
  "status": "ok",
  "loop_name": "observe_candidate_plan_position_outcome_review_rule_update",
  "preset": "toy",
  "champion_mutated": false,
  "network_required": false,
  "telemetry": false,
  "safety": "READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE"
}
```

## For Normal Users

You can review decisions without a broker API:

- Use trading plan text.
- Use trading journal CSV.
- Use TongHuaShun / broker screenshots for read-only review notes.
- Use read-only exports.
- Use toy offline examples to learn the workflow before touching private local artifacts.

The harness helps structure what happened: thesis, invalidation, time stop, give-up conditions, source quality, D1/D3 outcome, review grade, failure tags, memory, and rule candidates.

## For Coding Agents

Tell an agent: `loop`, `自进化`, or `复盘一下`.

The safe agent workflow is:

1. Run `smcub loop --preset toy --agent-trigger "自进化"`.
2. Open `loop_report.md` and `trace.jsonl`.
3. Propose safety or review improvements.
4. Keep all rule updates as challenger candidates.
5. Never place orders, cancel orders, modify accounts, automate brokers, or mutate champion rules without explicit human confirmation.

See [docs/agent-loop.md](docs/agent-loop.md).

## Safety

Every manifest, decision, outcome, evaluation, registry, doctor output, and loop output carries:

```text
READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE
```

Project defaults:

- Local-first.
- Offline by default.
- No telemetry.
- No upload.
- No trading execution.
- No broker automation.
- Redaction before CLI output.
- Toy examples only in the public repo.

Run:

```bash
smcub privacy-audit
smcub doctor
```

## Core Loop

```text
Plan -> Observe -> Record -> Outcome -> Evaluate -> Memory -> Rule Candidate
```

The 5-second loop maps to:

1. Run doctor.
2. Capture a toy decision.
3. Build D1 outcome.
4. Evaluate the run.
5. Collect an offline case.
6. Write local Markdown memory.
7. Append an evolution ledger event.
8. Propose a challenger rule update.
9. Write `loop_report.md`.
10. Write `trace.jsonl`.
11. Keep `champion_mutated=false`.

## Privacy

This project does not collect, upload, sell, or learn your trading logic. By default it has no server, no telemetry, no remote database, and no real account connection.

Your private trading logic should remain in local artifacts on your machine. It must not be copied into the public repository. Public examples must stay toy-only.

See [docs/privacy.md](docs/privacy.md) and [docs/public-vs-private-quantkb.md](docs/public-vs-private-quantkb.md).

## CLI Commands

```bash
smcub loop --preset toy --agent-trigger "自进化"
smcub privacy-audit
smcub inspect-artifacts <run_dir>
smcub collect-case <run_dir>
smcub append-ledger --event EVENT --payload-json FILE
smcub save-memory --case-record FILE
smcub doctor
smcub validate-manifest examples/sample_run/run_manifest.json
```

## Development Checks

```bash
pip install -e ".[dev]"
pytest -q
python -m smartmoney_cub_harness.cli doctor
python -m smartmoney_cub_harness.cli --help
```

## Public Boundary

The public repo can include schemas, loop runtime, toy examples, redaction, case bank, local Markdown memory format, evolution ledger, challenger/champion governance, and agent runbooks.

The public repo must not include real trades, real watchlists, account data, private QMT paths, private strategy prompts, key stock-picking logic, secret scoring weights, credentials, cookies, or local private workspace paths.

## License

MIT. See [LICENSE](LICENSE).
