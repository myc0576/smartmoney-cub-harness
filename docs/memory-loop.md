# Memory Loop

The memory loop turns a completed review into reusable local text artifacts.

## Artifacts

- `case_record.json`: normalized offline case with decision, outcome, and evaluation payloads.
- `memory.md`: redacted local Markdown memory for human and agent review.
- `evolution_ledger.jsonl`: append-only rule and review events.
- `proposed_challenger_rule.json`: a candidate rule that does not mutate champion state.
- `rule_registry.json`: challenger/champion governance state.

## Flow

```text
Decision -> Outcome -> Evaluation -> Case Record -> Markdown Memory -> Ledger -> Challenger Rule
```

## Governance

Challenger rules are cheap to propose. Champion mutation is intentionally expensive:

- Metrics must pass thresholds.
- A promotion can be recommended.
- Champion mutation still requires explicit human confirmation.

The toy loop always writes `champion_mutated=false`.

## Redaction

Memory output is rendered through the same redaction layer used by CLI JSON output. It masks common emails, phone numbers, token/cookie/account assignments, and local home paths.
