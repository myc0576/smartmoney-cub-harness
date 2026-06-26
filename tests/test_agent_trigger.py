from __future__ import annotations

from smartmoney_cub_harness.agent_trigger import normalize_agent_trigger_text, resolve_agent_trigger
from smartmoney_cub_harness.schemas import SAFETY_DECLARATION


def test_resolves_chinese_self_evolve_to_safe_full_loop():
    intent = resolve_agent_trigger("请自进化一下")

    assert intent.intent_name == "full_loop"
    assert intent.loop_stage == "full_loop"
    assert intent.full_loop is True
    assert intent.safety_mode == SAFETY_DECLARATION
    assert intent.requires_confirmation is False
    assert intent.champion_mutation is False


def test_resolves_english_loop_to_safe_full_loop():
    intent = resolve_agent_trigger("run loop")

    assert intent.intent_name == "full_loop"
    assert intent.loop_stage == "full_loop"
    assert intent.full_loop is True
    assert intent.champion_mutation is False


def test_resolves_position_check_stage_without_safety_bypass():
    intent = resolve_agent_trigger("持仓检查")

    assert intent.intent_name == "position_check"
    assert intent.loop_stage == "position_check"
    assert intent.full_loop is False
    assert intent.safety_mode == SAFETY_DECLARATION
    assert intent.champion_mutation is False


def test_resolves_rule_evolution_as_challenger_only():
    intent = resolve_agent_trigger("规则进化")

    assert intent.intent_name == "rule_evolution"
    assert intent.loop_stage == "review+challenger_rule_update"
    assert intent.champion_mutation is False
    assert "challenger" in intent.description.lower()


def test_normalizes_common_windows_mojibake_for_chinese_trigger():
    mojibake = "\u9477\ue047\u7e58\u9356?"

    intent = resolve_agent_trigger(mojibake)

    assert normalize_agent_trigger_text(mojibake) == "自进化"
    assert intent.intent_name == "full_loop"
