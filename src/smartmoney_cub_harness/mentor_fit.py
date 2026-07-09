from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from smartmoney_cub_harness.schemas import MENTOR_FIT_SCHEMA, SAFETY_DECLARATION

PUBLIC_CASE_SOURCE_TYPES = {"public_replay", "tgb_case", "video_note", "seat_review"}
ALLOWED_PUBLIC_TEMPLATE_USES = {"case_study", "skill_proposal", "counterexample", "ontology_update"}
FORBIDDEN_PUBLIC_TEMPLATE_USES = {
    "real_time_recommendation_evidence",
    "next_day_buy_trigger",
    "direct_portfolio_action",
}
POSITIVE_GRADES = {"useful_alert", "confirmed", "true_silent", "correct_no_trade"}
NEGATIVE_GRADES = {"false_alert", "missed_opportunity", "invalid", "not_fit", "avoided_copy_trade"}
EMERGENCE_MIN_CASES = 10
EMERGENCE_MIN_MARKET_PHASES = 2


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _listify(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_text(item) for item in value)
    return str(value or "")


def _text_variants(value: str) -> list[str]:
    variants = [value]
    for encoding in ("gbk", "cp936"):
        try:
            repaired = value.encode(encoding).decode("utf-8")
        except UnicodeError:
            continue
        if repaired and repaired not in variants:
            variants.append(repaired)
    return variants


def _closed_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    closed: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        status = str(case.get("status") or "")
        confirmation = str(case.get("confirmation_status") or "")
        payloads = case.get("source_payloads") or case.get("payloads") or {}
        has_outcome = isinstance(payloads, dict) and bool(payloads.get("outcome"))
        has_eval = isinstance(payloads, dict) and bool(payloads.get("evaluation"))
        if status in {"normalized", "derived", "closed"} and (confirmation in {"confirmed", ""}) and has_outcome and has_eval:
            closed.append(case)
    return closed


def _case_grade(case: dict[str, Any]) -> str:
    payloads = case.get("source_payloads") or case.get("payloads") or {}
    evaluation = payloads.get("evaluation") if isinstance(payloads, dict) else {}
    if isinstance(evaluation, dict):
        return str(evaluation.get("grade") or "").lower()
    return ""


def _case_ref(case: dict[str, Any]) -> str:
    return str(case.get("case_id") or case.get("id") or "unknown")


def _label(label: str, evidence_refs: list[str], evidence_count: int, total: int) -> dict[str, Any]:
    confidence = round(min(1.0, evidence_count / max(1, total)), 3)
    return {
        "label": label,
        "confidence": confidence,
        "evidence_count": evidence_count,
        "evidence_refs": evidence_refs[:8],
    }


