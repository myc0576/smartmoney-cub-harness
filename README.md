# SmartMoney-Cub

<div align="center">

![SmartMoney-Cub cover](assets/smartmoney-cub-cover.png)

**OPEN SOURCE · LOCAL-FIRST · READ-ONLY**

AI-assisted trading review and evidence system
本地优先的 AI 交易复盘与证据系统

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-pytest-informational)](tests/)
[![Read-only](https://img.shields.io/badge/mode-read--only-brightgreen)](docs/safety.md)
[![Local-first](https://img.shields.io/badge/local--first-no%20telemetry-success)](docs/privacy.md)
[![Agent-ready](https://img.shields.io/badge/agent--ready-loop%20artifacts-blueviolet)](docs/agent-loop.md)

[简体中文](README.zh-CN.md)

`READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE`

</div>

---

SmartMoney-Cub is a local-first, read-only AI trading review system that turns decisions, evidence, and delayed outcomes into auditable cases, persistent memory, and human-approved rule candidates.

Its engine — the **Evidence & Review Core** — records what you planned, what evidence you had, what happened at D1/D3, and what rule candidate deserves a challenger trial. Nothing is promoted to champion without your explicit approval.

It is **not** a stock picker, a prediction system, an automated trading system, or a full quant platform.

## Why SmartMoney-Cub

Serious traders review every decision with a plan, evidence, delayed outcomes, and rule iteration. Most people instead dig through chat logs, terminal screenshots, and half-remembered feelings — and still cannot say why they bought, what went wrong, or what to change next time.

SmartMoney-Cub structures that review:

- What was the thesis at decision time?
- Were invalidation, time stop, and give-up conditions written down?
- Were the data sources, available time, and data quality reliable?
- What actually happened at D1/D3?
- Was the failure an execution, evidence, or rule problem?
- Is there a rule candidate worth a challenger trial?

Single judgments get forgotten. Systems evolve.

## What Works Today

| Capability | Status |
| --- | --- |
| Offline toy review loop (`smcub loop --preset toy`) | Working |
| Decision logging with provenance and safety validation | Working |
| D1/D3 delayed outcome review (no future leakage) | Working |
| Local Markdown case memory and evolution ledger | Working |
| Challenger → champion rule governance with explicit human confirmation | Working |
| Redaction before any CLI output | Working |
| Local private CSV self-evolve loop (`smcub self-evolve`) | Working |
| TradingAgents report ingestion (optional, user-configured) | Documented adapter / optional bridge |
| Screenshot / image understanding | External capability — see [Safety and Limitations](#safety-and-limitations) |

## 60-Second Quick Start

```bash
git clone https://github.com/myc0576/SmartMoney-Cub.git
cd SmartMoney-Cub
pip install -e ".[dev]"
smcub loop --preset toy --agent-trigger "自进化"
```

Common read-only commands after install:

```bash
smcub doctor
smcub privacy-audit
smcub loop --preset toy --agent-trigger "自进化"
smcub inspect-artifacts <run_dir>
```

Using a coding agent? One line is enough:

> Read `AGENTS.md` and `docs/harness-contract.md`, run `smcub loop --preset toy --agent-trigger "自进化"`, review-only: no broker connection, no orders.

The public repository ships toy offline data only.

## How It Works

```text
Inputs
  ↓
Capture Decisions & Evidence
  ↓
Validate Provenance & Safety
  ↓
D1 / D3 Outcome Review
  ↓
Memory & Challenger Rule
  ↓
Explicit Human Approval
```

| Stage | What happens |
| --- | --- |
| Capture | Plans, observations, and evidence are recorded as auditable artifacts |
| Validate | Provenance, available time, data quality, and the safety contract are checked; any source with `available_at > decision_time` fails validation |
| Outcome Review | Evaluation waits for D1/D3 results — no peeking at the future |
| Memory & Rule | Reviews become local Markdown memory; lessons become challenger rule candidates |
| Human Approval | Champion mutation only via `smcub confirm-promotion` — never automatic |

Optional external analysis (e.g. TradingAgents reports, multimodal agent output) enters this flow as **evidence only**.

## Outputs

Each loop run produces local artifacts:

- `loop_report.md` — the review report
- `case_record.json` — the auditable case
- `memory.md` — portable Markdown case memory
- `evolution_ledger.jsonl` — rule evolution history
- `trace.jsonl` — step-by-step trace

<details>
<summary>Example loop summary JSON</summary>

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

</details>

<details>
<summary>All CLI commands</summary>

```bash
smcub loop --preset toy --agent-trigger "自进化"
smcub privacy-audit
smcub self-evolve --input-csv path/to/private_cases.csv --max-iterations 20 --time-budget-min 10 --horizon d1
smcub confirm-promotion state/self_evolve/<loop_id>/promotion_packet.json --decision promote --note "manual approval"
smcub inspect-artifacts <run_dir>
smcub collect-case <run_dir>
smcub append-ledger --event EVENT --payload-json FILE
smcub save-memory --case-record FILE
smcub tradingagents-doctor
smcub tradingagents-ingest --report path/to/tradingagents_report.md --ticker 600519.SS --analysis-date 2026-07-06
smcub tradingagents-run --ticker 600519.SS --analysis-date 2026-07-06 --allow-network --ack-external-llm
smcub doctor
smcub validate-manifest examples/sample_run/run_manifest.json
```

</details>

## Optional Integrations

Integrations feed the review flow with better evidence. They never turn SmartMoney-Cub into an execution system.

| Project / Category | Status | Boundary |
| --- | --- | --- |
| [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) | Documented adapter / optional bridge | User configures their own LLM/API keys; keys are never stored, collected, or uploaded; output enters review as evidence only, never as order intent |
| [wbh604/UZI-Skill](https://github.com/wbh604/UZI-Skill) | Recommended companion | External capability; its output enters the reviewer/challenger flow as local review material |
| Multimodal agents (e.g. Codex, multimodal LLMs) | External capability | Screenshots can be processed by external multimodal agents and converted into structured evidence; SmartMoney-Cub consumes structured evidence only |
| Data source adapters, report generators, evaluation tools | Reserved slots | Read-only exports and toy fixtures only; no broker execution, no account writes |

TradingAgents usage (both modes require your own local setup):

```bash
# report-only: generate a report in TradingAgents, then import it
smcub tradingagents-ingest --report path/to/report.md --ticker 600519.SS --analysis-date 2026-07-06

# optional local bridge: explicit opt-in flags required
smcub tradingagents-run --ticker 600519.SS --analysis-date 2026-07-06 --allow-network --ack-external-llm
```

See [docs/integrations.md](docs/integrations.md) and [docs/tradingagents-adapter.md](docs/tradingagents-adapter.md).

## Safety and Limitations

Every manifest, decision, outcome, evaluation, registry, doctor, and loop output carries:

```text
READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE
```

By design, SmartMoney-Cub is:

- **Local-first** — no server, no telemetry, no upload; your trading logic evolves only on your machine
- **Read-only** — no order placement, no cancellation, no account modification, no broker automation
- **Human-in-the-loop** — champion rules never mutate automatically

Current limitations, stated honestly:

- No built-in OCR or image parsing. Screenshots can be processed by external multimodal agents (e.g. Codex or user tools) and converted into structured evidence; SmartMoney-Cub consumes structured evidence only.
- No broker connectivity of any kind — by design, not as a missing feature.
- No prediction or stock-picking capability.
- `evidence_pack.sha256` is local tamper detection, not a certification signature.
- The `--sandbox` flag selects an output directory (`tmp/sandbox`); it is not OS-level sandboxing.
- Public examples are toy offline data only.

See [docs/safety.md](docs/safety.md) and [docs/privacy.md](docs/privacy.md).

## Documentation

- [docs/harness-contract.md](docs/harness-contract.md) — the core safety contract (technical name kept for compatibility)
- [docs/architecture.md](docs/architecture.md) — Evidence & Review Core architecture
- [docs/user-guide.md](docs/user-guide.md) — user guide
- [docs/agent-loop.md](docs/agent-loop.md) / [docs/agent-integration.md](docs/agent-integration.md) — coding agent collaboration
- [docs/decision-schema.md](docs/decision-schema.md) — decision record schema
- [docs/evolution-loop.md](docs/evolution-loop.md) / [docs/memory-loop.md](docs/memory-loop.md) — rule and memory loops
- [docs/integrations.md](docs/integrations.md) — integration policy
- [docs/public-vs-private-quantkb.md](docs/public-vs-private-quantkb.md) — public/private boundary

## Roadmap

- Richer structured-evidence import formats for external multimodal agent output
- Better local review report rendering
- More evaluation metrics for challenger rule trials
- Additional documented adapters (evidence-only, read-only)

Roadmap items never include order execution, broker automation, or automatic champion mutation.

## Contributing

1. Read [AGENTS.md](AGENTS.md) and [docs/harness-contract.md](docs/harness-contract.md).
2. Keep the safety declaration on every output surface.
3. Use toy offline data in all examples and tests.

```bash
pip install -e ".[dev]"
pytest -q
python -m smartmoney_cub.cli doctor
```

## License

MIT. See [LICENSE](LICENSE).
