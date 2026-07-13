# Agent Integration

Any external Agent or CLI can use the harness as a local evidence boundary. The harness is vendor-neutral: it does not import an Agent SDK, host a model, require a model provider, or embed an LLM. Agent identity is descriptive provenance, not authorization.

## Integration sequence

1. Call `smcub capture-run` with an offline command or the toy preset plus `--agent-name`, optional `--agent-version`, and `--agent-interface`.
2. Read the returned run directory and validate its `run_envelope.json` with `smcub validate-envelope`.
3. Add delayed D1/D3 outcome data from a local source and build a frozen pack with `smcub build-evidence-pack`.
4. Verify integrity and recomputed results with `smcub replay-evidence-pack`.
5. Present eligible evidence to a human. Do not promote a challenger or mutate core rules automatically.

See the [Run Envelope schema](../schemas/run-envelope.schema.json) and [Evidence Pack schema](../schemas/evidence-pack.schema.json) for machine-readable contracts.

## Permission scope

The Run Envelope records the caller's intended scope as a declarative policy:

| Capability | Allowed value |
| --- | --- |
| Network | `false` |
| Broker access | `false` |
| Account mutation | `false` |
| Order / cancel / trade | `false` |
| Embedded LLM | `false` |
| Writes | `run_directory_only` |
| Enforcement | `declarative` |
| Verified | `false` |

These fields are provenance, not a sandbox attestation. `capture-run` does not isolate or inspect an arbitrary subprocess deeply enough to prove network, broker, account, or filesystem compliance. Its `--sandbox` option only selects the `tmp/sandbox` output namespace. Put untrusted commands inside an OS/container sandbox and record that separately; the harness deliberately reports its own policy as unverified.

Do not interpret access to local notes, screenshots, or exported data as permission to act. Public examples must remain toy-only and must not contain private watchlists, account identifiers, credentials, cookies, personal trading records, or local absolute paths.

## Output evidence

Each tool call records its name, timestamps, return code, timeout flag, attempt number, reconciled success/failure status, and relative paths to stdout, stderr, and metadata. `output_evidence` lists those paths. The harness hashes frozen Evidence Pack artifacts and replay recomputes validation, evaluation, metrics, and failure counts instead of trusting the external Agent's claims. It also writes `evidence_pack.sha256` over the exact manifest bytes. This is local tamper evidence, not an authenticated signature; replay fails closed to `pending_review` when the seal or manifest contract is invalid.

An Agent may summarize or challenge this evidence. It must not rewrite frozen evidence, convert `ALERT` or another `action_label` into an instruction, or claim that review eligibility equals promotion.

## Failure handling

| Context | Status | Required caller behavior |
| --- | --- | --- |
| Run Envelope | `completed` | Continue to evidence construction when delayed outcome data is available. |
| Run Envelope | `pending_review` | Surface one or more tool failures; do not silently continue. |
| Run Envelope | `blocked` | Stop the workflow after three or more trailing failures. |
| Evidence Pack | `challenger` | Preserve as a proposal; metrics do not meet the human-review gate. |
| Evidence Pack | `ready_for_review` | Present to a human; do not mutate the registry. |
| Evidence Pack | `pending_review` | Surface failed samples or inconsistencies. |
| Evidence Pack | `blocked` | Stop after three or more trailing sample failures. |
| Replay report | `verified` | Integrity and deterministic recomputation passed. |
| Replay report | `pending_review` / `blocked` | Surface hash/result mismatches or failures and do not promote. |

These are workflow statuses, not trading action labels.

## Agent responsibilities

- Preserve invalidation, time stop, give-up conditions, source availability, and data quality for every non-silent observation.
- Treat `available_at > decision_time` as a validation failure.
- Generate opposing-evidence questions before strengthening a thesis.
- Keep challenger-to-champion promotion behind explicit human confirmation.
- Preserve the safety declaration on applicable artifacts and outputs:

```text
READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE
```
