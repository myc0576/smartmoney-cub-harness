# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Rebrand: **SmartMoney-Cub** is now the single public product brand. The former
  "Harness" naming is retired from public narrative; the engine is referred to as
  the **Evidence & Review Core** (证据与复盘核心).
- README.md rewritten in English and README.zh-CN.md in Simplified Chinese with a
  unified structure (Why / What Works Today / 60-Second Quick Start / How It Works /
  Outputs / Optional Integrations / Safety and Limitations / Documentation /
  Roadmap / Contributing / License).
- Capability claims aligned with the actual implementation: image/screenshot
  understanding is documented as an external capability (e.g. Codex or multimodal
  agents produce structured evidence); SmartMoney-Cub consumes structured evidence
  only.
- `pyproject.toml` metadata: corrected description, removed misleading keywords
  (`backtesting`, `mcp`, `skills`, `agent-harness`), added project URLs.
- Cover copy unified to "OPEN SOURCE · LOCAL-FIRST · READ-ONLY / SmartMoney-Cub /
  AI-assisted trading review and evidence system / 本地优先的 AI 交易复盘与证据系统".

### Unchanged safety contract

- `READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE` remains on every manifest, decision,
  outcome, evaluation, registry, doctor, and loop output.
- No broker execution, no automatic order placement or cancellation, no automatic
  champion-rule mutation. Champion promotion still requires
  `smcub confirm-promotion`.

### Compatibility notes

- `docs/harness-contract.md` keeps its file name for link compatibility; its
  content now presents the SmartMoney-Cub core safety contract.
- The Python package remains `smartmoney_cub` and the CLI remains `smcub`.
  No import paths or commands changed.
