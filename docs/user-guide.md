# User Guide

This harness helps a subjective trader review decisions after evidence arrives. It does not tell you what to trade and does not touch execution.

## 5-Second Start

```bash
pip install -e ".[dev]"
smcub loop --preset toy --agent-trigger "自进化"
```

Open the generated `loop_report.md` first, then inspect `trace.jsonl` when you want a step-by-step audit trail.

## Normal Inputs

The public repo ships toy examples only. In private local work, the workflow can structure:

- Trading plan text.
- Trading journal CSV.
- TongHuaShun or broker screenshots.
- Read-only exports.
- Manual notes.

Keep private inputs outside the public repo.

## Review Fields

A useful non-silent observation should carry:

- Decision time.
- Data source.
- Available time.
- Data quality.
- Thesis.
- Invalidation.
- Time stop.
- Give-up conditions.
- D1/D3 outcome.
- Evaluation grade.
- Failure tags.
- Challenger rule candidate if the review suggests a rule change.

## Safe CLI Path

```bash
smcub privacy-audit
smcub loop --preset toy --agent-trigger "自进化"
smcub inspect-artifacts <run_dir>
```

`READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE` must remain present in generated artifacts.
