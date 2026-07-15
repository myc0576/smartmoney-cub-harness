from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

from smartmoney_cub_harness import __version__
from smartmoney_cub_harness.case_bank import collect_offline_case
from smartmoney_cub_harness.evaluator import evaluate_decision
from smartmoney_cub_harness.evolution_ledger import append_ledger_event
from smartmoney_cub_harness.launcher import launcher_diagnostics
from smartmoney_cub_harness.loop import run_agent_loop
from smartmoney_cub_harness.manifest import validate_run_manifest
from smartmoney_cub_harness.memory import save_memory_record
from smartmoney_cub_harness.mentor_fit import build_mentor_fit
from smartmoney_cub_harness.outcome import build_outcome
from smartmoney_cub_harness.privacy_audit import inspect_run_artifacts, load_payload_json, privacy_audit
from smartmoney_cub_harness.registry import register_candidate
from smartmoney_cub_harness.run_capture import capture_run, get_command_preset, parse_command
from smartmoney_cub_harness.safety import redact
from smartmoney_cub_harness.schemas import SAFETY_DECLARATION
from smartmoney_cub_harness.self_evolve import confirm_promotion, run_self_evolve
from smartmoney_cub_harness.tradingagents_adapter import (
    check_tradingagents_environment,
    ingest_tradingagents_report,
    run_tradingagents_local_bridge,
)


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(redact(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(redact(payload), ensure_ascii=False, indent=2))


def evaluate_run(run_dir: str | Path, horizon: str = "d1") -> dict[str, Any]:
    run_path = Path(run_dir)
    decision_path = run_path / "decision.json"
    outcome_path = run_path / f"outcome_{horizon}.json"
    eval_path = run_path / "eval.json"
    decision = _read_json(decision_path)
    if str(decision.get("action_label", "")).upper() == "ERROR":
        result = {
            "status": "error_decision_not_evaluated",
            "grade": "not_evaluated",
            "decision_path": str(decision_path),
            "eval_path": str(eval_path),
            "safety": SAFETY_DECLARATION,
        }
        _write_json(eval_path, result)
        return result

    outcome = _read_json(outcome_path)
    result = evaluate_decision(decision, outcome)
    result.update(
        {
            "status": "evaluated",
            "decision_path": str(decision_path),
            "outcome_path": str(outcome_path),
            "eval_path": str(eval_path),
            "safety": SAFETY_DECLARATION,
        }
    )
    _write_json(eval_path, result)
    return result


def doctor() -> dict[str, Any]:
    return {
        "status": "ok",
        "package": "smartmoney-cub-harness",
        "version": __version__,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cwd": str(Path.cwd()),
        "network_required": False,
        "telemetry": False,
        "upload": False,
        "credentials_required": False,
        "github_auth_required": False,
        "external_api_required": False,
        "broker_api_required": False,
        "execution_integrations": "disabled",
        "default_data_mode": "offline_json_fixtures",
        "launcher": launcher_diagnostics(),
        "safety": SAFETY_DECLARATION,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="smcub",
        description="Read-only trading companion harness for decision logging, outcome review, and rule evolution.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-manifest", help="Validate a run manifest JSON file")
    validate.add_argument("manifest")

    capture = sub.add_parser("capture-run", help="Run offline commands and save replay artifacts")
    capture.add_argument("--root", default=".")
    capture.add_argument("--mode", required=True, choices=["intraday", "after-close"])
    capture.add_argument("--preset", choices=["toy", "after-close"])
    capture.add_argument("--command", dest="inline_commands", action="append", default=[])
    capture.add_argument("--decision-time")
    capture.add_argument("--timeout-seconds", type=int, default=300)
    capture.add_argument("--sandbox", action="store_true")

    build_outcome_cmd = sub.add_parser("build-outcome", help="Build D1/D3 outcome JSON for a run")
    build_outcome_cmd.add_argument("run_dir")
    build_outcome_cmd.add_argument("--horizon", choices=["d1", "d3"], required=True)
    build_outcome_cmd.add_argument("--price-source", required=True)

    evaluate_run_cmd = sub.add_parser("evaluate-run", help="Evaluate a run directory")
    evaluate_run_cmd.add_argument("run_dir")
    evaluate_run_cmd.add_argument("--horizon", choices=["d1", "d3"], default="d1")

    register = sub.add_parser("register-candidate", help="Register a rule candidate")
    register.add_argument("registry")
    register.add_argument("candidate")
    register.add_argument("--confirm-promote", action="store_true")

    doctor_cmd = sub.add_parser("doctor", help="Show local package health and safety settings")
    doctor_cmd.set_defaults(command="doctor")

    loop_cmd = sub.add_parser("loop", help="Run the offline toy agent loop")
    loop_cmd.add_argument("--preset", choices=["toy"], default="toy")
    loop_cmd.add_argument("--agent-trigger", default="")
    loop_cmd.add_argument("--horizon", choices=["d1", "d3"], default="d1")
    loop_cmd.add_argument("--json", action="store_true", help="Print the final loop summary as JSON")

    mentor_fit = sub.add_parser("mentor-fit", help="Build offline toy mentor-fit style anchor JSON")
    mentor_fit.add_argument("input", help="JSON payload with toy cases and optional public templates")

    self_evolve = sub.add_parser("self-evolve", help="Run the local private CSV self-evolution loop")
    self_evolve.add_argument("--input-csv", required=True)
    self_evolve.add_argument("--max-iterations", type=int, default=20)
    self_evolve.add_argument("--time-budget-min", type=float, default=10.0)
    self_evolve.add_argument("--horizon", choices=["d1", "d3"], default="d1")
    self_evolve.add_argument("--state-root", default="state/self_evolve")
    self_evolve.add_argument("--resume")
    self_evolve.add_argument("--interactive-confirm", action="store_true")

    confirm = sub.add_parser("confirm-promotion", help="Record a manual promotion decision")
    confirm.add_argument("promotion_packet")
    confirm.add_argument("--decision", required=True, choices=["promote", "defer", "reject"])
    confirm.add_argument("--note", default="")

    privacy_cmd = sub.add_parser("privacy-audit", help="Show offline privacy and safety settings")
    privacy_cmd.set_defaults(command="privacy-audit")

    ta_doctor = sub.add_parser("tradingagents-doctor", help="Check optional TradingAgents adapter readiness")
    ta_doctor.set_defaults(command="tradingagents-doctor")

    ta_ingest = sub.add_parser("tradingagents-ingest", help="Import a local TradingAgents report as a review packet")
    ta_ingest.add_argument("--report", required=True)
    ta_ingest.add_argument("--ticker", required=True)
    ta_ingest.add_argument("--analysis-date", required=True)
    ta_ingest.add_argument("--output")

    ta_run = sub.add_parser("tradingagents-run", help="Run optional local TradingAgents bridge as review-only evidence")
    ta_run.add_argument("--ticker", required=True)
    ta_run.add_argument("--analysis-date", required=True)
    ta_run.add_argument("--output")
    ta_run.add_argument("--allow-network", action="store_true")
    ta_run.add_argument("--ack-external-llm", action="store_true")
    ta_run.add_argument("--provider")
    ta_run.add_argument("--deep-model")
    ta_run.add_argument("--quick-model")
    ta_run.add_argument("--max-debate-rounds", type=int)

    inspect = sub.add_parser("inspect-artifacts", help="Inspect a loop run directory for required safe artifacts")
    inspect.add_argument("run_dir")

    collect_case = sub.add_parser("collect-case", help="Collect a toy offline case from a run directory")
    collect_case.add_argument("run_dir")
    collect_case.add_argument("--output")

    append_ledger = sub.add_parser("append-ledger", help="Append a redacted event to an evolution ledger JSONL file")
    append_ledger.add_argument("--event", required=True)
    append_ledger.add_argument("--payload-json", required=True)
    append_ledger.add_argument("--ledger")

    save_memory = sub.add_parser("save-memory", help="Write local Markdown memory from a case record")
    save_memory.add_argument("--case-record", required=True)
    save_memory.add_argument("--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate-manifest":
        result = validate_run_manifest(_read_json(args.manifest))
        _print_json(result)
        return 0 if result["ok"] else 2

    if args.command == "capture-run":
        commands = [parse_command(value) for value in args.inline_commands]
        if not commands:
            commands = get_command_preset(args.preset or args.mode)
        _print_json(
            capture_run(
                root=args.root,
                mode=args.mode,
                commands=commands,
                decision_time=args.decision_time,
                timeout_seconds=args.timeout_seconds,
                sandbox=args.sandbox,
            )
        )
        return 0

    if args.command == "build-outcome":
        outcome_path = build_outcome(args.run_dir, horizon=args.horizon, price_source=args.price_source)
        _print_json({"status": "ok", "outcome_path": str(outcome_path), "safety": SAFETY_DECLARATION})
        return 0

    if args.command == "evaluate-run":
        _print_json(evaluate_run(args.run_dir, horizon=args.horizon))
        return 0

    if args.command == "register-candidate":
        _print_json(register_candidate(args.registry, _read_json(args.candidate), confirm_promote=args.confirm_promote))
        return 0

    if args.command == "doctor":
        _print_json(doctor())
        return 0

    if args.command == "loop":
        _print_json(
            run_agent_loop(
                preset=args.preset,
                horizon=args.horizon,
                agent_trigger=args.agent_trigger,
            )
        )
        return 0

    if args.command == "mentor-fit":
        _print_json(build_mentor_fit(_read_json(args.input)))
        return 0

    if args.command == "self-evolve":
        result = run_self_evolve(
            input_csv=args.input_csv,
            max_iterations=args.max_iterations,
            time_budget_min=args.time_budget_min,
            horizon=args.horizon,
            state_root=args.state_root,
            resume=args.resume,
        )
        if args.interactive_confirm and result.get("promotion_status") == "promotion_recommended":
            sys.stderr.write("Promotion recommended. Enter promote, defer, or reject: ")
            decision = input().strip().lower()
            sys.stderr.write("Optional note: ")
            note = input()
            packet_path = Path(args.state_root) / str(result["loop_id"]) / "promotion_packet.json"
            result["confirmation"] = confirm_promotion(packet_path, decision=decision, note=note)
        _print_json(result)
        return 0

    if args.command == "confirm-promotion":
        _print_json(confirm_promotion(args.promotion_packet, decision=args.decision, note=args.note))
        return 0

    if args.command == "privacy-audit":
        _print_json(privacy_audit())
        return 0

    if args.command == "tradingagents-doctor":
        _print_json(check_tradingagents_environment())
        return 0

    if args.command == "tradingagents-ingest":
        try:
            result = ingest_tradingagents_report(
                report=args.report,
                ticker=args.ticker,
                analysis_date=args.analysis_date,
            )
        except FileNotFoundError as exc:
            result = {
                "status": "error",
                "error": {"code": "report_missing", "message": str(exc)},
                "safety": SAFETY_DECLARATION,
            }
            _print_json(result)
            return 2
        if args.output:
            _write_json(Path(args.output), result)
            result["output"] = str(Path(args.output))
        _print_json(result)
        return 0

    if args.command == "tradingagents-run":
        result = run_tradingagents_local_bridge(
            ticker=args.ticker,
            analysis_date=args.analysis_date,
            allow_network=args.allow_network,
            ack_external_llm=args.ack_external_llm,
            provider=args.provider,
            deep_model=args.deep_model,
            quick_model=args.quick_model,
            max_debate_rounds=args.max_debate_rounds,
        )
        if args.output and result.get("status") == "ok":
            _write_json(Path(args.output), result)
            result["output"] = str(Path(args.output))
        _print_json(result)
        return 0 if result.get("status") == "ok" else 2

    if args.command == "inspect-artifacts":
        _print_json(inspect_run_artifacts(args.run_dir))
        return 0

    if args.command == "collect-case":
        _print_json(collect_offline_case(args.run_dir, output_path=args.output))
        return 0

    if args.command == "append-ledger":
        payload_path = Path(args.payload_json)
        ledger_path = Path(args.ledger) if args.ledger else payload_path.with_name("evolution_ledger.jsonl")
        _print_json(append_ledger_event(ledger_path, args.event, load_payload_json(payload_path)))
        return 0

    if args.command == "save-memory":
        _print_json(save_memory_record(args.case_record, output_path=args.output))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
