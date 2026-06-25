from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

from smartmoney_cub_harness import __version__
from smartmoney_cub_harness.evaluator import evaluate_decision
from smartmoney_cub_harness.manifest import validate_run_manifest
from smartmoney_cub_harness.outcome import build_outcome
from smartmoney_cub_harness.registry import register_candidate
from smartmoney_cub_harness.run_capture import capture_run, get_command_preset, parse_command
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

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
