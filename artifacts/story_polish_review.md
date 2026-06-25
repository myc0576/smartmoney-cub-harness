# Story Polish Review

Generated: 2026-06-25

## README Change Summary

- Rebuilt `README.md` and `README.zh-CN.md` around the "聪明资金幼年体 / 游资幼年体" story.
- Repositioned the project as an AI decision harness for subjective A-share traders, not a generic engineering README.
- Added a bilingual first-screen story: the "小资金做大的神话" is treated as review language and discipline training, not as a project promise.
- Added clearer "What it is" and "What it is not" sections, including the semi-quantitative bridge between human discretion and machine-audited review.
- Added Account & Screenshot Input sections for read-only exports, local adapters, CSV journals, watchlists, TongHuaShun/broker screenshots, and handwritten notes.

## 易经 Modularization

The README pair and `docs/philosophy.md` now explain where 易经 thinking lives without mystic forecasting:

- Market Regime / Sentiment Cycle maps to decision context, outcome tags, and Markdown memory.
- Timing & Position maps to `decision_time`, `available_at`, and D1/D3 horizon review.
- Change vs Invariance maps to manifest validation, evaluator checks, and registry governance.
- Advance / Retreat / Restraint maps to `WATCH`, `AVOID`, `EMPTY_POSITION`, and risk contracts.
- Opposing Evidence maps to the agent challenger role and failure tags.

## Systems Engineering Modularization

The README pair and `docs/philosophy.md` now map systems-engineering language to concrete harness modules:

- Goal Tree separates annual, monthly, single-trade, and review goals.
- Decomposition & Integration flows through `manifest`, `decision`, `outcome`, and `evaluation`.
- Feedback Loop is expressed as Plan -> Observe -> Decide -> Record -> Outcome -> Evaluate -> Evolve.
- Human-Machine Collaboration is enforced through `docs/agent-integration.md`.
- Qualitative-to-Quantitative Review maps subjective observations to D1/D3 evaluation and challenger -> champion governance.

## Semi-Quant Subjective Trading Positioning

The new section `Not Quant Trading. Not Pure Discretion. A Semi-Quant AI Decision Harness.` distinguishes:

- Traditional quant systems: strategy-first, backtest-first, signal-seeking, sometimes automated.
- `smartmoney-cub-harness`: human-decision-first, evidence-chain-first, AI-challenged, D1/D3-reviewed, never executing trades.

Core message: it is not the strategy itself; it is the container where a strategy grows up.

## Core Loop Diagram

The README pair now uses a multi-layer Mermaid diagram with GitHub-friendly theme initialization:

- Human Trader.
- Read-only Inputs.
- Smartmoney Cub Harness.
- AI Agent Companion.

The diagram keeps node labels short and bilingual while avoiding dense cross-arrows.

## Compliance Review

Safety language was strengthened with the unified disclaimer:

- English: research, journaling, review, educational workflow only; not financial advice, not stock recommendation, not price prediction, not execution.
- Chinese: research, trading journal, review, educational workflow only; no individual-stock recommendation, no price prediction, no return promise, no execution.

Compliance scan summary:

- Strict prohibited phrase scan: no hits for recommendation, guaranteed-profit, limit-up, VIP pool, or buy/sell-point phrases.
- Contextual terms such as "龙头", "小资金做大", "收益", "账户", "截图", "QMT", and "同花顺" appear only inside story framing, disclaimer, read-only input boundary, or compliance explanation.
- Token pattern scan: no matches in publishable files.

## Test Results

```text
python -m pip install -e ".[dev]"              PASS
pytest -q                                      PASS: 22 passed
python -m smartmoney_cub_harness.cli doctor    PASS: status ok
python -m smartmoney_cub_harness.cli --help    PASS
git status --short --branch                    PASS: expected docs/artifact changes only
```
