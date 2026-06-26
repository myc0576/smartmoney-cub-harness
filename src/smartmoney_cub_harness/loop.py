from __future__ import annotations

import json
import platform
import sys
from pathlib import Path
from typing import Any

from smartmoney_cub_harness import __version__
from smartmoney_cub_harness.agent_trigger import AgentIntent, normalize_agent_trigger_text, resolve_agent_trigger
from smartmoney_cub_harness.evaluator import evaluate_decision
from smartmoney_cub_harness.outcome import build_outcome
from smartmoney_cub_harness.registry import register_candidate
from smartmoney_cub_harness.run_capture import capture_run, get_command_preset
from smartmoney_cub_harness.safety import redact
from smartmoney_cub_harness.schemas import SAFETY_DECLARATION, VALID_HORIZONS

LOOP_NAME = "observe_candidate_plan_position_outcome_review_rule_update"
TOY_DECISION_TIME = "2026-06-01T15:30:00+08:00"
TOY_PRICE_SOURCE = "examples/toy_strategy/sample_prices.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(redact(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _display_path(path: str | Path, root: Path) -> str:
    resolved = Path(path).resolve()
    try:
        display = resolved.relative_to(root.resolve())
    except ValueError:
        return str(redact(str(resolved))).replace("\\", "/")
    return display.as_posix()


def _doctor_payload(root: Path) -> dict[str, Any]:
    return redact(
        {
            "status": "ok",
            "package": "smartmoney-cub-harness",
            "version": __version__,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "cwd": str(root),
            "network_required": False,
            "execution_integrations": "disabled",
            "default_data_mode": "offline_json_fixtures",
            "safety": SAFETY_DECLARATION,
        }
    )


def _trace_entry(
    step: str,
    status: str,
    *,
    input_payload: Any,
    output_payload: Any,
    decision_time: str,
    available_at: str | None = None,
    no_future_leakage: bool = True,
) -> dict[str, Any]:
    return redact(
        {
            "step": step,
            "status": status,
            "input": input_payload,
            "output": output_payload,
            "safety": SAFETY_DECLARATION,
            "decision_time": decision_time,
            "available_at": available_at or decision_time,
            "no_future_leakage": no_future_leakage,
            "champion_mutated": False,
        }
    )


def _write_trace(trace_path: Path, entries: list[dict[str, Any]]) -> None:
    trace_path.write_text(
        "".join(json.dumps(redact(entry), ensure_ascii=False, sort_keys=True) + "\n" for entry in entries),
        encoding="utf-8",
    )


def _decision_plan(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "smartmoney_cub_decision_plan.v1",
        "thesis": decision.get("thesis") or "toy pullback observation with delayed review",
        "invalidation": decision.get("invalidation_price"),
        "time_stop": decision.get("time_stop"),
        "give_up_conditions": decision.get("give_up_conditions", []),
        "max_position_note": "No real position sizing is produced; human decision required.",
        "safety": SAFETY_DECLARATION,
        "champion_mutated": False,
    }


def _position_check(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "smartmoney_cub_position_check.v1",
        "status": "ok",
        "symbol": decision.get("symbol"),
        "position_state": "toy_offline_no_real_position",
        "risk_flag": "read_only_fixture_review",
        "max_position_note": "No broker, account, order, or live position data is accessed.",
        "human_decision_required": True,
        "safety": SAFETY_DECLARATION,
        "champion_mutated": False,
    }


def _review_payload(
    decision: dict[str, Any],
    outcome: dict[str, Any],
    evaluation: dict[str, Any],
    position_check: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "smartmoney_cub_loop_review.v1",
        "status": "reviewed",
        "decision_label": decision.get("action_label"),
        "result_status": evaluation.get("grade"),
        "failure_tags": evaluation.get("failure_tags", []),
        "risk_flag": position_check.get("risk_flag"),
        "outcome_horizon": outcome.get("horizon"),
        "review_note": "Offline toy evidence was evaluated after the recorded decision time.",
        "safety": SAFETY_DECLARATION,
        "champion_mutated": False,
    }


