# Agent Runbook

## When the user says

* loop
* 自进化
* 复盘一下
* run harness
* review this decision
* rule evolution

## Do this

1. Read AGENTS.md
2. Read docs/harness-contract.md
3. Run `smcub doctor`
4. Run `smcub loop --preset toy --agent-trigger "<user phrase>"`
5. Open generated `demo_report.md` or `loop_report.md`
6. Open generated `trace.jsonl`
7. Summarize:

   * what happened
   * what failed
   * what rule update was proposed
   * whether safety was preserved
8. If code changes are needed, modify code and tests
9. Run `pytest -q`
10. Never mutate champion rules without explicit human confirmation

## Forbidden

* Do not place orders
* Do not cancel orders
* Do not connect to broker
* Do not scrape private account data
* Do not add financial advice wording
* Do not promote challenger to champion automatically
* Do not use future data in decision-time artifacts
* Do not leak absolute local paths
