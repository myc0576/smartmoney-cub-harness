from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

from smartmoney_cub_harness import __version__
from smartmoney_cub_harness.evidence_pack import build_evidence_pack, replay_evidence_pack
from smartmoney_cub_harness.evaluator import evaluate_decision
from smartmoney_cub_harness.loop import run_agent_loop
from smartmoney_cub_harness.manifest import validate_run_manifest
from smartmoney_cub_harness.mentor_fit import build_mentor_fit
from smartmoney_cub_harness.outcome import build_outcome
from smartmoney_cub_harness.registry import register_candidate
from smartmoney_cub_harness.run_capture import capture_run, get_command_preset, parse_command
from smartmoney_cub_harness.run_envelope import validate_run_envelope
from smartmoney_cub_harness.safety import redact
from smartmoney_cub_harness.schemas import SAFETY_DECLARATION


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
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
        "safety": SAFETY_DECLARATION,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="smcub",
        description="Read-only trading companion harness for decision logging, outcome review, and rule evolution.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-manifest", help="Validate a run manifest JSON file")
    validate.add_argument("manifest")

    validate_envelope = sub.add_parser("validate-envelope", help="Validate a run envelope JSON file")
    validate_envelope.add_argument("envelope")

    capture = sub.add_parser("capture-run", help="Run offline commands and save replay artifacts")
    capture.add_argument("--root", default=".")
    capture.add_argument("--mode", required=True, choices=["intraday", "after-close"])
    capture.add_argument("--preset", choices=["toy", "after-close"])
    capture.add_argument("--command", dest="inline_commands", action="append", default=[])
    capture.add_argument("--decision-time")
    capture.add_argument("--timeout-seconds", type=int, default=300)
    capture.add_argument("--sandbox", action="store_true")
    capture.add_argument("--agent-name", default="external-agent")
    capture.add_argument("--agent-version")
    capture.add_argument("--agent-interface", default="command")

    build_evidence = sub.add_parser(
        "build-evidence-pack", help="Freeze offline runs into a replayable evidence pack"
    )
    build_evidence.add_argument("output_dir")
    build_evidence.add_argument("--sample", dest="sample_dirs", action="append", required=True)
    build_evidence.add_argument("--rule-candidate", required=True)
    build_evidence.add_argument("--horizon", choices=["d1", "d3"], default="d1")

    replay_evidence = sub.add_parser(
        "replay-evidence-pack", help="Verify and replay a frozen evidence pack"
    )
    replay_evidence.add_argument("pack_dir")

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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate-manifest":
        result = validate_run_manifest(_read_json(args.manifest))
        _print_json(result)
        return 0 if result["ok"] else 2

    if args.command == "validate-envelope":
        result = validate_run_envelope(_read_json(args.envelope))
        _print_json(result)
        return 0 if result["valid"] else 2

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
                agent_name=args.agent_name,
                agent_version=args.agent_version,
                agent_interface=args.agent_interface,
            )
        )
        return 0

    if args.command == "build-evidence-pack":
        result = build_evidence_pack(
            args.output_dir,
            args.sample_dirs,
            _read_json(args.rule_candidate),
            horizon=args.horizon,
        )
        _print_json(result)
        return 0

    if args.command == "replay-evidence-pack":
        result = replay_evidence_pack(args.pack_dir)
        _print_json(result)
        return 0 if result.get("evidence_status") == "verified" else 2

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

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
