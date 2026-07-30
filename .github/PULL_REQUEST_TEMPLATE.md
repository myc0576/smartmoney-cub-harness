<!-- Suggested title: Rebrand to SmartMoney-Cub (Evidence & Review Core) + bilingual flowchart -->

## Summary

This PR completes the rebrand of the public offline core to **SmartMoney-Cub**, with the harness layer unified under **Evidence & Review Core**. It does **not** add any trading execution, order placement/cancellation, or broker automation — the read-only safety contract is fully preserved.

Changes (6 commits relative to `main`: one baseline + five rebrand):

- **docs** (`1fb8b9c`): Split English/Chinese README; rewrote brand narrative across `docs/`, `AGENTS.md`, `CLAUDE.md`; cleaned `pyproject.toml` metadata (description, project URLs, removed misleading keywords such as backtesting/mcp/skills/agent-harness); added `CHANGELOG.md`; `doctor` now reports `product` / `component`.
- **design** (`222009b`): Unified cover copy to `OPEN SOURCE · LOCAL-FIRST · READ-ONLY / SmartMoney-Cub`; re-rendered cover PNG.
- **test** (`8c107d7`): Added bilingual system flowchart (`opendesign/flowchart/flow.html`) with a visual-regression check at 100% / 50% / 33% zoom.
- **chore** (`c022557`): Added `.gitattributes` (LF / binary classification) for line-ending policy.
- **test** (`263ce06`): Fixed flowchart render (full-page + trimmed, dedicated deliverable file so zoom proofs no longer overwrite it) and added a true horizontal-overflow guard via CDP (`overflow_check.mjs`); the 5号 HUMAN APPROVAL arrow is rerouted down-then-left to avoid crossing the MEMORY connector.
- **chore** (`b0e6ec7`): Stopped force-tracking the local-only draft cover SVG (now gitignored).

## Safety & Limitations (unchanged)

- `READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE` contract preserved on every manifest / decision / outcome / doctor output.
- Local-first, read-only, human-in-the-loop. No broker execution, no automatic order placement/cancellation, no automatic champion-rule mutation.
- Screenshot / multimodal understanding is an **external capability** (e.g. Codex / multimodal LLM converting to structured evidence); the core only consumes structured evidence.
- TradingAgents: documented-adapter / optional-bridge only. UZI-Skill: recommended companion (external), not a dependency.

## Verification

- `pytest -q` passes (61 tests).
- `python -m smartmoney_cub.cli doctor` → `product=SmartMoney-Cub`, `component=Evidence & Review Core`, `safety=READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE`.
- Flowchart visual regression: 100% / 50% / 33% all `scrollWidth == innerWidth` (no horizontal overflow).

## 中文摘要

本次将公开离线核心统一品牌为 **SmartMoney-Cub**，原 harness 功能归入 **Evidence & Review Core**。未新增任何交易执行、下单/撤单或券商自动化，只读安全契约完整保留。

- 文档：中英 README 分离，统一品牌叙事，清理 `pyproject` 元数据，新增 `CHANGELOG`。
- 视觉：封面文案统一为 SmartMoney-Cub 并重新渲染。
- 测试：新增双语流程图及 100% / 50% / 33% 三档视觉回归校验；用 CDP 真实检测水平溢出。
- 工程：新增 `.gitattributes` 行尾规范；草稿封面 SVG 不再强制跟踪。
