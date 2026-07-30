# TradingAgents Optional Adapter

This document describes the optional TradingAgents adapter boundary for SmartMoney-Cub.

```text
READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE
```

## What This Is

TradingAgents can be used as a user-selected external LLM multi-agent financial analysis engine. Its reports may be wrapped into local review packets so SmartMoney-Cub can preserve provenance, risk notes, reviewer questions, challenger questions, and later D1/D3 review context.

The adapter is local-first and optional. It does not make TradingAgents a default runtime dependency.

## What This Is Not

This adapter is not a stock picker, broker connector, account tool, or financial advice system. It does not place orders, cancel orders, modify accounts, or promote champion rules automatically.

TradingAgents output remains evidence for review. It is not a trading instruction.

## Safety Contract

- SmartMoney-Cub remains `READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE`.
- Default toy loops do not need TradingAgents.
- Default toy loops do not need any LLM/API key.
- Public examples stay toy-only.
- No telemetry is added.
- No broker execution is added.
- No credential capture is added.
- TradingAgents output enters reviewer / challenger / evidence / case-review workflows only.
- Champion promotion still requires explicit human confirmation.

## Setup Model

TradingAgents must be installed and configured by the user in the user's own local environment. SmartMoney-Cub does not ship, store, proxy, or collect TradingAgents credentials.

LLM/API keys stay outside this repository. Configure them according to TradingAgents' own documentation and your local security policy. The SmartMoney-Cub doctor surfaces only booleans/provider presence, never key values.

## Two Modes

### Report-Only Import Mode

Use this when you run TradingAgents independently and already have a local Markdown, text, or JSON report.

```bash
smcub tradingagents-ingest \
  --report path/to/tradingagents_report.md \
  --ticker 600519.SS \
  --analysis-date 2026-07-06 \
  --output artifacts/tradingagents_review_packet.json
```

This mode is offline from SmartMoney-Cub's perspective. It reads a local report and writes a redacted review packet.

### Optional Local Bridge Mode

Use this only after you have installed TradingAgents locally and configured any LLM provider keys outside this repository.

```bash
smcub tradingagents-doctor
smcub tradingagents-run \
  --ticker 000001.SZ \
  --analysis-date 2026-07-06 \
  --output artifacts/tradingagents_review_packet.json \
  --allow-network \
  --ack-external-llm
```

`--allow-network` and `--ack-external-llm` are deliberate consent gates. Without both flags, the bridge refuses to run and returns a structured safety error.

## Example Workflow

1. The user runs TradingAgents locally or exports a TradingAgents report.
2. The user imports the report with `smcub tradingagents-ingest`, or explicitly runs `smcub tradingagents-run`.
3. SmartMoney-Cub writes a local `smartmoney_cub_tradingagents_review_packet.v1` packet.
4. A reviewer agent inspects evidence, risk notes, missing provenance, and D1/D3 follow-up questions.
5. A challenger agent proposes counter-theses or rule-candidate questions.
6. A human decides whether any future rule candidate deserves promotion review.

The A-share tickers `600519.SS` and `000001.SZ` are command examples only. Do not commit real watchlists, real trading records, private reports, or account data to the public repository.

## Output Artifact Schema

The review packet has this shape:

```json
{
  "schema": "smartmoney_cub_tradingagents_review_packet.v1",
  "source": "tradingagents",
  "ticker": "600519.SS",
  "analysis_date": "2026-07-06",
  "mode": "report_only",
  "external_llm_required": false,
  "network_required": false,
  "credentials_captured": false,
  "broker_execution": false,
  "actionability": "review_only",
  "safety": "READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE",
  "evidence_summary": [],
  "risk_notes": [],
  "reviewer_questions": [],
  "challenger_questions": []
}
```

The packet may include a redacted `report_excerpt`, report filename, hash, provider name, and human-gate metadata.

## Failure Modes

- TradingAgents not installed: `tradingagents-run` returns `status=disabled` with `error.code=tradingagents_not_installed`.
- API key missing: TradingAgents may fail in the user's local environment; SmartMoney-Cub returns a redacted structured error.
- Network not explicitly allowed: `tradingagents-run` returns `error.code=network_not_allowed`.
- External LLM not acknowledged: `tradingagents-run` returns `error.code=external_llm_not_acknowledged`.
- Report missing: `tradingagents-ingest` returns `error.code=report_missing`.

None of these failures should create a traceback for normal CLI users.

## Privacy And Redaction

The adapter uses the core redaction layer before printing or writing packet JSON. Report excerpts are redacted for common credential-like values, cookies, account-like fields, emails, phone numbers, and local absolute paths.

Do not put `.env`, private prompts, real reports, real positions, real fills, cookies, account identifiers, or API key material into git.

## Human Gate

TradingAgents output can support a reviewer or challenger. It cannot directly change champion rules.

Any rule evolution remains:

```text
challenger -> evaluated evidence -> explicit human confirmation -> champion
```

No adapter path may bypass this gate.