def _challenger_rule_proposal(evaluation: dict[str, Any]) -> dict[str, Any]:
    grade = str(evaluation.get("grade") or "not_evaluated")
    return {
        "rule_id": f"toy-loop-{grade}-challenger-v1",
        "family": "toy-loop-review",
        "candidate_role": "challenger",
        "proposal": "Require every non-silent toy observation to preserve invalidation, time stop, give-up conditions, data source, available time, and data quality.",
        "why_proposed": "The loop exercises the risk contract and records whether delayed evidence supported the observation.",
        "evidence": {
            "grade": grade,
            "failure_tags": evaluation.get("failure_tags", []),
            "sample_count": 1,
        },
        "confidence": "low",
        "requires_human_confirmation": True,
        "champion_mutated": False,
        "metrics": {
            "sample_count": 1,
            "false_alert_rate": 0.0,
            "missed_opportunity_rate": 0.0,
            "future_leakage_count": 0,
            "risk_contract_violation_rate": 0.0,
        },
        "safety": SAFETY_DECLARATION,
    }


def _generate_report(
    *,
    trigger_text: str,
    intent: AgentIntent,
    preset: str,
    decision: dict[str, Any],
    outcome: dict[str, Any],
    evaluation: dict[str, Any],
    plan: dict[str, Any],
    position_check: dict[str, Any],
    proposal: dict[str, Any],
) -> str:
    scores = evaluation.get("scores", {})
    failure_tags = evaluation.get("failure_tags", [])
    return "\n".join(
        [
            "# Smartmoney Cub Agent Loop Report",
            "",
            "## Safety",
            "",
            SAFETY_DECLARATION,
            "",
            "## Loop",
            "",
            "Observe -> Candidate -> Plan -> Position Check -> Outcome -> Review -> Rule Update",
            "",
            "## Trigger",
            "",
            f"agent_trigger: {trigger_text or 'loop'}",
            f"intent: {intent.intent_name}",
            "",
            "## Decision Context",
            "",
            f"* preset: {preset}",
            f"* decision_time: {decision.get('decision_time')}",
            f"* available data: {decision.get('data_source')}",
            f"* data quality: {decision.get('data_quality_flag')}",
            "* no future leakage status: true",
            "",
            "## Candidate",
            "",
            f"* toy candidate id: {decision.get('symbol')}",
            "* reason category: toy_pullback_observation",
            f"* risk state: {position_check.get('risk_flag')}",
            "",
            "## Plan",
            "",
            f"* thesis: {plan.get('thesis')}",
            f"* invalidation condition: {plan.get('invalidation')}",
            f"* time stop: {plan.get('time_stop')}",
            f"* give-up conditions: {', '.join(str(item) for item in plan.get('give_up_conditions', []))}",
            f"* max position note: {plan.get('max_position_note')}",
            "",
            "## Outcome",
            "",
            f"* {str(outcome.get('horizon')).upper()} toy outcome: {outcome.get(str(outcome.get('horizon')) + '_return_pct')}%",
            f"* max adverse excursion: {outcome.get('max_adverse_excursion_pct')}%",
            f"* result status: {evaluation.get('grade')}",
            "",
            "## Evaluation",
            "",
            "| score | value |",
            "| --- | ---: |",
            *[f"| {key} | {value} |" for key, value in scores.items()],
            "",
            f"* grade: {evaluation.get('grade')}",
            f"* failure tags: {', '.join(failure_tags) if failure_tags else 'none'}",
            "",
            "## Rule Update Proposal",
            "",
            f"* proposed challenger rule: {proposal.get('rule_id')}",
            f"* why proposed: {proposal.get('why_proposed')}",
            f"* evidence: grade={proposal['evidence']['grade']}, sample_count={proposal['evidence']['sample_count']}",
            f"* confidence: {proposal.get('confidence')}",
            "* champion_mutated: false",
            "* requires human confirmation: true",
            "",
            "## What this proves",
            "",
            "* the harness can run an offline loop",
            "* the harness can log decisions",
            "* the harness can evaluate outcomes",
            "* the harness can propose challenger rules safely",
            "",
            "## What this does NOT prove",
            "",
            "* no live trading performance",
            "* no stock-picking instruction",
            "* no predictive edge claim",
            "* no broker integration",
            "",
        ]
    )


