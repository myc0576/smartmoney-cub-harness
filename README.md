# smartmoney-cub-harness

<div align="center">

![smartmoney-cub-harness cover](assets/smartmoney-cub-harness-cover.png)

## 游资复盘引擎 · 让每一次决策都变成系统的进化

*"散户靠感觉，高手靠系统。把你的感觉，变成可复盘、可验证、可进化的规则。"*

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-pytest-informational)](tests/)
[![Read-only](https://img.shields.io/badge/mode-read--only-brightgreen)](docs/safety.md)
[![Local-first](https://img.shields.io/badge/local--first-no%20telemetry-success)](docs/privacy.md)
[![No LLM API Required](https://img.shields.io/badge/no--llm--api-required-success)](docs/external-review-brain.md)
[![Agent Agnostic](https://img.shields.io/badge/agent--agnostic-Codex%20%7C%20Claude%20%7C%20Cursor%20%7C%20Gemini-blue)](docs/agent-integration.md)
[![External Review Brain](https://img.shields.io/badge/external--review--brain-local--first-blueviolet)](docs/external-review-brain.md)
[![No Broker](https://img.shields.io/badge/no--broker-no%20execution-critical)](docs/safety.md)
[![Agent-ready](https://img.shields.io/badge/agent--ready-loop%20artifacts-blueviolet)](docs/agent-loop.md)
[![UZI-Skill](https://img.shields.io/badge/ecosystem-UZI--Skill-orange)](docs/integrations.md)

A no-LLM-API, local-first review brain for external agents: let Codex, Claude Code, Cursor, Gemini, and other agents turn trading theses into auditable review artifacts and human-gated rule evolution.

TradingAgents makes trading decisions. SmartMoney Cub audits trading decisions.

[30 秒上手](#30-秒上手) · [5 秒体验闭环](#5-秒体验复盘闭环) · [External Review Brain](#not-a-trading-agent--an-external-review-brain-for-agents) · [核心理念](#核心理念系统--感觉) · [AI 助手接入](#给-ai-助手只读复盘协作) · [Agent Interaction](#agent-interaction-model) · [Compared with TradingAgents](#compared-with-tradingagents) · [开源生态矩阵](#优秀开源项目集成矩阵) · [安全边界](#安全边界你的系统只属于你) · [CLI](#cli-commands)

`READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE`

</div>

---

`smartmoney-cub-harness` is not another trading agent framework with an embedded LLM provider. It is a local-first, read-only, agent-agnostic external review brain.

The harness itself does not embed or require OpenAI, Anthropic, Gemini, or any other LLM API key. External agents such as Codex, Claude Code, Cursor, Gemini CLI, OpenCode, and OpenClaw bring their own reasoning environment, read the local contract files, run `smcub`, and turn trading theses, research notes, review text, or external reports into auditable local artifacts.

It is not financial advice, not an auto-trading system, not a broker connector, and not a stock picker. It is a disciplined artifact layer for decision logging, D1/D3 outcome review, local Markdown memory, and challenger -> champion rule governance.

Your agent thinks and writes. SmartMoney Cub leaves an audit trail, checks provenance, reviews delayed outcomes, and keeps rule evolution human-gated.

## 30 秒上手

任何 agent 里丢一句话，让它按本仓库的安全合同跑 toy 离线闭环。公开仓库只使用 toy offline data。

| 你用的 agent | 直接丢这句 |
| --- | --- |
| Claude Code | `阅读 AGENTS.md 和 docs/harness-contract.md，运行 smcub loop --preset toy --agent-trigger "自进化"，只做只读复盘，不连接券商，不下单。` |
| Codex / OpenAI CLI | `在这个仓库里按 README 跑 smartmoney-cub-harness toy loop：smcub loop --preset toy --agent-trigger "自进化"，然后阅读 loop_report.md 和 trace.jsonl。` |
| Cursor | `请按 docs/agent-loop.md 使用本项目，跑 toy loop 并总结复盘产物；所有规则更新只能保持 challenger 状态。` |
| Gemini CLI | `请阅读 docs/harness-contract.md，执行 toy offline loop，确认输出包含 READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE。` |
| OpenCode / OpenClaw | `帮我用这个仓库做一次只读复盘演示：运行 smcub doctor，再运行 smcub loop --preset toy --agent-trigger "自进化"。` |
| CLI 直用 | `git clone https://github.com/myc0576/smartmoney-cub-harness.git && cd smartmoney-cub-harness && pip install -e ".[dev]" && smcub loop --preset toy --agent-trigger "自进化"` |

装好后最常用的安全命令：

```bash
smcub doctor
smcub privacy-audit
smcub loop --preset toy --agent-trigger "自进化"
smcub inspect-artifacts <run_dir>
```

本地私有 CSV 复盘可以使用自进化流程，但 champion 规则变更仍然必须人工确认：

```bash
smcub self-evolve --input-csv path/to/private_cases.csv --max-iterations 20 --time-budget-min 10 --horizon d1
smcub confirm-promotion state/self_evolve/<loop_id>/promotion_packet.json --decision promote --note "manual approval"
```

## 5 秒体验复盘闭环

真正有价值的复盘，不是看一眼盈亏就完事，而是把每一次判断拆成：计划是什么、证据是什么、结果是什么、下次怎么改。

一条命令跑完整个 toy 闭环：

```bash
git clone https://github.com/myc0576/smartmoney-cub-harness.git
cd smartmoney-cub-harness
pip install -e ".[dev]"
smcub loop --preset toy --agent-trigger "自进化"
```

运行后会在本地生成：

- `loop_report.md`
- `trace.jsonl`
- `case_record.json`
- `memory.md`
- `evolution_ledger.jsonl`

输出摘要会保持这个形状：

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

## Not a Trading Agent — An External Review Brain for Agents

TradingAgents is closer to a forward research desk: it can organize analysts, researchers, traders, and risk roles to generate market views or simulated trading decisions. SmartMoney Cub is the post-processing and governance layer after those views exist.

External agents do the thinking and writing. They can draft a thesis, summarize a report, challenge assumptions, or import a TradingAgents report. SmartMoney Cub records the thesis, checks evidence, tracks D1/D3 outcomes, writes local memory, and proposes challenger rules. It never places orders, cancels orders, connects to broker execution, uploads private strategy, or mutates champion rules automatically.

That makes it a good external brain for Codex, Claude Code, Cursor, Gemini CLI, OpenCode, and similar tools: the agent does not need this project to call a model API. It only needs to read local files such as `AGENTS.md`, `CLAUDE.md`, and `docs/harness-contract.md`, then run the `smcub` CLI.

### SmartMoney Cub as an External Review Brain

```mermaid
flowchart LR
    subgraph A["External Agents"]
        codex["Codex / OpenAI CLI"]
        claude["Claude Code"]
        cursor["Cursor"]
        gemini["Gemini CLI"]
        report["TradingAgents report"]
    end

    subgraph H["SmartMoney Cub Harness"]
        manifest["Manifest"]
        capture["Run Capture"]
        outcome["Outcome D1/D3"]
        eval["Evaluator"]
        memory["Memory"]
        registry["Rule Registry"]
    end

    subgraph R["Human Trader / Review Loop"]
        review["Review artifacts"]
        approve["Approve or reject rule promotion"]
    end

    codex --> manifest
    claude --> capture
    cursor --> manifest
    gemini --> capture
    report --> manifest
    manifest --> capture --> outcome --> eval --> memory --> registry --> review --> approve

    boundary["NO ORDER / NO CANCEL / NO BROKER / NO FINANCIAL ADVICE"]
    boundary -. safety boundary .- H
```

## 核心理念：系统 > 感觉

单次判断会忘，系统会进化。

`smartmoney-cub-harness` 把一次复盘拆成一条可审计链路：

```text
Plan -> Observe -> Record -> Outcome -> Evaluate -> Memory -> Rule Candidate
```

这条链路对应的是：

| 环节 | 作用 |
| --- | --- |
| Plan | 写清楚当时的计划、假设和风险条件 |
| Observe | 记录只读观察，不把观察变成买卖指令 |
| Record | 生成 manifest、decision、trace 等可审计产物 |
| Outcome | 等 D1/D3 结果出现后再评价，不偷看未来 |
| Evaluate | 检查决策质量、数据质量和安全合同 |
| Memory | 把复盘变成本地 Markdown 记忆 |
| Rule Candidate | 只提出 challenger 规则候选，不自动改 champion |

每一次错误都应该被拆解，每一条规则都应该被验证或淘汰。这个项目做的不是预测，而是帮你把主观判断训练成可复盘的系统。

## 给普通用户

你不需要券商 API，不需要量化背景，也不需要把私有资料放进公开仓库。你可以在本地整理这些只读输入：

- 交易计划文本。
- 交易日志 CSV。
- 同花顺或券商截图。
- 只读导出文件。
- 手写复盘笔记。
- toy offline 示例，用来先学习流程。

Harness 帮你结构化这些问题：

- 当时的 thesis 是什么？
- invalidation、time stop、give-up conditions 是否写清楚？
- 数据源、available time、data quality 是否可靠？
- D1/D3 之后结果如何？
- 这次失败是执行问题、证据问题，还是规则问题？
- 有没有值得进入 challenger 状态的规则候选？

## 给 AI 助手：只读复盘协作

AI 助手在这个仓库里只能扮演 reviewer、challenger、archivist、drift detector 或 systems assistant。它们帮助你复盘，不替你承担交易动作。

| 角色 | 可以做什么 | 不能做什么 |
| --- | --- | --- |
| Reviewer | 总结计划、证据、延迟结果和复盘评分 | 把复盘结论改写成买卖指令 |
| Challenger | 生成反方证据问题和缺失风险清单 | 只挑支持原判断的证据 |
| Archivist | 把本地产物整理成可携带 Markdown 记忆 | 把真实账户、截图或私有路径提交到公开仓库 |
| Drift Detector | 对比当前行为和历史规则 | 绕过指标与人工确认提升 champion |
| Systems Assistant | 拆解目标、风险、心理和结果 | 覆盖人的最终判断或执行交易 |

安全 agent workflow：

1. 读 `AGENTS.md` 和 [docs/harness-contract.md](docs/harness-contract.md)。
2. 运行 `smcub doctor`。
3. 运行 `smcub loop --preset toy --agent-trigger "自进化"`。
4. 打开 `loop_report.md` 和 `trace.jsonl`。
5. 提出复盘、安全、redaction、schema 或 workflow 改进。
6. 规则更新保持 challenger 状态。
7. champion 变更只通过显式人工确认路径发生。

详见 [docs/agent-loop.md](docs/agent-loop.md) 和 [docs/agent-integration.md](docs/agent-integration.md)。

## Agent Interaction Model

![SmartMoney Cub Agent Interaction](assets/smartmoney-agent-interaction.png)

```text
External Agent -> read contract -> run smcub CLI -> inspect artifacts -> write review/challenger notes -> human approves rule promotion
```

Recommended interaction surfaces:

- Codex / OpenAI CLI reads `AGENTS.md` and `docs/harness-contract.md`, then runs `smcub` commands.
- Claude Code follows `CLAUDE.md` and the harness contract before writing review notes.
- Cursor can inspect local artifacts and propose challenger rules without touching execution.
- Gemini CLI can run toy or local review flows and verify the safety declaration.
- OpenCode / OpenClaw can operate as reviewer, challenger, archivist, or drift detector.
- TradingAgents reports can enter only as optional upstream artifacts through `ingest-external-report`.

Rules for agents:

- Agents may analyze, but they must not execute trades.
- Agents may propose challenger rules, but they must not promote champion rules automatically.
- Agents may import external reports, but every import must pass provenance, anti-future-leakage, and redaction checks.
- This harness itself does not embed or require an LLM API provider or API key.

## Compared with TradingAgents

TradingAgents is a strong multi-agent financial research and forward decision framework. SmartMoney Cub is intentionally different: TradingAgents makes trading decisions. SmartMoney Cub audits trading decisions.

| Dimension | TradingAgents | SmartMoney Cub |
| --- | --- | --- |
| System role | Forward trading research team | Read-only review and rule-governance brain |
| LLM dependency | Usually expects model/API participation in agent reasoning | Harness itself does not embed or require an LLM API key; external agents bring their own reasoning |
| Output | Research views, trading suggestions, decision simulations | Manifest, decision record, D1/D3 outcome, evaluation, memory, rule candidate |
| Execution boundary | May model around trading decisions | Never places orders, cancels orders, or connects to broker execution |
| Privacy | Depends on the upstream system | Local-first, no telemetry, public repo uses toy examples only |
| Rule evolution | Reasoning inside the research workflow | challenger -> champion; champion mutation requires explicit human confirmation |

Optional TradingAgents report ingestion is documented in [docs/integrations/tradingagents.md](docs/integrations/tradingagents.md). It is compatibility documentation and a minimal read-only adapter, not a claim that TradingAgents is bundled, copied, or officially integrated.

## 优秀开源项目集成矩阵

这个 harness 会持续预留优秀开源项目的接入位。集成的目标不是制造更激进的交易信号，而是把外部工具的输出纳入只读复盘、证据整理和规则治理。

| 项目 / 类别 | 当前状态 | 可以怎样接入 harness | 安全边界 |
| --- | --- | --- | --- |
| [TradingAgents](docs/integrations/tradingagents.md) | documented-adapter | Optional upstream research provider; Markdown reports may be imported as `external_analysis_artifact` review evidence. | No runtime dependency by default; no copied core code; no broker execution, order routing, or automatic champion mutation. |
| [wbh604/UZI-Skill](https://github.com/wbh604/UZI-Skill) | 推荐搭配 / 生态接入位 | 作为外部分析报告或 agent skill 灵感来源，输出只能作为本地复盘材料进入 reviewer / challenger 流程 | 不声明内置运行时集成；不把分析结论变成买卖指令 |
| 数据源适配项目 | 预留 | 只读导出、toy fixture、公开样例 schema | 不接 broker execution，不写账户，不下单 |
| 报告生成项目 | 预留 | 把 `loop_report.md`、case record、ledger 转成更好的本地阅读材料 | 不上传私有复盘，不发布真实持仓 |
| Agent skill 项目 | 预留 | 增强 reviewer、challenger、archivist、drift detector 的协作体验 | 不允许越权到交易执行 |
| 评估 / 回测项目 | 预留 | 帮助评估规则候选和样本质量 | 不跳过 D1/D3 provenance 与 future-leakage 检查 |
| 知识记忆项目 | 预留 | 管理本地 Markdown memory、case bank、evolution ledger | 不上传私有交易逻辑 |

接入规则见 [docs/integrations.md](docs/integrations.md)。

## 安全边界：你的系统，只属于你

交易逻辑和复盘记忆是私有资产。`smartmoney-cub-harness` 的设计原则是：你的交易系统只在你本地进化。

每个 manifest、decision、outcome、evaluation、registry、doctor output 和 loop output 都必须携带：

```text
READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE
```

项目默认：

- Not financial advice.
- Not an auto-trading system.
- Not a broker connector.
- No order placement.
- No order cancellation.
- No private strategy upload.
- Local-first and read-only by default.
- Local-first。
- Offline by default。
- No telemetry。
- No upload。
- No trading execution。
- No broker automation。
- CLI 输出前先 redaction。
- 公开仓库只使用 toy examples。

它明确不做：

- 不下单。
- 不撤单。
- 不修改账户。
- 不自动化券商。
- 不连接真实交易执行。
- 发布真实交易记录、真实 watchlist、账户数据、私有策略 prompt、私有路径、credentials 或 cookies。

运行：

```bash
smcub privacy-audit
smcub doctor
```

## Privacy

This project does not collect, upload, sell, or learn your trading logic. By default it has no server, no telemetry, no remote database, and no real account connection.

Your private trading logic should remain in local artifacts on your machine. It must not be copied into the public repository. Public examples must stay toy-only.

See [docs/privacy.md](docs/privacy.md) and [docs/public-vs-private-quantkb.md](docs/public-vs-private-quantkb.md).

## CLI Commands

```bash
smcub loop --preset toy --agent-trigger "自进化"
smcub privacy-audit
smcub self-evolve --input-csv path/to/private_cases.csv --max-iterations 20 --time-budget-min 10 --horizon d1
smcub confirm-promotion state/self_evolve/<loop_id>/promotion_packet.json --decision promote --note "manual approval"
smcub inspect-artifacts <run_dir>
smcub collect-case <run_dir>
smcub append-ledger --event EVENT --payload-json FILE
smcub save-memory --case-record FILE
smcub ingest-external-report --source tradingagents --input path/to/report.md --decision-time 2026-07-05T09:30:00+08:00 --output artifacts/external/
smcub doctor
smcub validate-manifest examples/sample_run/run_manifest.json
```

## Development Checks

```bash
pip install -e ".[dev]"
pytest -q
python -m smartmoney_cub_harness.cli doctor
python -m smartmoney_cub_harness.cli --help
```

## Public Boundary

The public repo can include schemas, loop runtime, toy examples, redaction, case bank, local Markdown memory format, evolution ledger, challenger/champion governance, integration guidance, and agent runbooks.

The public repo must not include real trades, real watchlists, account data, private QMT paths, private strategy prompts, key stock-picking logic, secret scoring weights, credentials, cookies, or local private workspace paths.

`READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE` remains the public boundary and runtime safety declaration.

## License

From version 0.2.0 onward, this project is licensed under Apache License 2.0.
Earlier versions were released under MIT License and remain available under the
license terms that applied at the time of release.

See [LICENSE](LICENSE), [NOTICE](NOTICE), and [TRADEMARK.md](TRADEMARK.md).
