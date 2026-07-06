# TradingAgents Compatibility

TradingAgents is a strong multi-agent financial research framework. This
project documents optional interoperability with its report output while keeping
`smartmoney-cub-harness` at the review and audit layer.

SmartMoney Cub is not an embedded-LLM trading agent framework. It does not
require users to configure OpenAI, Anthropic, Gemini, or any other LLM API key.
TradingAgents can be treated as an optional upstream research artifact source;
the harness remains a local-first external review brain.

```text
READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE
```

## Purpose

- TradingAgents can be used as an optional upstream research provider.
- TradingAgents reports may be imported as `external_analysis_artifact`.
- The imported report is review evidence only.
- The imported report does not replace the user's selection process, strategy,
  or human judgment.

## Boundary

- No runtime dependency on TradingAgents is required by default.
- No TradingAgents core code is copied into this repository.
- No built-in LLM provider or TradingAgents runtime is required by this harness.
- No broker execution is introduced.
- No order routing is introduced.
- No automatic champion rule mutation is introduced.
- Do not claim that TradingAgents is bundled or officially integrated unless
  actual tested runtime integration exists.

## Mapping

TradingAgents report output is mapped into review fields:

- `bull_case`
- `bear_case`
- `risk_notes`
- `external_proposal`
- `confidence`
- `source_project`
- `source_license`
- `raw_report_path`

The `external_proposal` field may preserve buy, sell, hold, or position-sizing
language from the upstream report as an external research view. It must not be
converted into `order`, `broker`, `execution`, `auto_trade`, `cancel_order`, or
`position_execution` fields.

## License Note

- TradingAgents is Apache-2.0.
- This project may document optional interoperability.
- Do not copy TradingAgents source code into this repository.
- If future code is copied or vendored, preserve Apache-2.0 attribution, NOTICE,
  and modification notices.

## Example Workflow

```bash
smcub ingest-external-report --source tradingagents --input path/to/report.md --decision-time 2026-07-05T09:30:00+08:00 --output artifacts/external/
```

## Safety Invariant

Every import must preserve:

- `READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE=true`
- `network_required=false`
- `telemetry=false`
- `broker_execution=false`
- `champion_mutated=false`

If `available_at > decision_time`, the imported artifact must be marked with a
failed future-leakage check and the CLI must return a non-zero exit status.
