from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache

from smartmoney_cub_harness.schemas import SAFETY_DECLARATION


@dataclass(frozen=True)
class AgentIntent:
    intent_name: str
    loop_stage: str
    full_loop: bool
    safety_mode: str
    requires_confirmation: bool
    description: str
    champion_mutation: bool = False

    def to_dict(self) -> dict[str, str | bool]:
        return asdict(self)


def _intent(
    intent_name: str,
    loop_stage: str,
    *,
    full_loop: bool,
    requires_confirmation: bool = False,
    description: str,
) -> AgentIntent:
    return AgentIntent(
        intent_name=intent_name,
        loop_stage=loop_stage,
        full_loop=full_loop,
        safety_mode=SAFETY_DECLARATION,
        requires_confirmation=requires_confirmation,
        description=description,
        champion_mutation=False,
    )


FULL_LOOP_INTENT = _intent(
    "full_loop",
    "full_loop",
    full_loop=True,
    description="Run the offline read-only review loop and propose challenger rules only.",
)

POSITION_CHECK_INTENT = _intent(
    "position_check",
    "position_check",
    full_loop=False,
    description="Run read-only position check logic without account, broker, or order access.",
)

CANDIDATE_GENERATION_INTENT = _intent(
    "candidate_generation",
    "candidate",
    full_loop=False,
    description="Generate or load an offline toy candidate under the read-only safety contract.",
)

RULE_EVOLUTION_INTENT = _intent(
    "rule_evolution",
    "review+challenger_rule_update",
    full_loop=False,
    description="Review evidence and propose a challenger rule; champion promotion still needs explicit human confirmation.",
)


TRIGGER_MAP: tuple[tuple[str, AgentIntent], ...] = (
    ("rule evolution", RULE_EVOLUTION_INTENT),
    ("position check", POSITION_CHECK_INTENT),
    ("candidate generation", CANDIDATE_GENERATION_INTENT),
    ("run harness", FULL_LOOP_INTENT),
    ("run loop", FULL_LOOP_INTENT),
    ("self-evolve", FULL_LOOP_INTENT),
    ("review", FULL_LOOP_INTENT),
    ("replay", FULL_LOOP_INTENT),
    ("loop", FULL_LOOP_INTENT),
    ("规则进化", RULE_EVOLUTION_INTENT),
    ("持仓检查", POSITION_CHECK_INTENT),
    ("候选生成", CANDIDATE_GENERATION_INTENT),
    ("自进化", FULL_LOOP_INTENT),
    ("复盘一下", FULL_LOOP_INTENT),
    ("跑一轮", FULL_LOOP_INTENT),
    ("跑闭环", FULL_LOOP_INTENT),
    ("交易复盘", FULL_LOOP_INTENT),
)


def _has_non_ascii(value: str) -> bool:
    return any(ord(char) > 127 for char in value)


@lru_cache(maxsize=64)
def _mojibake_variants(value: str) -> tuple[str, ...]:
    variants: set[str] = set()
    if not _has_non_ascii(value):
        return ()
    for encoding in ("gb18030", "gbk", "cp936", "latin1"):
        try:
            variant = value.encode("utf-8").decode(encoding, errors="replace")
        except LookupError:
            continue
        variants.add(variant)
        variants.add(variant.replace("\ufffd", "?"))
    variants.discard(value)
    variants.discard("")
    return tuple(sorted(variants, key=len, reverse=True))


def normalize_agent_trigger_text(text: str) -> str:
    normalized = str(text or "")
    for trigger, _intent_value in TRIGGER_MAP:
        for variant in _mojibake_variants(trigger):
            if variant in normalized:
                normalized = normalized.replace(variant, trigger)
    return normalized


def resolve_agent_trigger(text: str) -> AgentIntent:
    normalized = normalize_agent_trigger_text(text).strip().lower()
    if not normalized:
        return FULL_LOOP_INTENT

    for trigger, intent in TRIGGER_MAP:
        if trigger in normalized:
            return intent
    return FULL_LOOP_INTENT
