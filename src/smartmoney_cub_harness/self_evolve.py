from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from smartmoney_cub_harness.case_bank import collect_offline_case
from smartmoney_cub_harness.evaluator import evaluate_decision
from smartmoney_cub_harness.evolution_ledger import append_ledger_event
from smartmoney_cub_harness.loop_state import initial_state, load_state, mark_stage, now_iso, write_state
from smartmoney_cub_harness.manifest import validate_run_manifest
from smartmoney_cub_harness.memory import save_memory_record
from smartmoney_cub_harness.private_input import fingerprint_file, load_private_cases
from smartmoney_cub_harness.registry import promotion_blockers, register_candidate
from smartmoney_cub_harness.run_capture import safe_name
from smartmoney_cub_harness.safety import redact
from smartmoney_cub_harness.schemas import (
    MANIFEST_SCHEMA,
    PROMOTION_PACKET_SCHEMA,
    SAFETY_DECLARATION,
    SELF_EVOLVE_CONTRACT_SCHEMA,
    VALID_HORIZONS,
)

SELF_EVOLVE_LOOP_NAME = "private_csv_budgeted_self_evolve_loop"
FORBIDDEN_CAPABILITIES = (
    "order_placement",
    "order_cancellation",
    "broker_automation",
    "account_modification",
    "live_execution",
    "credential_handling",
)


