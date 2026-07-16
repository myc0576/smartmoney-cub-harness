# Changelog

## Unreleased

### Added

- Run Envelope v1 for external-Agent provenance, reconciled offline tool results, output evidence paths, fixed permissions, and failure status.
- Evidence Pack v1 for frozen D1/D3 samples, artifact hashes, review metrics, and deterministic replay.
- `validate-envelope`, Agent metadata options on `capture-run`, `build-evidence-pack`, and `replay-evidence-pack` CLI support.
- Challenger evidence states and an explicit human confirmation gate before champion registry mutation.
- Machine-readable schemas at `schemas/run-envelope.schema.json` and `schemas/evidence-pack.schema.json`.
- Explicit `declarative` / unverified Run Envelope permission semantics so provenance is not mistaken for subprocess sandbox enforcement.
- `evidence_pack.sha256`, fail-closed manifest validation, complete hash-inventory checks, and safe `pending_review` reports for invalid packs.

### Compatibility

- Existing v1 manifest, decision, outcome, evaluation, registry, case, ledger, memory, and mentor-fit artifacts remain supported.
- Existing commands remain supported; the new control-plane commands and `capture-run` metadata options are additive.

Safety remains `READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE`.
