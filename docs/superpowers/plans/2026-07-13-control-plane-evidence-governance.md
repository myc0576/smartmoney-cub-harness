# Control Plane Evidence Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add standardized run provenance and deterministic benchmark evidence governance while preserving the read-only public contract.

**Architecture:** Add focused envelope and evidence-pack modules, integrate them through the existing capture and CLI surfaces, and reuse evaluator/registry behavior. All outputs remain offline JSON with explicit human gates.

**Tech Stack:** Python 3.10+, standard library, argparse, pytest; no new dependencies.

## Global Constraints

- Every new artifact and doctor/CLI result carries `READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE`.
- No LLM runtime, broker connection, order/cancel/trade capability, stock selection, account mutation, network dependency, or background agent.
- Toy/offline data only; relative artifact paths only; redact sensitive values before persistence.
- Preserve existing public function signatures and v1 schemas unless only adding optional return fields.

---

### Task 1: Run Envelope

**Files:** create `src/smartmoney_cub_harness/run_envelope.py`, create `tests/test_run_envelope.py`, modify `src/smartmoney_cub_harness/run_capture.py`, `src/smartmoney_cub_harness/schemas.py`, and `tests/test_run_capture.py`.

**Produces:** `build_run_envelope(...) -> dict`, `validate_run_envelope(envelope) -> dict`, and `run_envelope.json` from every capture.

- [ ] Write tests asserting normalized Agent metadata, input hash, tool calls, relative evidence, fixed permissions, and the safety declaration.
- [ ] Run the targeted tests and confirm they fail because the module/artifact does not exist.
- [ ] Implement the minimal envelope builder/validator and optional capture arguments.
- [ ] Run targeted and existing capture tests until green.
- [ ] Add tests for `completed`, `pending_review`, and `blocked` transitions; confirm red then green.

### Task 2: Benchmark / Evidence Pack

**Files:** create `src/smartmoney_cub_harness/evidence_pack.py`, create `tests/test_evidence_pack.py`, modify `src/smartmoney_cub_harness/schemas.py` and `src/smartmoney_cub_harness/registry.py`.

**Produces:** `build_evidence_pack(...) -> dict`, `replay_evidence_pack(...) -> dict`, fixed metric calculation, frozen SHA-256 samples, and a human promotion gate.

- [ ] Write tests for sample freezing, fixed metrics, deterministic replay, and no champion mutation.
- [ ] Run the targeted tests and confirm missing APIs fail.
- [ ] Implement freezing, hashing, evaluator reuse, and review-state derivation using only the standard library.
- [ ] Run targeted tests until green.
- [ ] Write and verify tamper/failure tests, then block registry promotion for `blocked`, `pending_review`, or nonzero failure counts.

### Task 3: CLI and Machine-Readable Schemas

**Files:** modify `src/smartmoney_cub_harness/cli.py`, create `schemas/run-envelope.schema.json`, create `schemas/evidence-pack.schema.json`, and create/modify CLI tests.

**Produces:** `validate-envelope`, `build-evidence-pack`, and `replay-evidence-pack` commands with stable JSON output.

- [ ] Write failing CLI tests for command parsing, exit codes, safety output, and relative paths.
- [ ] Add minimal argparse wiring and JSON schema documents without adding a validator dependency.
- [ ] Run CLI and schema tests until green; confirm old commands remain unchanged.

### Task 4: Documentation and Release Notes

**Files:** modify `README.md`, `README.zh-CN.md`, `docs/architecture.md`, `docs/agent-integration.md`, `docs/decision-schema.md`, and create `CHANGELOG.md`.

**Produces:** synchronized English/Chinese positioning, architecture, artifact flow, CLI examples, boundaries, and changelog entry.

- [ ] Add concise local-first control-plane positioning and one reproducible toy/offline CLI workflow in both READMEs.
- [ ] Document envelope/evidence-pack schemas, failure states, replay, and the human gate.
- [ ] Add/read tests that execute documented command shapes and confirm safety output.

### Task 5: Verification, Review, and Delivery

**Files:** all files changed by Tasks 1-4 only; preserve unrelated working-tree files.

- [ ] Run `python -m pytest -q` and record the exact pass count.
- [ ] Run `python -m compileall -q src`, `python -m smartmoney_cub_harness.cli doctor`, and `python -m smartmoney_cub_harness.cli --help`.
- [ ] Scan tracked changes for absolute paths, secrets, broker/trading execution language, and missing safety declarations.
- [ ] Review the diff for backward compatibility and small-scope design.
- [ ] Commit only task-owned paths using the repository Lore commit protocol, push the feature branch, and create a PR against `main`.