def infer_user_style_labels(
    cases: list[dict[str, Any]],
    confirmed_memories: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Infer observable trading-behavior labels from closed toy cases and confirmed memories."""
    closed = _closed_cases(cases)
    memories = [
        item for item in (confirmed_memories or [])
        if isinstance(item, dict) and str(item.get("status") or "confirmed") == "confirmed"
    ]
    memory_text = " ".join(_text(item.get("text") or item.get("body_md") or item) for item in memories)
    labels: list[dict[str, Any]] = []
    counters: dict[str, tuple[int, list[str]]] = {}

    def mark(name: str, ref: str) -> None:
        count, refs = counters.get(name, (0, []))
        counters[name] = (count + 1, [*refs, ref])

    for case in closed:
        ref = _case_ref(case)
        payloads = case.get("source_payloads") or case.get("payloads") or {}
        combined = " ".join(_text_variants(" ".join([_text(case), _text(payloads), memory_text]))).lower()
        if any(token in combined for token in ("低吸", "low-buy", "low_buy", "low absorb")):
            mark("low_buy_preference", ref)
        if any(token in combined for token in ("不打板", "no_board", "no board", "不追板")):
            mark("no_board_chasing", ref)
        if any(token in combined for token in ("快反馈", "1-3", "d1", "d3", "fast feedback")):
            mark("fast_feedback_preference", ref)
        if any(token in combined for token in ("龙头", "辨识度", "recognition", "leader", "前排")):
            mark("high_recognition_only", ref)
        if any(token in combined for token in ("怕浮亏", "浮亏", "loss sensitive", "drawdown")):
            mark("loss_sensitive_execution", ref)

    for label_name in sorted(counters):
        count, refs = counters[label_name]
        labels.append(_label(label_name, refs, count, len(closed)))

    market_phases = sorted({str(case.get("market_phase") or "") for case in closed if case.get("market_phase")})
    positive = sum(1 for case in closed if _case_grade(case) in POSITIVE_GRADES)
    negative = sum(1 for case in closed if _case_grade(case) in NEGATIVE_GRADES)
    return {
        "schema": "smartmoney_cub_style_profile.v1",
        "closed_case_count": len(closed),
        "market_phases": market_phases,
        "positive_case_count": positive,
        "negative_case_count": negative,
        "style_labels": labels,
        "evidence_refs": [_case_ref(case) for case in closed[:12]],
        "confirmed_memory_count": len(memories),
        "safety": SAFETY_DECLARATION,
        "mutates_champion": False,
        "public_case_as_signal": False,
        "requires_user_confirmation": True,
    }


def _default_template_registry() -> list[dict[str, Any]]:
    return [
        {
            "template_id": "total_dragon_rebound",
            "display_name": "总龙反抽软锚定",
            "source_type": "public_replay",
            "allowed_use": ["case_study", "skill_proposal", "counterexample", "ontology_update"],
            "required_labels": ["low_buy_preference", "high_recognition_only", "fast_feedback_preference"],
            "why_fit": ["偏低吸", "重视高辨识度龙头", "需要买后快速反馈"],
            "forbidden_scenarios": ["退潮失控", "高位批量A杀", "无失效位", "把公开案例当实时跟买信号"],
        },
        {
            "template_id": "strong_theme_first_divergence",
            "display_name": "强主线首次分歧软锚定",
            "source_type": "public_replay",
            "allowed_use": ["case_study", "skill_proposal", "counterexample", "ontology_update"],
            "required_labels": ["low_buy_preference", "high_recognition_only"],
            "why_fit": ["适合主线核心分歧低吸", "要求地位和承接"],
            "forbidden_scenarios": ["题材退潮", "后排补涨", "没有快反馈路径"],
        },
        {
            "template_id": "capacity_trend_anchor",
            "display_name": "容量趋势卡位软锚定",
            "source_type": "public_replay",
            "allowed_use": ["case_study", "skill_proposal", "counterexample", "ontology_update"],
            "required_labels": ["low_buy_preference", "fast_feedback_preference"],
            "why_fit": ["适合容量核心分歧确认", "不要求打板"],
            "forbidden_scenarios": ["缩量轮动", "容量核心地位丧失", "趋势破位"],
        },
        {
            "template_id": "institutional_trend",
            "display_name": "机构趋势软锚定",
            "source_type": "public_replay",
            "allowed_use": ["case_study", "skill_proposal", "counterexample", "ontology_update"],
            "required_labels": ["no_board_chasing"],
            "why_fit": ["不打板", "偏研究和趋势确认"],
            "forbidden_scenarios": ["把机构买入当买点", "无流动性", "基本面兑现风险不明"],
        },
    ]


def _validate_public_template(template: dict[str, Any]) -> None:
    source_type = str(template.get("source_type") or "")
    allowed = {str(item) for item in _listify(template.get("allowed_use"))}
    forbidden = {str(item) for item in _listify(template.get("forbidden_use"))}
    errors: list[str] = []
    if source_type in PUBLIC_CASE_SOURCE_TYPES:
        if allowed - ALLOWED_PUBLIC_TEMPLATE_USES:
            errors.append("invalid_allowed_use")
        if forbidden & FORBIDDEN_PUBLIC_TEMPLATE_USES:
            errors.append("forbidden_use")
        if allowed & FORBIDDEN_PUBLIC_TEMPLATE_USES:
            errors.append("forbidden_allowed_use")
        if template.get("next_day_buy_trigger"):
            errors.append("next_day_buy_trigger")
        if template.get("recommendation_evidence"):
            errors.append("recommendation_evidence")
    if errors:
        raise ValueError(f"public_template_forbidden:{template.get('template_id', 'unknown')}:{','.join(errors)}")


def _emergence_gate(style_profile: dict[str, Any]) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    if int(style_profile.get("closed_case_count") or 0) < EMERGENCE_MIN_CASES:
        blockers.append("closed_case_count_below_10")
    if len(style_profile.get("market_phases") or []) < EMERGENCE_MIN_MARKET_PHASES:
        blockers.append("market_phase_coverage_below_2")
    if int(style_profile.get("positive_case_count") or 0) <= 0:
        blockers.append("missing_positive_cases")
    if int(style_profile.get("negative_case_count") or 0) <= 0:
        blockers.append("missing_negative_or_counterexample_cases")
    return not blockers, blockers


def match_template_anchors(
    style_profile: dict[str, Any],
    template_registry: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    templates = template_registry or _default_template_registry()
    for template in templates:
        _validate_public_template(template)

    gate_ok, blockers = _emergence_gate(style_profile)
    if not gate_ok:
        return {
            "schema": "smartmoney_cub_template_anchor.v1",
            "emergence_status": {
                "status": "insufficient_evidence",
                "blockers": blockers,
                "required": {
                    "closed_case_count": EMERGENCE_MIN_CASES,
                    "market_phase_count": EMERGENCE_MIN_MARKET_PHASES,
                    "positive_and_negative_cases": True,
                },
            },
            "template_matches": [],
            "safety": SAFETY_DECLARATION,
        }

    labels = {item["label"]: item for item in style_profile.get("style_labels", []) if isinstance(item, dict)}
    matches: list[dict[str, Any]] = []
    for template in templates:
        required = [str(item) for item in _listify(template.get("required_labels"))]
        if not required:
            continue
        hits = [label for label in required if label in labels]
        score = round(len(hits) / len(required), 3)
        if score <= 0:
            continue
        missing = [label for label in required if label not in labels]
        refs: list[str] = []
        for label in hits:
            refs.extend(labels[label].get("evidence_refs") or [])
        matches.append(
            {
                "template_id": template["template_id"],
                "display_name": template.get("display_name", template["template_id"]),
                "score": score,
                "confidence": "high" if score >= 0.8 else ("medium" if score >= 0.5 else "low"),
                "matched_labels": hits,
                "missing_labels": missing,
                "why_fit": template.get("why_fit", []),
                "why_not_full_fit": [f"missing_label:{label}" for label in missing],
                "evidence_refs": sorted(set(refs))[:12],
                "counterevidence": ["negative_or_counterexample_cases_present"],
                "forbidden_scenarios": template.get("forbidden_scenarios", []),
                "soft_anchor_only": True,
                "public_case_as_signal": False,
            }
        )
    matches.sort(key=lambda item: (-float(item["score"]), -len(item.get("matched_labels") or []), str(item["template_id"])))
    status = "emerging" if matches and float(matches[0]["score"]) >= 0.5 else "no_template_match"
    return {
        "schema": "smartmoney_cub_template_anchor.v1",
        "emergence_status": {
            "status": status,
            "blockers": [],
            "closed_case_count": style_profile.get("closed_case_count", 0),
            "market_phase_count": len(style_profile.get("market_phases") or []),
        },
        "template_matches": matches,
        "safety": SAFETY_DECLARATION,
    }


def build_style_anchor_context(anchor_result: dict[str, Any]) -> dict[str, Any]:
    top = (anchor_result.get("template_matches") or [{}])[0]
    return {
        "schema": "smartmoney_cub_style_anchor_context.v1",
        "active": bool(top) and anchor_result.get("emergence_status", {}).get("status") == "emerging",
        "template_id": top.get("template_id", ""),
        "soft_weight_only": True,
        "can_override_risk_contract": False,
        "can_trigger_buy": False,
        "public_case_as_signal": False,
        "mutates_champion": False,
        "requires_user_confirmation": True,
        "forbidden_scenarios": top.get("forbidden_scenarios", []),
        "safety": SAFETY_DECLARATION,
    }


def _training_suggestions(anchor_result: dict[str, Any]) -> list[str]:
    if anchor_result.get("emergence_status", {}).get("status") != "emerging":
        return ["Continue collecting closed, evaluated cases before naming a style anchor."]
    top = anchor_result["template_matches"][0]
    return [
        f"Use {top['display_name']} as a soft review lens, not as a trade trigger.",
        "For every future candidate, write why the setup fits and why it might be a false fit.",
        "Preserve invalidation, time stop, give-up conditions, and market-stage gates before style scoring.",
    ]


def build_mentor_fit(payload: dict[str, Any]) -> dict[str, Any]:
    cases = [item for item in _listify(payload.get("cases")) if isinstance(item, dict)]
    memories = [item for item in _listify(payload.get("confirmed_memories")) if isinstance(item, dict)]
    templates = payload.get("template_registry")
    template_registry = [item for item in _listify(templates) if isinstance(item, dict)] if templates is not None else None
    style_profile = infer_user_style_labels(cases, memories)
    anchor_result = match_template_anchors(style_profile, template_registry)
    return {
        "schema": MENTOR_FIT_SCHEMA,
        "generated_at": _now_iso(),
        "style_labels": style_profile["style_labels"],
        "style_profile": style_profile,
        "emergence_status": anchor_result["emergence_status"],
        "template_matches": anchor_result["template_matches"],
        "style_anchor_context": build_style_anchor_context(anchor_result),
        "training_suggestions": _training_suggestions(anchor_result),
        "network_required": False,
        "telemetry": False,
        "mutates_champion": False,
        "public_case_as_signal": False,
        "requires_user_confirmation": True,
        "safety": SAFETY_DECLARATION,
    }
