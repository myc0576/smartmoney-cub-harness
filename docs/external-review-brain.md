# External Review Brain

`smartmoney-cub-harness` is a local-first, read-only, agent-agnostic external
review brain. It is not another trading agent framework with an embedded LLM
provider.

The harness itself does not embed or require an OpenAI API key, Anthropic API
key, Gemini API key, or any other built-in LLM provider. External agents bring
their own reasoning environment, read the local contract files, and call the
`smcub` CLI.

```text
READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE
```

## Role Split

External agents think and write:

- Codex / OpenAI CLI
- Claude Code
- Cursor
- Gemini CLI
- OpenCode / OpenClaw
- TradingAgents reports imported as optional upstream artifacts

SmartMoney Cub records and governs:

- Manifest creation
- Decision records
- D1/D3 outcome review
- Evaluation artifacts
- Local Markdown memory
- Challenger rule candidates
- Human-gated champion promotion

## Interaction Model

```text
External Agent -> read contract -> run smcub CLI -> inspect artifacts -> write review/challenger notes -> human approves rule promotion
```

The contract files are intentionally plain text:

- `AGENTS.md`
- `CLAUDE.md`
- `docs/harness-contract.md`
- `docs/agent-integration.md`
- `docs/integrations/tradingagents.md`

## Boundaries

The harness must remain:

- Local-first.
- Read-only.
- No telemetry.
- No private strategy upload.
- No broker connector.
- No trading execution.
- No order placement.
- No order cancellation.
- No automatic champion mutation.
- Not financial advice.

External agents may analyze evidence, propose challenger rules, and import
external reports. They must not place trades, cancel orders, automate brokers,
or promote champion rules without explicit human confirmation.
