# Architecture

`smartmoney-cub-harness` is a local-first, read-only, agent-agnostic control plane for trading review and evidence governance. An external Agent or CLI can call it, but the caller does not own the resulting provenance, replay, or promotion decision.

```mermaid
flowchart LR
  subgraph Caller["External caller -- outside the harness"]
    A["Any Agent or CLI"]
  end

  subgraph Control["Read-only control plane"]
    C["capture-run"]
    R["Run Envelope"]
    V["validate-envelope"]
    B["Frozen Benchmark / Evidence Pack"]
    P["Deterministic replay"]
  end

  subgraph Governance["Human governance"]
    H["Explicit confirmation gate"]
    G["Champion registry mutation"]
  end

  A --> C --> R --> V --> B --> P --> H
  H -->|"confirmed only"| G
```

The Run Envelope and Evidence Pack are control-plane artifacts outside the external Agent. The caller supplies metadata and offline commands; the harness records the actual results, validates artifact references as portable relative paths, freezes hashes, seals the exact pack manifest bytes, and recomputes evaluation during replay. A passing replay can make evidence eligible for human review, but it cannot mutate the champion registry. Registry mutation remains behind the explicit `register-candidate --confirm-promote` action.

Machine-readable contracts:

- [`schemas/run-envelope.schema.json`](../schemas/run-envelope.schema.json)
- [`schemas/evidence-pack.schema.json`](../schemas/evidence-pack.schema.json)

## Artifact flow

1. `capture-run` executes only the requested offline command or toy preset and writes `run_manifest.json`, `run_envelope.json`, `decision.json`, and captured stdout/stderr metadata.
2. `validate-envelope` checks Agent identity, permissions, evidence paths, tool outcomes, failure counts, and the safety declaration.
3. D1/D3 outcome data is added from a local toy fixture.
4. `build-evidence-pack` freezes the rule candidate plus manifest, decision, outcome, and evaluation for every sample, records SHA-256 hashes and review metrics, and writes `evidence_pack.sha256` over the exact manifest bytes.
5. `replay-evidence-pack` verifies the manifest seal, manifest structure, complete hash inventory, artifact hashes, and deterministic recomputation of validation, evaluation, metrics, and failure state.
6. A human reviews eligible evidence. Rule promotion still requires explicit confirmation.

## Status ownership

| Artifact | Status field | Values | Meaning |
| --- | --- | --- | --- |
| Run Envelope | `status` | `completed`, `pending_review`, `blocked` | Tool-run completion and failure state |
| Evidence Pack | `review_status` | `challenger`, `ready_for_review`, `pending_review`, `blocked` | Frozen evidence readiness for human review |
| Replay report | `evidence_status` | `verified`, `pending_review`, `blocked` | Integrity and deterministic replay result |
| Decision | `action_label` | `SILENT`, `ALERT`, `ERROR`, `WATCH`, `AVOID`, `EMPTY_POSITION` | Recorded observation context, never an order |

Workflow statuses are not trading action labels.

## Module map

- `run_capture.py`: runs offline commands and writes portable run artifacts.
- `run_envelope.py`: records Agent metadata, actual tool results, output evidence, permissions, and failure state.
- `manifest.py`: validates provenance, data quality, and anti-future-leakage constraints.
- `decision.py`: derives recorded observation labels and required risk context.
- `outcome.py` and `evaluator.py`: build and review delayed D1/D3 toy outcomes.
- `evidence_pack.py`: freezes evidence, hashes artifacts, and performs deterministic replay.
- `registry.py`: stores challengers and enforces explicit champion promotion.
- `safety.py`: redacts sensitive values and local absolute paths.

## Trust boundaries

The public core has no network requirement, embedded LLM, broker access, account mutation, order, cancel, or trade capability. In the Run Envelope, `writes: run_directory_only` and the other denied capabilities are a declarative, explicitly unverified policy (`enforcement: declarative`, `verified: false`). The harness does not sandbox arbitrary captured commands; callers must use an OS/container sandbox when enforcement is required. Separately, harness governance commands may write local evidence and registry artifacts. The pack seal detects local in-place changes but is not an authenticated signature. Champion registry mutation still requires a human to invoke `register-candidate --confirm-promote`. Public fixtures contain toy data only.

Every applicable artifact carries:

```text
READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE
```
