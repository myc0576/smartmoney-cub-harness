# Agent Integration

Agents can use this repository as a disciplined artifact layer for subjective trading review. They must behave like reviewers, challengers, archivists, and drift detectors, never like stock pickers or execution systems.

## Recommended Flow

1. Run `smcub capture-run` against an offline command, toy fixture, screenshot extraction step, or user-provided local note parser.
2. Read `run_manifest.json`, `decision.json`, and captured artifacts.
3. Treat `ALERT` as recorded context, not an instruction.
4. Generate opposing evidence questions before strengthening any thesis.
5. Wait for D1/D3 outcome data.
6. Run `smcub evaluate-run`.
7. Propose a rule candidate only from evaluated evidence.
8. Keep rule promotion in challenger state unless metrics pass and the human explicitly confirms champion mutation.

## Agent Roles

| Role | What it can do | What it must not do |
| --- | --- | --- |
| Reviewer | Summarize plans, decisions, evidence, and delayed outcomes | Convert review into buy/sell instructions |
| Challenger | Generate opposing thesis and missing-risk questions | Cherry-pick evidence that supports the user |
| Archivist | Turn local artifacts into portable Markdown memory | Commit private account data or screenshots |
| Drift Detector | Compare current behavior with past rules | Promote rules without evaluated samples |
| Systems Assistant | Decompose goals, risk, psychology, and outcomes | Override the human's final judgment |

## Read-only Input Modes

Agents may help structure these local inputs:

- Toy JSON fixtures in public examples.
- User-written trading plans and review notes.
- Trading journal CSV files.
- Watchlist files kept outside the public repo.
- Read-only broker/account exports.
- Read-only QMT or adapter outputs if configured locally.
- TongHuaShun or broker screenshots of positions, fills, and daily review.

These inputs are for local review and structured analysis only. They must not be used to place orders, cancel orders, modify accounts, or generate public examples with real holdings or real trading records.

## Agent Rules

- Never ask the harness to place or cancel orders.
- Never infer missing invalidation fields.
- Never soften future-leakage failures.
- Never put private user data into public examples.
- Never treat a screenshot or account export as permission to act.
- Always generate or preserve opposing evidence for non-silent observations.
- Always preserve the safety declaration.

```text
READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE
```
