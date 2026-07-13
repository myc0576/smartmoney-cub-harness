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

For local private CSV review, the safe self-evolution command is:

```bash
smcub self-evolve --input-csv path/to/private_cases.csv --max-iterations 20 --time-budget-min 10 --horizon d1
```

If a promotion is recommended, champion mutation still requires an explicit human gate:

```bash
smcub confirm-promotion state/self_evolve/<loop_id>/promotion_packet.json --decision promote --note "manual approval"
```

## Required Agent Behavior

1. Run the toy offline loop.
2. Read `loop_report.md`.
3. Read `trace.jsonl` when audit evidence is needed.
4. Propose review, redaction, schema, or workflow improvements.
5. Keep rule updates as challenger candidates.
6. Preserve `champion_mutated=false` unless a human explicitly confirms champion mutation through the governance path.
7. For `self-evolve`, read `promotion_packet.json` before any `confirm-promotion` action.

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

`self-evolve` additionally writes:

- `contract.json`
- `loop_state.json`
- `self_evolve_report.md`
- `promotion_packet.json`
