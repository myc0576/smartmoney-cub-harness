# SmartMoney-Cub

<div align="center">

![SmartMoney-Cub 封面](assets/smartmoney-cub-cover.png)

**OPEN SOURCE · LOCAL-FIRST · READ-ONLY**

AI-assisted trading review and evidence system
本地优先的 AI 交易复盘与证据系统

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-pytest-informational)](tests/)
[![Read-only](https://img.shields.io/badge/mode-read--only-brightgreen)](docs/safety.md)
[![Local-first](https://img.shields.io/badge/local--first-no%20telemetry-success)](docs/privacy.md)
[![Agent-ready](https://img.shields.io/badge/agent--ready-loop%20artifacts-blueviolet)](docs/agent-loop.md)

[English](README.md)

`READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE`

</div>

---

SmartMoney-Cub 是一个本地优先、只读的 AI 交易复盘系统，把交易计划、证据和延迟结果沉淀为可审计案例、长期记忆与需人工批准的规则候选。

它的引擎——**证据与复盘核心（Evidence & Review Core）**——记录你当时的计划、手上的证据、D1/D3 的实际结果，以及哪条规则候选值得进入 challenger 试炼。任何规则在你显式批准之前都不会成为 champion。

它**不是**选股机器人、预测系统、自动交易系统，也不是完整量化平台。

## 为什么需要 SmartMoney-Cub

高手每一次决策都有计划、有证据、有延迟验证、有规则迭代。普通人复盘时翻聊天记录、翻交易软件、翻截图，折腾半天还是说不清当时为什么买、错在什么地方、下一次该怎么改。

SmartMoney-Cub 把复盘结构化为这些问题：

- 决策当时的 thesis 是什么？
- invalidation、time stop、give-up conditions 是否写清楚？
- 数据源、available time、data quality 是否可靠？
- D1/D3 之后结果如何？
- 这次失败是执行问题、证据问题，还是规则问题？
- 有没有值得进入 challenger 状态的规则候选？

单次判断会忘，系统会进化。

## 当前已实现的能力

| 能力 | 状态 |
| --- | --- |
| 离线 toy 复盘闭环（`smcub loop --preset toy`） | 已实现 |
| 带溯源与安全校验的决策记录 | 已实现 |
| D1/D3 延迟结果验证（不偷看未来） | 已实现 |
| 本地 Markdown 案例记忆与进化台账 | 已实现 |
| challenger → champion 规则治理，champion 变更必须人工确认 | 已实现 |
| CLI 输出前 redaction | 已实现 |
| 本地私有 CSV 自进化循环（`smcub self-evolve`） | 已实现 |
| TradingAgents 报告导入（可选，用户自行配置） | documented adapter / optional bridge |
| 截图 / 图像理解 | 外部能力——见[安全与局限](#安全与局限) |

## 60 秒上手

```bash
git clone https://github.com/myc0576/SmartMoney-Cub.git
cd SmartMoney-Cub
pip install -e ".[dev]"
smcub loop --preset toy --agent-trigger "自进化"
```

装好后最常用的只读命令：

```bash
smcub doctor
smcub privacy-audit
smcub loop --preset toy --agent-trigger "自进化"
smcub inspect-artifacts <run_dir>
```

用 coding agent？丢一句话即可：

> 阅读 `AGENTS.md` 和 `docs/harness-contract.md`，运行 `smcub loop --preset toy --agent-trigger "自进化"`，只做只读复盘，不连接券商，不下单。

公开仓库只使用 toy 离线数据。

## 工作原理

```text
Inputs 输入
  ↓
Capture Decisions & Evidence 记录决策与证据
  ↓
Validate Provenance & Safety 校验溯源与安全
  ↓
D1 / D3 Outcome Review 延迟结果验证
  ↓
Memory & Challenger Rule 记忆与规则候选
  ↓
Explicit Human Approval 人工显式批准
```

| 环节 | 发生什么 |
| --- | --- |
| 记录 | 计划、观察和证据被记录为可审计产物 |
| 校验 | 检查溯源、available time、数据质量与安全契约；任何 `available_at > decision_time` 的数据源直接校验失败 |
| 结果验证 | 等 D1/D3 结果出现后再评价，不偷看未来 |
| 记忆与规则 | 复盘沉淀为本地 Markdown 记忆，教训生成 challenger 规则候选 |
| 人工批准 | champion 变更只能通过 `smcub confirm-promotion`——永不自动 |

可选的外部分析（如 TradingAgents 报告、多模态 agent 的输出）只能以**证据（evidence only）**身份进入这条链路。

## 输出产物

每次 loop 运行都会在本地生成：

- `loop_report.md` — 复盘报告
- `case_record.json` — 可审计案例
- `memory.md` — 可携带的 Markdown 案例记忆
- `evolution_ledger.jsonl` — 规则进化台账
- `trace.jsonl` — 逐步执行轨迹

<details>
<summary>loop 输出摘要 JSON 示例</summary>

```json
{
  "status": "ok",
  "loop_name": "observe_candidate_plan_position_outcome_review_rule_update",
  "preset": "toy",
  "champion_mutated": false,
  "network_required": false,
  "telemetry": false,
  "safety": "READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE"
}
```

</details>

<details>
<summary>全部 CLI 命令</summary>

```bash
smcub loop --preset toy --agent-trigger "自进化"
smcub privacy-audit
smcub self-evolve --input-csv path/to/private_cases.csv --max-iterations 20 --time-budget-min 10 --horizon d1
smcub confirm-promotion state/self_evolve/<loop_id>/promotion_packet.json --decision promote --note "manual approval"
smcub inspect-artifacts <run_dir>
smcub collect-case <run_dir>
smcub append-ledger --event EVENT --payload-json FILE
smcub save-memory --case-record FILE
smcub tradingagents-doctor
smcub tradingagents-ingest --report path/to/tradingagents_report.md --ticker 600519.SS --analysis-date 2026-07-06
smcub tradingagents-run --ticker 600519.SS --analysis-date 2026-07-06 --allow-network --ack-external-llm
smcub doctor
smcub validate-manifest examples/sample_run/run_manifest.json
```

</details>

## 可选集成

集成的目标是给复盘链路提供更好的证据，绝不会把 SmartMoney-Cub 变成执行系统。

| 项目 / 类别 | 状态 | 边界 |
| --- | --- | --- |
| [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) | documented adapter / optional bridge | 用户自行配置 LLM/API key；key 不保存、不收集、不上传；输出只能以证据身份进入复盘，永不作为下单意图 |
| [wbh604/UZI-Skill](https://github.com/wbh604/UZI-Skill) | 推荐搭配（外部能力） | 其输出作为本地复盘材料进入 reviewer / challenger 流程 |
| 多模态 agent（如 Codex、多模态 LLM） | 外部能力 | 截图可由外部多模态 agent 处理并转换为结构化证据；SmartMoney-Cub 只消费结构化证据 |
| 数据源适配 / 报告生成 / 评估工具 | 预留接入位 | 只读导出与 toy fixture；不接券商执行，不写账户 |

TradingAgents 用法（两种模式都需要你自己在本地安装配置）：

```bash
# report-only：先在 TradingAgents 生成报告，再导入
smcub tradingagents-ingest --report path/to/report.md --ticker 600519.SS --analysis-date 2026-07-06

# optional local bridge：需要显式传入选择加入的 flag
smcub tradingagents-run --ticker 600519.SS --analysis-date 2026-07-06 --allow-network --ack-external-llm
```

详见 [docs/integrations.md](docs/integrations.md) 和 [docs/tradingagents-adapter.md](docs/tradingagents-adapter.md)。

## 安全与局限

每个 manifest、decision、outcome、evaluation、registry、doctor 和 loop 输出都携带：

```text
READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE
```

设计原则：

- **Local-first** — 无服务器、无遥测、无上传；你的交易系统只在你本地进化
- **Read-only** — 不下单、不撤单、不修改账户、不自动化券商
- **Human-in-the-loop** — champion 规则永不自动变更

如实说明当前局限：

- 不内置 OCR 或图像解析。截图可由外部多模态 agent（如 Codex 或用户自选工具）处理并转换为结构化证据；SmartMoney-Cub 只消费结构化证据。
- 不提供任何券商连接——这是设计边界，不是缺失功能。
- 没有预测或选股能力。
- `evidence_pack.sha256` 是本地篡改检测，不是认证签名。
- `--sandbox` 只是选择输出目录（`tmp/sandbox`），不是操作系统级沙箱。
- 公开示例只使用 toy 离线数据。

详见 [docs/safety.md](docs/safety.md) 和 [docs/privacy.md](docs/privacy.md)。

## 文档

- [docs/harness-contract.md](docs/harness-contract.md) — 核心安全契约（技术文件名保留以兼容）
- [docs/architecture.md](docs/architecture.md) — 证据与复盘核心架构
- [docs/user-guide.md](docs/user-guide.md) — 用户指南
- [docs/agent-loop.md](docs/agent-loop.md) / [docs/agent-integration.md](docs/agent-integration.md) — coding agent 协作
- [docs/decision-schema.md](docs/decision-schema.md) — 决策记录 schema
- [docs/evolution-loop.md](docs/evolution-loop.md) / [docs/memory-loop.md](docs/memory-loop.md) — 规则与记忆闭环
- [docs/integrations.md](docs/integrations.md) — 集成策略
- [docs/public-vs-private-quantkb.md](docs/public-vs-private-quantkb.md) — 公开/私有边界

## Roadmap

- 更丰富的结构化证据导入格式（承接外部多模态 agent 的输出）
- 更好的本地复盘报告渲染
- challenger 规则试炼的更多评估指标
- 更多 documented adapter（只读、仅证据）

Roadmap 永远不会包含下单执行、券商自动化或 champion 自动变更。

## 参与贡献

1. 阅读 [AGENTS.md](AGENTS.md) 和 [docs/harness-contract.md](docs/harness-contract.md)。
2. 在所有输出面保留安全声明。
3. 所有示例和测试只用 toy 离线数据。

```bash
pip install -e ".[dev]"
pytest -q
python -m smartmoney_cub.cli doctor
```

## License

MIT，见 [LICENSE](LICENSE)。
