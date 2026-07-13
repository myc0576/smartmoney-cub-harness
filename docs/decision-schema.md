# Artifact Schema Reference

The harness separates recorded observation labels from control-plane workflow states. All applicable artifacts carry `READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE`.

## Decision artifact

```json
{
  "schema": "smartmoney_cub_decision.v1",
  "run_id": "toy-run",
  "decision_time": "2026-07-13T15:30:00+08:00",
  "mode": "after-close",
  "action_label": "ALERT",
  "symbol": "TOY.CUB",
  "invalidation_price": 9.4,
  "time_stop": "D1/D3 review",
  "give_up_conditions": ["toy observation thesis is no longer supported"],
  "data_source": "toy_strategy",
  "available_at": "2026-07-13T15:30:00+08:00",
  "data_quality_flag": "ok",
  "safety": "READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE"
}
```

`action_label` may be `SILENT`, `ALERT`, `ERROR`, `WATCH`, `AVOID`, or `EMPTY_POSITION`. These labels describe recorded review context; none is an order or recommendation. Every non-silent observation must include `invalidation_price`, `time_stop`, `give_up_conditions`, `data_source`, `available_at`, and `data_quality_flag`. A source with `available_at > decision_time` fails validation.

## Run Envelope v1

Machine schema: [`schemas/run-envelope.schema.json`](../schemas/run-envelope.schema.json)

| Field | Type / values | Purpose |
| --- | --- | --- |
| `schema` | `smartmoney_cub_run_envelope.v1` | Contract version |
| `run_id`, `decision_time`, `mode` | strings | Run identity, cutoff, and mode |
| `safety` | fixed declaration | Read-only safety contract |
| `agent` | object | External caller `name`, nullable `version`, and `interface` |
| `input_snapshot_sha256` | 64 hex characters | Hash of redacted command input |
| `tool_calls` | array | Actual timestamps, return code, timeout, status, attempt, and evidence paths per call |
| `output_evidence` | relative-path array | Portable stdout, stderr, and metadata artifacts |
| `failure_count` | integer `>= 0` | Failed call count |
| `trailing_consecutive_failure_count` | integer `>= 0` | Failures at the end of the run |
| `status` | `completed`, `pending_review`, `blocked` | Run workflow state |
| `permission_scope` | object | Declarative, unverified policy: denied capabilities fixed to `false`, writes fixed to `run_directory_only`, `enforcement` fixed to `declarative`, and `verified` fixed to `false` |
| `champion_mutated`, `core_rules_mutated` | `false` | Capture never changes governed rules |

Run status meaning:

- `completed`: no tool call failed.
- `pending_review`: one or more calls failed, but fewer than three failures trail the run.
- `blocked`: at least three consecutive failures trail the run.

The permission scope is provenance, not a sandbox attestation. The harness validates the declaration and portable evidence paths but does not prove that an arbitrary subprocess complied with it.

## Evidence Pack v1

Machine schema: [`schemas/evidence-pack.schema.json`](../schemas/evidence-pack.schema.json)

| Field | Type / values | Purpose |
| --- | --- | --- |
| `schema` | `smartmoney_cub_evidence_pack.v1` | Contract version |
| `horizon` | `d1` or `d3` | Delayed review horizon |
| `rule_candidate_path` | relative path | Frozen challenger payload |
| `samples` | non-empty array | Frozen manifest, decision, outcome, evaluation, validation, grade, and failure state |
| `hashes` | relative path -> SHA-256 | Integrity map for every frozen artifact |
| `metrics` | object | Sample count, false-alert rate, missed-opportunity rate, future-leakage count, and risk-contract violation rate |
| `failure_count` | integer `>= 0` | Failed sample count |
| `trailing_consecutive_failure_count` | integer `>= 0` | Failures at the end of the sample list |
| `review_status` | `challenger`, `ready_for_review`, `pending_review`, `blocked` | Evidence governance state |
| `promotion_gate` | object | Eligibility plus required human confirmation; mutation flags remain `false` |
| `safety` | fixed declaration | Read-only safety contract |

`build-evidence-pack` also writes `evidence_pack.sha256`, the SHA-256 of the exact `evidence_pack.json` bytes. Replay verifies that seal and the complete manifest/hash inventory before reading frozen artifacts. The seal detects local tampering but is not an authenticated signature.

Evidence review status meaning:

- `challenger`: evidence is valid but promotion thresholds are not met.
- `ready_for_review`: thresholds pass and a human may review; no promotion has occurred.
- `pending_review`: one or more samples failed or need review.
- `blocked`: at least three consecutive samples failed.

`replay-evidence-pack` writes `replay_report.json`. Its `evidence_status` is `verified` only when frozen hashes and recomputed results match with no failed sample; otherwise it is `pending_review`, or `blocked` after at least three trailing failures.

## Status versus action label

| Concept | Field | Governs |
| --- | --- | --- |
| Observation label | `decision.action_label` | What context was recorded for later review |
| Run workflow | `run_envelope.status` | Whether offline tool execution completed cleanly |
| Pack workflow | `evidence_pack.review_status` | Whether frozen evidence is a challenger, review-ready, pending, or blocked |
| Replay workflow | `replay_report.evidence_status` | Whether integrity and deterministic replay are verified |

Never present `completed`, `pending_review`, `blocked`, `challenger`, `ready_for_review`, or `verified` as trading action labels.
