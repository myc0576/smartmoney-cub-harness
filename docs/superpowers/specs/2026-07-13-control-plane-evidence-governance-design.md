# Control Plane Evidence Governance Design

## Goal

Strengthen Smartmoney Cub Harness as a local-first, read-only, agent-agnostic control plane for trading review and evidence governance without adding an LLM runtime, broker connectivity, stock selection, or autonomous background behavior.

## Chosen Architecture

Add two focused modules and keep the existing workflow intact:

- `run_envelope.py` owns a portable `smartmoney_cub_run_envelope.v1` artifact. `capture_run()` writes it alongside the existing manifest and decision, so old callers and artifacts remain valid.
- `evidence_pack.py` owns a `smartmoney_cub_evidence_pack.v1` directory. It freezes copies of offline decision/outcome evidence, records SHA-256 hashes, reuses `evaluate_decision()` for deterministic replay, and computes the same five metrics used by the registry gate.
- `registry.py` remains the only champion mutation point. A candidate in `blocked` or `pending_review`, or carrying failures, cannot be promoted even when confirmation is requested.
- `cli.py` exposes validation/build/replay commands; all paths emitted in artifacts are relative or redacted.

This avoids a workflow engine, database, rule DSL, embedded model, or new dependency.

## Run Envelope Contract

Every new capture writes `run_envelope.json` with:

- schema, run id, decision time, mode, and the mandatory safety declaration;
- external Agent name, optional version, and interface, with no vendor-specific behavior;
- a canonical SHA-256 input snapshot over redacted command specifications;
- normalized tool calls with relative evidence references, timestamps, return status, and attempt number;
- total and trailing-consecutive failure counts;
- status: `completed` for no failures, `pending_review` for fewer than three consecutive failures, and `blocked` for three or more;
- an explicit permission scope declaring local-only operation, no network, no broker, no account mutation, no order/cancel/trade, and writes limited to the run directory;
- `champion_mutated: false` and `core_rules_mutated: false`.

Validation rejects missing safety fields, unsupported status values, absolute evidence paths, mismatched failure status, or any permission that enables trading, broker access, network access, account mutation, or core-rule mutation.

## Benchmark / Evidence Pack Contract

`build-evidence-pack` accepts one or more existing offline run directories and a rule-candidate JSON file. It copies decision, outcome, and evaluation payloads into a new pack, hashes every frozen artifact, and writes a manifest containing:

- the fixed metric contract: sample count, false-alert rate, missed-opportunity rate, future-leakage count, and risk-contract-violation rate;
- replay results produced by the existing evaluator rather than a new rule language;
- a frozen snapshot of the challenger rule candidate;
- failure counts and a review state;
- a human promotion gate that can recommend review but never mutates a champion.

`replay-evidence-pack` verifies hashes, reruns evaluation, recomputes metrics, and compares them with the frozen pack. Tampering or replay mismatch produces `pending_review`; three or more consecutive replay failures produce `blocked`. Weak but valid metrics remain `challenger`; passing evidence becomes `ready_for_review`. None of these states performs promotion.

## Compatibility and Safety

- Existing `capture_run()` arguments and return keys remain valid; new Agent metadata is optional.
- Existing manifest, decision, outcome, evaluation, and registry schemas stay at v1.
- Existing direct registry promotion remains available only for successful candidates with explicit confirmation; failure/review states add a stricter blocker.
- Examples remain toy-only and offline. No absolute local paths, private records, credentials, cookies, account identifiers, or watchlists are added.
- Every new artifact and CLI result carries `READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE`.

## Verification

Tests will cover envelope generation and validation, failure-state transitions, evidence freezing and replay, tamper detection, fixed metrics, registry blocking, CLI examples, safety declarations, redaction, and backward compatibility. Final verification runs the full pytest suite, bytecode compilation, doctor, CLI help, and targeted privacy scans.