def _new_loop_id() -> str:
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    return f"self-evolve-{stamp}-{uuid.uuid4().hex[:8]}"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(redact(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _display_path(path: str | Path, root: str | Path | None = None) -> str:
    resolved = Path(path).resolve()
    base = Path(root).resolve() if root else Path.cwd().resolve()
    try:
        return resolved.relative_to(base).as_posix()
    except ValueError:
        return str(redact(str(resolved))).replace("\\", "/")


def _append_trace(loop_dir: Path, entry: dict[str, Any]) -> None:
    payload = {
        "created_at": now_iso(),
        "safety": SAFETY_DECLARATION,
        "network_required": False,
        "telemetry": False,
        "champion_mutated": False,
        **entry,
    }
    trace_path = loop_dir / "trace.jsonl"
    with trace_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(redact(payload), ensure_ascii=False, sort_keys=True) + "\n")


def _contract_path(loop_dir: Path) -> Path:
    return loop_dir / "contract.json"


def _write_contract(
    *,
    loop_dir: Path,
    input_csv: str | Path,
    loop_id: str,
    max_iterations: int,
    time_budget_min: float,
    horizon: str,
) -> dict[str, Any]:
    contract = {
        "schema": SELF_EVOLVE_CONTRACT_SCHEMA,
        "loop_id": loop_id,
        "loop_name": SELF_EVOLVE_LOOP_NAME,
        "created_at": now_iso(),
        "input_fingerprint": fingerprint_file(input_csv),
        "max_iterations": max_iterations,
        "time_budget_min": time_budget_min,
        "horizon": horizon,
        "output_root": _display_path(loop_dir),
        "forbidden_capabilities": list(FORBIDDEN_CAPABILITIES),
        "verification_checklist": [
            "validate_private_csv",
            "write_loop_state",
            "append_trace",
            "evaluate_cases",
            "write_promotion_packet",
            "preserve_champion_until_confirmation",
        ],
        "network_required": False,
        "telemetry": False,
        "champion_mutated": False,
        "safety": SAFETY_DECLARATION,
    }
    _write_json(_contract_path(loop_dir), contract)
    return contract


def _load_or_create_loop(
    *,
    input_csv: str | Path,
    state_root: str | Path,
    resume: str | None,
    max_iterations: int,
    time_budget_min: float,
    horizon: str,
) -> tuple[str, Path, dict[str, Any], dict[str, Any]]:
    root = Path(state_root)
    if resume:
        loop_id = resume
        loop_dir = root / loop_id
        state = load_state(loop_dir)
        contract = _read_json(_contract_path(loop_dir))
        current_fingerprint = fingerprint_file(input_csv)
        if current_fingerprint.get("sha256") != (contract.get("input_fingerprint") or {}).get("sha256"):
            raise ValueError("resume_input_csv_fingerprint_mismatch")
        _append_trace(
            loop_dir,
            {
                "role": "planner_contract",
                "step": "resume_contract",
                "status": "ok",
                "loop_id": loop_id,
                "input": {"resume": resume},
                "output": {"state_path": "loop_state.json"},
            },
        )
        return loop_id, loop_dir, state, contract

    loop_id = _new_loop_id()
    loop_dir = root / loop_id
    loop_dir.mkdir(parents=True, exist_ok=False)
    state = initial_state(loop_id, max_iterations=max_iterations, horizon=horizon)
    state = write_state(loop_dir, state)
    contract = _write_contract(
        loop_dir=loop_dir,
        input_csv=input_csv,
        loop_id=loop_id,
        max_iterations=max_iterations,
        time_budget_min=time_budget_min,
        horizon=horizon,
    )
    _append_trace(
        loop_dir,
        {
            "role": "planner_contract",
            "step": "write_contract",
            "status": "ok",
            "loop_id": loop_id,
            "input": {"horizon": horizon, "max_iterations": max_iterations},
            "output": {"contract_path": "contract.json", "state_path": "loop_state.json"},
        },
    )
    state = mark_stage(
        loop_dir,
        state,
        stage="planner_contract",
        status="contract_written",
        message="contract and initial state written",
        artifact_paths={"contract": "contract.json", "loop_state": "loop_state.json"},
    )
    return loop_id, loop_dir, state, contract


def _manifest_for_case(case: dict[str, Any], case_dir: Path) -> dict[str, Any]:
    decision = case["decision"]
    source_name = decision.get("data_source") or "private_csv"
    return {
        "schema": MANIFEST_SCHEMA,
        "run_id": case_dir.name,
        "decision_time": decision.get("decision_time"),
        "mode": "private-csv-review",
        "safety": SAFETY_DECLARATION,
        "selection_system_version": "private_csv_self_evolve_v1",
        "selection_system_refs": ["local_private_csv"],
        "data_sources": [
            {
                "name": source_name,
                "fetch_time": decision.get("available_at"),
                "available_at": decision.get("available_at"),
                "data_quality_flag": decision.get("data_quality_flag"),
                "artifact_stdout": None,
                "artifact_stderr": None,
                "artifact_meta": None,
            }
        ],
    }


def _score_review_quality(decision: dict[str, Any], manifest_validation: dict[str, Any]) -> dict[str, Any]:
    thesis = str(decision.get("thesis") or "").strip()
    give_up = decision.get("give_up_conditions") if isinstance(decision.get("give_up_conditions"), list) else []
    risk_complete = all(
        [
            decision.get("invalidation_price") not in (None, ""),
            decision.get("time_stop") not in (None, ""),
            bool(give_up),
        ]
    )
    evidence_quality = 1.0 if decision.get("data_quality_flag") == "ok" else 0.5
    repeatable = 1.0 if decision.get("data_source") and manifest_validation.get("ok") else 0.0
    scores = {
        "thesis_clarity": 1.0 if len(thesis) >= 10 else 0.0,
        "risk_contract_completeness": 1.0 if risk_complete else 0.0,
        "evidence_quality": evidence_quality,
        "repeatability": repeatable,
    }
    scores["average"] = round(sum(scores.values()) / len(scores), 3)
    return scores


def _review_payload(
    *,
    case: dict[str, Any],
    evaluation: dict[str, Any],
    manifest_validation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "smartmoney_cub_self_evolve_review.v1",
        "case_id": case.get("case_id"),
        "status": "reviewed",
        "decision_label": case["decision"].get("action_label"),
        "result_status": evaluation.get("grade"),
        "failure_tags": evaluation.get("failure_tags", []),
        "manifest_ok": manifest_validation.get("ok"),
        "rubric": _score_review_quality(case["decision"], manifest_validation),
        "review_note": "Local private CSV evidence was evaluated under read-only self-evolution.",
        "network_required": False,
        "telemetry": False,
        "champion_mutated": False,
        "safety": SAFETY_DECLARATION,
    }


def _read_case_evaluations(loop_dir: Path, completed_case_ids: set[str]) -> list[dict[str, Any]]:
    evaluations: list[dict[str, Any]] = []
    cases_root = loop_dir / "cases"
    if not cases_root.exists():
        return evaluations
    for case_dir in sorted(cases_root.iterdir()):
        eval_path = case_dir / "eval.json"
        if not eval_path.exists():
            continue
        evaluation = _read_json(eval_path)
        case_id = str(evaluation.get("case_id") or "")
        if case_id in completed_case_ids:
            evaluations.append(evaluation)
    return evaluations


def _aggregate_metrics(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    sample_count = len(evaluations)
    if sample_count == 0:
        return {
            "sample_count": 0,
            "false_alert_rate": 0.0,
            "missed_opportunity_rate": 0.0,
            "future_leakage_count": 0,
            "risk_contract_violation_rate": 0.0,
        }
    false_alerts = sum(1 for item in evaluations if item.get("grade") == "false_alert")
    missed = sum(1 for item in evaluations if item.get("grade") == "missed_opportunity")
    future_leakage = sum(1 for item in evaluations if "future_leakage" in " ".join(item.get("failure_tags", [])))
    risk_violations = sum(1 for item in evaluations if (item.get("scores") or {}).get("risk_contract_violation"))
    return {
        "sample_count": sample_count,
        "false_alert_rate": round(false_alerts / sample_count, 4),
        "missed_opportunity_rate": round(missed / sample_count, 4),
        "future_leakage_count": future_leakage,
        "risk_contract_violation_rate": round(risk_violations / sample_count, 4),
    }


def _candidate_from_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    blockers = promotion_blockers(metrics)
    confidence = "medium" if not blockers else ("low" if metrics.get("sample_count", 0) < 20 else "medium")
    return {
        "rule_id": "private-csv-risk-contract-challenger-v1",
        "family": "private-csv-review",
        "candidate_role": "challenger",
        "proposal": (
            "Require every local private review case to preserve thesis, invalidation, time stop, "
            "give-up conditions, source provenance, available time, data quality, and delayed outcome evidence."
        ),
        "why_proposed": "The budgeted self-evolve loop aggregates local private review outcomes without execution access.",
        "evidence": {
            "metrics": metrics,
            "blockers": blockers,
        },
        "confidence": confidence,
        "requires_human_confirmation": True,
        "champion_mutated": False,
        "metrics": metrics,
        "safety": SAFETY_DECLARATION,
    }


def _write_promotion_packet(
    *,
    loop_dir: Path,
    candidate: dict[str, Any],
    registry_status: str,
    registry_reasons: list[str],
) -> dict[str, Any]:
    blockers = promotion_blockers(candidate.get("metrics") or {})
    packet = {
        "schema": PROMOTION_PACKET_SCHEMA,
        "status": "promotion_recommended" if not blockers else "blocked_challenger",
        "created_at": now_iso(),
        "candidate": candidate,
        "registry_status": registry_status,
        "blockers": blockers,
        "registry_reasons": registry_reasons,
        "rule_registry_path": "rule_registry.json",
        "ledger_path": "evolution_ledger.jsonl",
        "human_confirmation": {
            "decision": None,
            "note": None,
            "decided_at": None,
        },
        "network_required": False,
        "telemetry": False,
        "champion_mutated": False,
        "safety": SAFETY_DECLARATION,
    }
    _write_json(loop_dir / "promotion_packet.json", packet)
    append_ledger_event(
        loop_dir / "evolution_ledger.jsonl",
        "promotion_packet_created",
        {
            "status": packet["status"],
            "rule_id": candidate.get("rule_id"),
            "metrics": candidate.get("metrics"),
            "blockers": blockers,
            "champion_mutated": False,
            "requires_human_confirmation": True,
        },
    )
    return packet


def _write_report(
    *,
    loop_dir: Path,
    loop_id: str,
    contract: dict[str, Any],
    state: dict[str, Any],
    metrics: dict[str, Any],
    packet: dict[str, Any],
) -> str:
    blockers = packet.get("blockers") or []
    next_bottleneck = "human_confirmation_required" if packet.get("status") == "promotion_recommended" else (
        blockers[0] if blockers else "none"
    )
    report = "\n".join(
        [
            "# Smartmoney Cub Self-Evolve Report",
            "",
            f"safety: {SAFETY_DECLARATION}",
            "network_required: false",
            "telemetry: false",
            "champion_mutated: false",
            "",
            "## Contract",
            "",
            f"- loop_id: {loop_id}",
            f"- loop_name: {SELF_EVOLVE_LOOP_NAME}",
            f"- horizon: {contract.get('horizon')}",
            f"- max_iterations: {contract.get('max_iterations')}",
            f"- time_budget_min: {contract.get('time_budget_min')}",
            "",
            "## Results",
            "",
            f"- completed_cases: {len(state.get('completed_case_ids', []))}",
            f"- failed_cases: {len(state.get('failed_case_ids', []))}",
            f"- sample_count: {metrics.get('sample_count')}",
            f"- false_alert_rate: {metrics.get('false_alert_rate')}",
            f"- missed_opportunity_rate: {metrics.get('missed_opportunity_rate')}",
            f"- future_leakage_count: {metrics.get('future_leakage_count')}",
            f"- risk_contract_violation_rate: {metrics.get('risk_contract_violation_rate')}",
            "",
            "## Promotion Gate",
            "",
            f"- status: {packet.get('status')}",
            f"- blockers: {', '.join(blockers) if blockers else 'none'}",
            f"- next_bottleneck: {next_bottleneck}",
            "- champion_mutated: false",
            "- human_confirmation_required: true",
            "",
            "## Trace Reading",
            "",
            "- Inspect `trace.jsonl` for role-separated contract, runner, evaluator, archivist, and challenger steps.",
            "- Inspect `promotion_packet.json` before any `confirm-promotion` action.",
            "",
            "## What this does NOT prove",
            "",
            "- no live trading performance",
            "- no stock-picking instruction",
            "- no predictive edge claim",
            "- no broker integration",
            "",
        ]
    )
    report_path = loop_dir / "self_evolve_report.md"
    report_path.write_text(report, encoding="utf-8")
    return "self_evolve_report.md"


def _process_case(
    *,
    loop_dir: Path,
    case: dict[str, Any],
    index: int,
    evaluations: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    case_id = str(case.get("case_id") or f"case-{index}")
    case_dir = loop_dir / "cases" / f"{index:04d}-{safe_name(case_id)}"
    case_dir.mkdir(parents=True, exist_ok=True)

    manifest = _manifest_for_case(case, case_dir)
    manifest_validation = validate_run_manifest(manifest)
    decision = case["decision"]
    outcome = case["outcome"]

    _write_json(case_dir / "run_manifest.json", manifest)
    _write_json(case_dir / "manifest_validation.json", manifest_validation)
    _write_json(case_dir / "decision.json", decision)
    _write_json(case_dir / f"outcome_{outcome['horizon']}.json", outcome)

    evaluation = evaluate_decision(decision, outcome)
    evaluation.update(
        {
            "status": "evaluated",
            "case_id": case_id,
            "decision_path": "decision.json",
            "outcome_path": f"outcome_{outcome['horizon']}.json",
            "safety": SAFETY_DECLARATION,
        }
    )
    _write_json(case_dir / "eval.json", evaluation)

    review = _review_payload(case=case, evaluation=evaluation, manifest_validation=manifest_validation)
    _write_json(case_dir / "review.json", review)

    case_result = collect_offline_case(case_dir, case_dir / "case_record.json")
    memory_result = save_memory_record(case_dir / "case_record.json", case_dir / "memory.md")
    evaluations.append(evaluation)

    metrics = _aggregate_metrics(evaluations)
    candidate = _candidate_from_metrics(metrics)
    registry_result = register_candidate(loop_dir / "rule_registry.json", candidate, confirm_promote=False)
    append_ledger_event(
        loop_dir / "evolution_ledger.jsonl",
        "self_evolve_case_reviewed",
        {
            "case_id": case_id,
            "grade": evaluation.get("grade"),
            "case_record": f"cases/{case_dir.name}/case_record.json",
            "memory_record": f"cases/{case_dir.name}/memory.md",
            "metrics": metrics,
            "champion_mutated": False,
            "requires_human_confirmation": True,
        },
    )
    artifacts = {
        "case_dir": f"cases/{case_dir.name}",
        "decision": f"cases/{case_dir.name}/decision.json",
        "outcome": f"cases/{case_dir.name}/outcome_{outcome['horizon']}.json",
        "evaluation": f"cases/{case_dir.name}/eval.json",
        "review": f"cases/{case_dir.name}/review.json",
        "case_record": f"cases/{case_dir.name}/case_record.json",
        "memory": f"cases/{case_dir.name}/memory.md",
        "rule_registry": "rule_registry.json",
    }
    return {
        "case_id": case_id,
        "grade": evaluation.get("grade"),
        "manifest_ok": manifest_validation.get("ok"),
        "case_result": case_result,
        "memory_result": memory_result,
        "registry_result": registry_result,
        "metrics": metrics,
        "candidate": candidate,
        "artifacts": artifacts,
    }, evaluation


def run_self_evolve(
    *,
    input_csv: str | Path,
    max_iterations: int,
    time_budget_min: float,
    horizon: str,
    state_root: str | Path = "state/self_evolve",
    resume: str | None = None,
) -> dict[str, Any]:
    if max_iterations < 1:
        raise ValueError("max_iterations must be >= 1")
    if time_budget_min < 0:
        raise ValueError("time_budget_min must be >= 0")
    if horizon not in VALID_HORIZONS:
        raise ValueError("horizon must be one of: d1, d3")

    started = time.monotonic()
    loop_id, loop_dir, state, contract = _load_or_create_loop(
        input_csv=input_csv,
        state_root=state_root,
        resume=resume,
        max_iterations=max_iterations,
        time_budget_min=time_budget_min,
        horizon=horizon,
    )

    validation = load_private_cases(input_csv, horizon=horizon)
    _write_json(loop_dir / "input_validation.json", validation)
    _append_trace(
        loop_dir,
        {
            "role": "planner_contract",
            "step": "validate_private_csv",
            "status": "ok" if validation.get("ok") else "failed",
            "loop_id": loop_id,
            "input": {"horizon": horizon},
            "output": {
                "case_count": validation.get("case_count", 0),
                "errors": validation.get("errors", []),
                "input_validation_path": "input_validation.json",
            },
        },
    )
    if not validation.get("ok"):
        state = mark_stage(
            loop_dir,
            state,
            stage="planner_contract",
            status="failed",
            message="private CSV validation failed",
            artifact_paths={"input_validation": "input_validation.json"},
        )
        raise ValueError("private_csv_validation_failed:" + ",".join(validation.get("errors", [])))

    completed_case_ids = set(str(item) for item in state.get("completed_case_ids", []))
    evaluations = _read_case_evaluations(loop_dir, completed_case_ids)
    processed_this_run = 0
    budget_seconds = time_budget_min * 60
    cases = validation["cases"]

    for index, case in enumerate(cases, start=1):
        case_id = str(case.get("case_id"))
        if case_id in completed_case_ids:
            continue
        if processed_this_run >= max_iterations:
            break
        if budget_seconds and time.monotonic() - started >= budget_seconds:
            state = mark_stage(
                loop_dir,
                state,
                stage="budget_gate",
                status="budget_exhausted",
                message="time budget reached before next case",
            )
            break

        state["restart_cursor"] = case_id
        state = mark_stage(
            loop_dir,
            state,
            stage="runner_case",
            status="running",
            message=f"processing {case_id}",
        )
        _append_trace(
            loop_dir,
            {
                "role": "runner_case",
                "step": "start_case",
                "status": "ok",
                "loop_id": loop_id,
                "case_id": case_id,
                "input": {"row_number": case.get("row_number")},
                "output": {"case_id": case_id},
            },
        )
        try:
            result, evaluation = _process_case(loop_dir=loop_dir, case=case, index=index, evaluations=evaluations)
        except Exception as exc:
            failed = list(state.get("failed_case_ids", []))
            if case_id not in failed:
                failed.append(case_id)
            state["failed_case_ids"] = failed
            state = mark_stage(
                loop_dir,
                state,
                stage="runner_case",
                status="failed",
                message=f"failed {case_id}: {exc}",
            )
            _append_trace(
                loop_dir,
                {
                    "role": "runner_case",
                    "step": "case_failed",
                    "status": "failed",
                    "loop_id": loop_id,
                    "case_id": case_id,
                    "input": {"case_id": case_id},
                    "output": {"error": str(exc)},
                },
            )
            continue

        completed = list(state.get("completed_case_ids", []))
        if case_id not in completed:
            completed.append(case_id)
        state["completed_case_ids"] = completed
        state["restart_cursor"] = None
        state = mark_stage(
            loop_dir,
            state,
            stage="archivist_memory",
            status="case_completed",
            message=f"completed {case_id}",
            artifact_paths=result["artifacts"],
        )
        _append_trace(
            loop_dir,
            {
                "role": "evaluator_gate",
                "step": "evaluate_case",
                "status": "ok",
                "loop_id": loop_id,
                "case_id": case_id,
                "input": {"case_id": case_id},
                "output": {"grade": evaluation.get("grade"), "metrics": result.get("metrics")},
            },
        )
        _append_trace(
            loop_dir,
            {
                "role": "challenger_gate",
                "step": "register_challenger",
                "status": "ok",
                "loop_id": loop_id,
                "case_id": case_id,
                "input": {"metrics": result.get("metrics")},
                "output": result.get("registry_result"),
            },
        )
        processed_this_run += 1

    final_completed_ids = set(str(item) for item in state.get("completed_case_ids", []))
    final_evaluations = _read_case_evaluations(loop_dir, final_completed_ids)
    metrics = _aggregate_metrics(final_evaluations)
    candidate = _candidate_from_metrics(metrics)
    registry_result = register_candidate(loop_dir / "rule_registry.json", candidate, confirm_promote=False)
    packet = _write_promotion_packet(
        loop_dir=loop_dir,
        candidate=candidate,
        registry_status=registry_result.get("status"),
        registry_reasons=registry_result.get("reasons", []),
    )
    report_rel = _write_report(
        loop_dir=loop_dir,
        loop_id=loop_id,
        contract=contract,
        state=state,
        metrics=metrics,
        packet=packet,
    )
    _append_trace(
        loop_dir,
        {
            "role": "archivist_memory",
            "step": "write_final_report",
            "status": "ok",
            "loop_id": loop_id,
            "input": {"metrics": metrics},
            "output": {"report": report_rel, "promotion_packet": "promotion_packet.json"},
        },
    )
    state = mark_stage(
        loop_dir,
        state,
        stage="archivist_memory",
        status="complete",
        message="self-evolve run complete",
        artifact_paths={
            "report": report_rel,
            "trace": "trace.jsonl",
            "promotion_packet": "promotion_packet.json",
            "rule_registry": "rule_registry.json",
            "ledger": "evolution_ledger.jsonl",
        },
    )

    return redact(
        {
            "status": "ok",
            "loop_name": SELF_EVOLVE_LOOP_NAME,
            "loop_id": loop_id,
            "loop_dir": _display_path(loop_dir),
            "contract": _display_path(loop_dir / "contract.json"),
            "loop_state": _display_path(loop_dir / "loop_state.json"),
            "trace": _display_path(loop_dir / "trace.jsonl"),
            "self_evolve_report": _display_path(loop_dir / report_rel),
            "ledger": _display_path(loop_dir / "evolution_ledger.jsonl"),
            "rule_registry": _display_path(loop_dir / "rule_registry.json"),
            "promotion_packet": _display_path(loop_dir / "promotion_packet.json"),
            "processed_this_run": processed_this_run,
            "completed_cases": len(state.get("completed_case_ids", [])),
            "failed_cases": len(state.get("failed_case_ids", [])),
            "metrics": metrics,
            "promotion_status": packet.get("status"),
            "promotion_blockers": packet.get("blockers", []),
            "requires_human_confirmation": True,
            "network_required": False,
            "telemetry": False,
            "champion_mutated": False,
            "safety": SAFETY_DECLARATION,
        }
    )


def confirm_promotion(promotion_packet: str | Path, *, decision: str, note: str = "") -> dict[str, Any]:
    normalized = decision.strip().lower()
    if normalized not in {"promote", "defer", "reject"}:
        raise ValueError("decision must be one of: promote, defer, reject")

    packet_path = Path(promotion_packet)
    packet = _read_json(packet_path)
    candidate = packet.get("candidate")
    if not isinstance(candidate, dict):
        raise ValueError("promotion packet missing candidate")

    blockers = promotion_blockers(candidate.get("metrics") or {})
    champion_mutated = normalized == "promote"
    if champion_mutated and blockers:
        raise ValueError("cannot promote while blockers exist: " + ",".join(blockers))

    loop_dir = packet_path.parent
    registry_path = loop_dir / str(packet.get("rule_registry_path") or "rule_registry.json")
    ledger_path = loop_dir / str(packet.get("ledger_path") or "evolution_ledger.jsonl")
    registry_result = None
    if champion_mutated:
        registry_result = register_candidate(registry_path, candidate, confirm_promote=True)

    packet["human_confirmation"] = {
        "decision": normalized,
        "note": redact(note),
        "decided_at": now_iso(),
    }
    packet["champion_mutated"] = champion_mutated
    packet["status"] = "promoted" if champion_mutated else f"{normalized}red" if normalized == "defer" else "rejected"
    _write_json(packet_path, packet)

    ledger_event = append_ledger_event(
        ledger_path,
        "promotion_confirmation_recorded",
        {
            "decision": normalized,
            "note": note,
            "rule_id": candidate.get("rule_id"),
            "champion_mutated": champion_mutated,
            "explicit_confirmation": champion_mutated,
            "requires_human_confirmation": not champion_mutated,
        },
    )
    _append_trace(
        loop_dir,
        {
            "role": "human_gate",
            "step": "confirm_promotion",
            "status": "ok",
            "input": {"decision": normalized},
            "output": {"champion_mutated": champion_mutated},
        },
    )
    return redact(
        {
            "status": "ok",
            "decision": normalized,
            "promotion_packet": _display_path(packet_path),
            "rule_registry": _display_path(registry_path),
            "registry_result": registry_result,
            "ledger_event": ledger_event.get("event"),
            "network_required": False,
            "telemetry": False,
            "champion_mutated": champion_mutated,
            "safety": SAFETY_DECLARATION,
        }
    )
