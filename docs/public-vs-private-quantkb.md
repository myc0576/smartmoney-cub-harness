# Public vs Private QuantKB Boundary

This repository may borrow only public, abstract workflow capabilities. It must not copy private trading data, private stock-picking logic, private prompts, or private workspace content.

## Public Repo Can Include

- schema
- loop runtime
- toy examples
- redaction
- case bank
- local Markdown memory
- evolution ledger
- challenger/champion governance
- agent runbook

## Public Repo Must Not Include

- real trades
- real watchlists
- account data
- private QMT paths
- private strategy prompts
- key stock-picking logic
- secret scoring weights
- credentials
- cookies
- local BaiduSyncdisk / QuantKB paths

## Practical Rule

If an artifact teaches the shape of the workflow, it can be public. If it reveals private market logic, private data, private paths, account context, or credentials, it stays out of the public repo.

The public demo must remain toy-only and offline.
