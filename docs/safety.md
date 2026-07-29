# Safety

`smartmoney-cub` is a review and rule-evolution tool. It does not provide securities investment advice and does not connect to real trading execution.

## Hard Boundary

```text
READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE
```

This declaration is required on core artifacts and in doctor output.

## Redaction

The package redacts:

- credential-like fields;
- session and authorization fields;
- account-like fields;
- emails;
- phone numbers;
- local absolute paths.

Redaction happens before command metadata and CLI output are written.

## Data Policy

Do not commit:

- real trades;
- real watchlists;
- real account identifiers;
- private local paths;
- credentials;
- cookies;
- private notes.

Examples must remain toy-only and offline.

The TradingAgents adapter is optional and user-configured. External LLM/API credentials remain outside this repository and must never be committed or captured in artifacts.

