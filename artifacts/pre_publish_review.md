# Pre-Publish Review

Generated: 2026-06-25

## Scope

Reviewed the public offline core of `smartmoney-cub-harness` for open-source safety, README launch quality, runnable examples, and GitHub publish readiness.

## Test Results

```text
python -m pip install -e .                       PASS
python -m pip install -e ".[dev]"                PASS
pytest -q                                       PASS: 22 passed
python -m smartmoney_cub_harness.cli doctor     PASS
python -m smartmoney_cub_harness.cli --help     PASS
README toy capture/build/evaluate workflow      PASS: useful_alert
```

Doctor confirmed:

```text
status: ok
network_required: false
execution_integrations: disabled
safety: READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE
```

## Leak Scan Results

Requested keyword scan covered credentials, cookies, private accounts, real trading records, private watchlists, local path patterns, runtime folders, and private-memory markers.

Findings:

- No unredacted local absolute path findings in publishable text files.
- No credential, token, password, cookie, private watchlist, real trading record, QMT, or xtquant finding outside safety policy/redaction contexts.
- Sensitive-keyword hits are limited to safety rules, forbidden-data documentation, and redaction implementation.
- Generated `__pycache__`, pytest cache, egg-info, and sandbox run artifacts were removed after verification.

Promotional-language scan:

- No hits for the forbidden promotional terms, including precise buy/sell points, guaranteed profit language, limit-up promises, insider claims, VIP recommendation phrasing, or paid stock-pick hints.

## README Change Summary

Updated `README.md` and `README.zh-CN.md` into GitHub landing-page style project introductions:

- Added Python, license, tests, read-only, no-financial-advice, human-in-the-loop, and agent-ready badges.
- Put the required safety disclaimer in the upper section and again at the bottom.
- Preserved the "聪明资金幼年体 / 游资幼年体" concept and "陪你复盘，不替你下单" personality.
- Reframed the project as a read-only AI trading companion and training harness, not a recommendation product.
- Added What it is / What it is not sections.
- Added the Plan -> Observe -> Decide -> Record -> Validate Sources -> Outcome D1/D3 -> Evaluate -> Evolve Rules -> Update Memory Mermaid loop.
- Added Human x Agent Co-Evolution with the required edge quote.
- Added the 易经 / 钱学森系统工程 philosophy section without mystic prediction claims.
- Added runnable toy-data quick start and toy decision/evaluation output.
- Added GitHub description and topic recommendations.

## Open-Source Decision

Can open source: YES, based on the current publishable files after cleanup.

Rationale:

- Safety declaration remains present in core schemas, examples, docs, README output snippets, and doctor output.
- Examples use toy offline symbols and toy JSON fixtures only.
- No live trading execution, broker automation, order placement, order cancellation, or account modification was added.
- LICENSE exists.
- `.gitignore` excludes generated caches, runtime output, private state folders, exports, snapshots, watchlists, and env/secrets files.

## Push Decision

Can push from this environment: YES.

GitHub repository:

```text
https://github.com/myc0576/smartmoney-cub-harness
```

Publish result:

- Local release commit was prepared on `main`.
- The public GitHub repository was created through GitHub REST API.
- Remote `main` was published through GitHub Git Data API after seeding the empty repository with GitHub Contents API.
- Native git smart HTTP push was not used because the local global git proxy pointed at an unavailable `127.0.0.1` proxy and direct git HTTPS was reset.

Credential and transport note:

- Authentication used an ephemeral shell variable for GitHub REST/Git Data API calls.
- The Git remote URL does not contain the token.
- The token value was not written to repository files.
- Local git smart HTTP could not push because the global git proxy pointed at an unavailable local proxy; the repository was published through GitHub's Git Data API instead.
