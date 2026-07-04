# Integrations

`smartmoney-cub-harness` can reference and learn from strong open-source projects, but every integration stays inside the read-only review contract.

The goal is not to create stronger execution signals. The goal is to turn external analysis, reports, skills, and data shapes into better local review artifacts.

```text
READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE
```

## Integration Contract

Every integration must preserve these rules:

- Inputs are read-only.
- Public examples use toy offline data only.
- External reports are evidence for review, not trading instructions.
- Agent outputs may create challenger rule candidates only.
- Champion mutation requires explicit human confirmation.
- No integration may place orders, cancel orders, modify accounts, automate brokers, or handle credentials.
- No integration may publish real trades, real watchlists, account data, private strategy prompts, or local private paths.

## Status Vocabulary

| Status | Meaning |
| --- | --- |
| `recommended-companion` | Useful alongside the harness, but not imported or executed by the harness runtime. |
| `reserved-slot` | A category intentionally left open for future open-source integrations. |
| `documented-adapter` | A documented local pattern exists, but it remains read-only and optional. |
| `runtime-integrated` | Code, tests, and docs prove the integration is part of the harness runtime. |

Do not label a project `runtime-integrated` until the repository contains the code path, tests, and safety documentation that prove it.

## Current Matrix

| Project / Category | Status | Harness Role | Required Boundary |
| --- | --- | --- | --- |
| [wbh604/UZI-Skill](https://github.com/wbh604/UZI-Skill) | `recommended-companion` | External analysis skill and narrative inspiration; outputs may be saved locally and reviewed by reviewer / challenger agents. | Do not call it an embedded dependency. Do not convert its analysis into buy/sell instructions. |
| Data-source adapters | `reserved-slot` | Normalize read-only exports, toy fixtures, or public examples into manifests. | No broker execution, no account mutation, no credential capture. |
| Report generators | `reserved-slot` | Render loop reports, case records, and ledgers for local reading. | No upload of private review artifacts. |
| Agent skills | `reserved-slot` | Improve reviewer, challenger, archivist, and drift-detector workflows. | No role may bypass the harness contract or promote champion rules automatically. |
| Evaluation / backtest tools | `reserved-slot` | Help evaluate challenger candidates and sample quality. | No future leakage and no execution recommendation surface. |
| Knowledge-memory tools | `reserved-slot` | Organize Markdown memory, case banks, and evolution ledgers. | No cloud sync requirement and no private trading logic publication. |

## UZI-Skill Positioning

UZI-Skill is a strong example of agent-facing financial analysis packaging and a useful companion project for users who already run it in their own agent environment.

In this harness, UZI-Skill should be described carefully:

- Good: "recommended companion", "ecosystem slot", "external analysis that can be reviewed locally".
- Good: "its output can become read-only evidence inside a review packet".
- Not allowed: "built-in integration", unless runtime code and tests are added.
- Not allowed: "use this analysis to trade", "auto-trade from UZI output", or any equivalent execution framing.

## Future Integration Checklist

Before adding any new project to the README matrix:

1. Identify the integration status.
2. State the read-only input or artifact it contributes.
3. State what the harness must never do with it.
4. Confirm public examples remain toy-only.
5. Confirm the safety declaration appears in any new manifest, decision, outcome, evaluation, registry, doctor, or loop output touched by the integration.
6. Add tests when the integration becomes runtime behavior.

## Human Gate

Integrations may improve review quality, evidence organization, and challenger suggestions. They must not turn the harness into an execution system.

Champion rule changes remain human-gated:

```bash
smcub confirm-promotion state/self_evolve/<loop_id>/promotion_packet.json --decision promote --note "manual approval"
```
