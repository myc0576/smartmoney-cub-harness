# Agent Loop

Coding agents should treat this repository as a read-only review harness.

## Trigger Words

Users may say:

- `loop`
- `自进化`
- `复盘一下`
- `规则进化`

The safe default command is:

```bash
smcub loop --preset toy --agent-trigger "自进化"
```

## Required Agent Behavior

1. Run the toy offline loop.
2. Read `loop_report.md`.
3. Read `trace.jsonl` when audit evidence is needed.
4. Propose review, redaction, schema, or workflow improvements.
5. Keep rule updates as challenger candidates.
6. Preserve `champion_mutated=false` unless a human explicitly confirms champion mutation through the governance path.

## Forbidden Agent Behavior

Agents must not add or perform:

- Order placement.
- Order cancellation.
- Broker automation.
- Account modification.
- Live execution.
- Credential handling.
- Real watchlist publication.
- Private strategy prompt publication.

## Output Contract

Loop output must include:

- `loop_report`
- `trace`
- `case_record`
- `memory_record`
- `ledger`
- `champion_mutated=false`
- `network_required=false`
- `telemetry=false`
- `READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE`