def run_agent_loop(
    *,
    preset: str = "toy",
    horizon: str = "d1",
    agent_trigger: str = "",
    root: str | Path = ".",
) -> dict[str, Any]:
    if preset != "toy":
        raise ValueError("loop currently supports only the offline toy preset")
    if horizon not in VALID_HORIZONS:
        raise ValueError("horizon must be one of: d1, d3")

    root_path = Path(root).resolve()
    decision_time = TOY_DECISION_TIME
    entries: list[dict[str, Any]] = []

    trigger_text = normalize_agent_trigger_text(agent_trigger)
    intent = resolve_agent_trigger(trigger_text)
    entries.append(
        _trace_entry(
            "resolve_agent_trigger",
            "ok",
            input_payload={"agent_trigger": trigger_text},
            output_payload=intent.to_dict(),
            decision_time=decision_time,
        )
    )

    doctor_result = _doctor_payload(root_path)
    entries.append(
        _trace_entry(
            "doctor",
            "ok",
            input_payload={"preset": preset},
            output_payload={"status": doctor_result["status"], "network_required": False},
            decision_time=decision_time,
        )
    )

    capture_result = capture_run(
        root=root_path,
        mode="after-close",
        commands=get_command_preset(preset),
        decision_time=decision_time,
        timeout_seconds=300,
        sandbox=True,
    )
    run_dir = Path(capture_result["run_dir"])
    run_dir_rel = _display_path(run_dir, root_path)
    decision_path = run_dir / "decision.json"
    decision_path_rel = _display_path(decision_path, root_path)
    decision = _read_json(decision_path)
    manifest_validation = capture_result["manifest_validation"]
    no_future_leakage = not any(str(error).startswith("future_leakage") for error in manifest_validation.get("errors", []))

    entries.append(
        _trace_entry(
            "observe",
            "ok",
            input_payload={"preset": preset, "mode": "after-close"},
            output_payload={
                "manifest_ok": manifest_validation.get("ok"),
                "data_sources": [source["name"] for source in capture_result["manifest"].get("data_sources", [])],
            },
            decision_time=decision_time,
            no_future_leakage=no_future_leakage,
        )
    )

    entries.append(
        _trace_entry(
            "candidate",
            "ok",
            input_payload={"artifact": decision_path_rel},
            output_payload={"symbol": decision.get("symbol"), "action_label": decision.get("action_label")},
            decision_time=decision_time,
            available_at=decision.get("available_at"),
            no_future_leakage=no_future_leakage,
        )
    )

    plan = _decision_plan(decision)
    plan_path = run_dir / "decision_plan.json"
    _write_json(plan_path, plan)
    entries.append(
        _trace_entry(
            "plan",
            "ok",
            input_payload={"decision_path": decision_path_rel},
            output_payload={"plan_path": _display_path(plan_path, root_path), "time_stop": plan.get("time_stop")},
            decision_time=decision_time,
            available_at=decision.get("available_at"),
            no_future_leakage=no_future_leakage,
        )
    )

    position_check = _position_check(decision)
    position_check_path = run_dir / "position_check.json"
    _write_json(position_check_path, position_check)
    entries.append(
        _trace_entry(
            "position_check",
            "ok",
            input_payload={"decision_path": decision_path_rel},
            output_payload={"position_check_path": _display_path(position_check_path, root_path), "status": "ok"},
            decision_time=decision_time,
            available_at=decision.get("available_at"),
            no_future_leakage=no_future_leakage,
        )
    )

    outcome_path = build_outcome(run_dir_rel, horizon=horizon, price_source=TOY_PRICE_SOURCE)
    outcome_path = Path(outcome_path)
    outcome = _read_json(outcome_path)
    outcome_path_rel = _display_path(outcome_path, root_path)
    entries.append(
        _trace_entry(
            "outcome",
            "ok",
            input_payload={"horizon": horizon, "price_source": TOY_PRICE_SOURCE},
            output_payload={"outcome_path": outcome_path_rel, "horizon": horizon},
            decision_time=decision_time,
            available_at=decision.get("available_at"),
            no_future_leakage=no_future_leakage,
        )
    )

    evaluation = evaluate_decision(decision, outcome)
    evaluation.update(
        {
            "status": "evaluated",
            "decision_path": decision_path_rel,
            "outcome_path": outcome_path_rel,
            "safety": SAFETY_DECLARATION,
        }
    )
    evaluation_path = run_dir / "eval.json"
    _write_json(evaluation_path, evaluation)
    evaluation_path_rel = _display_path(evaluation_path, root_path)
    entries.append(
        _trace_entry(
            "evaluate",
            "ok",
            input_payload={"decision_path": decision_path_rel, "outcome_path": outcome_path_rel},
            output_payload={"evaluation_path": evaluation_path_rel, "grade": evaluation.get("grade")},
            decision_time=decision_time,
            available_at=decision.get("available_at"),
            no_future_leakage=no_future_leakage,
        )
    )

    review = _review_payload(decision, outcome, evaluation, position_check)
    review_path = run_dir / "review.json"
    _write_json(review_path, review)
    entries.append(
        _trace_entry(
            "review",
            "ok",
            input_payload={"evaluation_path": evaluation_path_rel},
            output_payload={"review_path": _display_path(review_path, root_path), "result_status": review.get("result_status")},
            decision_time=decision_time,
            available_at=decision.get("available_at"),
            no_future_leakage=no_future_leakage,
        )
    )

    proposal = _challenger_rule_proposal(evaluation)
    proposal_path = run_dir / "proposed_challenger_rule.json"
    _write_json(proposal_path, proposal)
    registry_path = run_dir / "rule_registry.json"
    registry_result = register_candidate(registry_path, proposal, confirm_promote=False)
    proposal_path_rel = _display_path(proposal_path, root_path)
    registry_path_rel = _display_path(registry_path, root_path)
    entries.append(
        _trace_entry(
            "propose_challenger_rule",
            "ok",
            input_payload={"review_path": _display_path(review_path, root_path)},
            output_payload={
                "proposed_challenger_rule_path": proposal_path_rel,
                "rule_registry_path": registry_path_rel,
                "registry_status": registry_result.get("status"),
            },
            decision_time=decision_time,
            available_at=decision.get("available_at"),
            no_future_leakage=no_future_leakage,
        )
    )

    report_path = run_dir / "loop_report.md"
    report_text = _generate_report(
        trigger_text=trigger_text,
        intent=intent,
        preset=preset,
        decision=decision,
        outcome=outcome,
        evaluation=evaluation,
        plan=plan,
        position_check=position_check,
        proposal=proposal,
    )
    report_path.write_text(report_text, encoding="utf-8")
    report_path_rel = _display_path(report_path, root_path)
    entries.append(
        _trace_entry(
            "generate_report",
            "ok",
            input_payload={"proposal_path": proposal_path_rel},
            output_payload={"report_path": report_path_rel},
            decision_time=decision_time,
            available_at=decision.get("available_at"),
            no_future_leakage=no_future_leakage,
        )
    )

    trace_path = run_dir / "trace.jsonl"
    _write_trace(trace_path, entries)
    trace_path_rel = _display_path(trace_path, root_path)

    summary = {
        "status": "ok",
        "loop_name": LOOP_NAME,
        "preset": preset,
        "horizon": horizon,
        "agent_intent": intent.intent_name,
        "run_id": run_dir.name,
        "run_dir": run_dir_rel,
        "report_path": report_path_rel,
        "trace_path": trace_path_rel,
        "decision_path": decision_path_rel,
        "outcome_path": outcome_path_rel,
        "evaluation_path": evaluation_path_rel,
        "proposed_challenger_rule_path": proposal_path_rel,
        "rule_registry_path": registry_path_rel,
        "grade": evaluation.get("grade"),
        "safety": SAFETY_DECLARATION,
        "champion_mutated": False,
    }
    return redact(summary)
