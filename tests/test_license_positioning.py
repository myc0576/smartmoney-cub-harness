from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_license_metadata_migrated_to_apache_with_historical_mit_note():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    zh_readme = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "license-MIT" not in readme
    assert "License: MIT" not in readme
    assert "license-MIT" not in zh_readme
    assert "License: MIT" not in zh_readme
    assert 'license = { text = "Apache-2.0" }' in pyproject
    assert "License :: OSI Approved :: Apache Software License" in pyproject
    assert "License :: OSI Approved :: MIT License" not in pyproject
    assert "From version 0.2.0 onward, this project is licensed under Apache License 2.0." in readme
    assert "Earlier versions were released under MIT License" in readme
    assert "From version 0.2.0 onward, this project is licensed under Apache License 2.0." in zh_readme
    assert "Earlier versions were released under MIT License" in zh_readme


def test_tradingagents_positioning_is_audit_not_bundled_execution():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    zh_readme = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    integration_doc = (REPO_ROOT / "docs" / "integrations" / "tradingagents.md").read_text(encoding="utf-8")

    assert "TradingAgents makes trading decisions. SmartMoney Cub audits trading decisions." in readme
    assert "TradingAgents 产生交易研究观点，SmartMoney Cub 负责审计、复盘和进化这些观点。" in zh_readme
    assert "optional upstream research provider" in integration_doc
    assert "No TradingAgents core code is copied into this repository." in integration_doc
    assert "Do not claim that TradingAgents is bundled or officially integrated" in integration_doc
    assert "No broker execution is introduced." in integration_doc
    assert "No order routing is introduced." in integration_doc


def test_external_review_brain_positioning_does_not_require_embedded_llm_api():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    zh_readme = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    agent_doc = (REPO_ROOT / "docs" / "agent-integration.md").read_text(encoding="utf-8")
    brain_doc = (REPO_ROOT / "docs" / "external-review-brain.md").read_text(encoding="utf-8")

    assert "no--llm--api-required" in readme
    assert "agent--agnostic" in readme
    assert "external--review--brain" in readme
    assert "A no-LLM-API, local-first review brain for external agents" in readme
    assert "无需内置 LLM API 的只读交易复盘大脑" in zh_readme
    assert "does not embed or" in agent_doc
    assert "OpenAI API key" in agent_doc
    assert "does not embed or require" in brain_doc
    assert "OpenAI API key" in brain_doc
    assert "External Agent -> read contract -> run smcub CLI" in readme
    assert "External Agent -> read contract -> run smcub CLI" in zh_readme
