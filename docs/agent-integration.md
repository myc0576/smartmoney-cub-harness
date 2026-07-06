# Agent Integration

Agents can use this repository as a disciplined artifact layer for subjective trading review. They must behave like reviewers, challengers, archivists, and drift detectors, never like stock pickers or execution systems.

`smartmoney-cub-harness` is agent-agnostic. The harness itself does not embed or
require an OpenAI API key, Anthropic API key, Gemini API key, or any built-in
LLM provider. External agents bring their own reasoning environment, read the
local contract files, and call the `smcub` CLI.

See [external-review-brain.md](external-review-brain.md) for the higher-level
positioning.

## External Review Brain Flow

```text
External Agent -> read contract -> run smcub CLI -> inspect artifacts -> write review/challenger notes -> human approves rule promotion
```

## Recommended Flow

1. Run `smcub capture-run` against an offline command, toy fixture, screenshot extraction step, or user-provided local note parser.
2. Read `run_manifest.json`, `decision.json`, and captured artifacts.
3. Treat `ALERT` as recorded context, not an instruction.
4. Generate opposing evidence questions before strengthening any thesis.
5. Wait for D1/D3 outcome data.
6. Run `smcub evaluate-run`.
7. Propose a rule candidate only from evaluated evidence.
8. Keep rule promotion in challenger state unless metrics pass and the human explicitly confirms champion mutation.

## Optional UZI Short-Horizon Plugin

When a user asks for A-share short-horizon analysis, hot-money review, LHB/龙虎榜 context, trap detection, or "A 股速判", agents may use the optional UZI-Skill adapter. This is a local plugin flow, not part of the offline public core.

1. Run `smcub uzi-status`.
2. If the status is `requires_integration`, ask the user for permission before installing the external plugin.
3. After explicit permission, run `smcub uzi-install`.
4. Run `smcub uzi-scan <symbol>` for a read-only observation.
5. Read the generated `run_manifest.json`, `decision.json`, and `artifacts/uzi_observation.json`.
6. Treat the result as `WATCH`/review evidence only. Do not convert it into buy/sell instructions.

`uzi-scan` is allowed to use public network data and records `network_required=true` on the run. It still disables broker/account integrations, remote report sharing, and any order or cancellation behavior. Non-error observations must include a derived invalidation price, D1/D3 review time stop, give-up conditions, data source, available time, data quality, and:

```text
READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE
```

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
- Never treat an external agent's research view as an executable order.
- Never require a built-in LLM provider or API key for the harness runtime.
- Never infer missing invalidation fields.
- Never soften future-leakage failures.
- Never put private user data into public examples.
- Never treat a screenshot or account export as permission to act.
- Always generate or preserve opposing evidence for non-silent observations.
- Always preserve the safety declaration.

```text
READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE
```
