# Agent Integration

Agents can use this repository as a disciplined artifact layer.

## Recommended Flow

1. Run `smcub capture-run` against an offline command.
2. Read `run_manifest.json`, `decision.json`, and captured artifacts.
3. Do not treat `ALERT` as an instruction.
4. Wait for D1/D3 outcome data.
5. Run `smcub evaluate-run`.
6. Propose a rule candidate only from evaluated evidence.

## Agent Rules

- Never ask the harness to place or cancel orders.
- Never infer missing invalidation fields.
- Never soften future-leakage failures.
- Never put private user data into public examples.
- Always preserve the safety declaration.
