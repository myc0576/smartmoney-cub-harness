# Harness Contract

`smartmoney-cub-harness` is a read-only trading companion harness. It records decisions, validates provenance, reviews D1/D3 outcomes, and evolves rules through challenger -> champion governance.

It is not a stock picker, financial adviser, broker connector, or execution system.

## Safety Declaration

Every manifest, decision, outcome, evaluation, registry, and doctor output must carry:

```text
READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE
```

## Seven Principles

1. **Read-only safety is non-negotiable.** No order placement, cancellation, account modification, or execution automation.
2. **No future leakage.** A data source with `available_at > decision_time` fails manifest validation.
3. **No non-silent observation without invalidation.** ALERT/WATCH style observations must include invalidation price, time stop, give-up conditions, data source, available time, and data quality.
4. **Public cases are learning material only.** They may inform review and rule proposals, not direct live instructions.
5. **Shadow first, explicit promotion later.** Challenger rules become champion only after metrics pass and confirmation is explicit.
6. **Provenance first.** Data sources carry fetch time, available time, and quality flag.
7. **Memory is portable text.** Public examples and docs are plain files, not private databases.

## Decision Labels

| Label | Meaning |
|---|---|
| `SILENT` | No command produced usable stdout. |
| `ALERT` | Context was recorded for review. It is not an instruction. |
| `ERROR` | One or more sources failed. |
| `WATCH` | Observation only. |
| `AVOID` | Avoidance rationale. |
| `EMPTY_POSITION` | No active exposure context. |

## Promotion Thresholds

| Metric | Threshold |
|---|---:|
| `sample_count` | `>= 20` |
| `false_alert_rate` | `<= 0.2` |
| `missed_opportunity_rate` | `<= 0.25` |
| `future_leakage_count` | `= 0` |
| `risk_contract_violation_rate` | `= 0` |

Passing thresholds may create a promotion recommendation. Champion mutation still requires explicit confirmation.
