# Open Source Check

Generated: 2026-06-24 22:45:46 +08:00

## git status

```text
?? .gitignore
?? AGENTS.md
?? CLAUDE.md
?? LICENSE
?? README.md
?? README.zh-CN.md
?? artifacts/
?? docs/
?? examples/
?? pyproject.toml
?? src/
?? tests/
```

## pytest -q

```text
......................                                                   [100%]
22 passed in 0.50s
```

## doctor

```text
{
  "status": "ok",
  "package": "smartmoney-cub-harness",
  "version": "0.1.0",
  "python": "3.12.8",
  "platform": "Windows-11-10.0.26200-SP0",
  "cwd": "[REDACTED]",
  "network_required": false,
  "execution_integrations": "disabled",
  "default_data_mode": "offline_json_fixtures",
  "safety": "READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE"
}
```

## cli help

```text
usage: smcub [-h]
             {validate-manifest,capture-run,build-outcome,evaluate-run,register-candidate,doctor}
             ...

Read-only trading companion harness for decision logging, outcome review, and
rule evolution.

positional arguments:
  {validate-manifest,capture-run,build-outcome,evaluate-run,register-candidate,doctor}
    validate-manifest   Validate a run manifest JSON file
    capture-run         Run offline commands and save replay artifacts
    build-outcome       Build D1/D3 outcome JSON for a run
    evaluate-run        Evaluate a run directory
    register-candidate  Register a rule candidate
    doctor              Show local package health and safety settings

options:
  -h, --help            show this help message and exit
```

## Leak Scan Summary

- Environment file pattern: no findings in publishable files.
- Local absolute path / private integration pattern: no findings in publishable files.
- Sensitive-keyword findings: limited to safety rules, documentation of forbidden data, and redaction implementation; reviewed as non-secret.
- Private trading/watchlist/profit-language findings: limited to documentation saying such data must not be committed, plus redaction tests; reviewed as non-private.

## Leak Scan Counts

```text
env_pattern_matches=0
path_or_private_integration_matches=0
sensitive_keyword_matches=17
private_trading_language_matches=17
```

Conclusion: no open-source blockers found.
