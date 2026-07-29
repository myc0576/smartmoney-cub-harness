"""CLI extension for the plugin host: ``smcub plugin ...`` and ``smcub analyze``.

This module keeps plugin-related argparse wiring out of the main ``cli.py``
so that all existing commands remain untouched and fully compatible.

Safety: READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE. Nothing in this module places,
cancels, or modifies orders. Plugins only produce review-only evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from smartmoney_cub.plugins import installer, manager, runner
from smartmoney_cub.plugins.exceptions import PluginError
from smartmoney_cub.plugins.protocol import build_analysis_request
from smartmoney_cub.safety import redact
from smartmoney_cub.schemas import SAFETY_DECLARATION


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(redact(payload), ensure_ascii=False, indent=2))


def _error_payload(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, PluginError):
        payload = exc.to_payload()
    else:
        payload = {
            "status": "error",
            "error": {"code": "unexpected_error", "message": str(exc)},
        }
    payload.setdefault("safety", SAFETY_DECLARATION)
    return payload


def add_plugin_arguments(sub: argparse._SubParsersAction) -> None:
    """Register ``plugin`` and ``analyze`` subcommands on the main parser."""
    plugin = sub.add_parser("plugin", help="Manage optional third-party analysis plugins")
    plugin_sub = plugin.add_subparsers(dest="plugin_command", required=True)

    plugin_sub.add_parser("list", help="List catalog plugins with install and readiness status")

    info = plugin_sub.add_parser("info", help="Show manifest, status, and setup steps for one plugin")
    info.add_argument("plugin_id")

    install = plugin_sub.add_parser("install", help="Install a plugin into its isolated virtualenv")
    install.add_argument("plugin_id")
    install.add_argument("--yes", action="store_true", help="Confirm installation non-interactively")
    install.add_argument("--allow-network", action="store_true", help="Allow network access for installation")
    install.add_argument("--ack-third-party", action="store_true", help="Acknowledge third-party code execution")
    install.add_argument(
        "--ack-model-download",
        action="store_true",
        help="Acknowledge large model weight downloads (required by model plugins)",
    )
    install.add_argument("--upgrade", action="store_true", help="Upgrade if already installed")

    update = plugin_sub.add_parser("update", help="Update an installed plugin inside its virtualenv")
    update.add_argument("plugin_id")
    update.add_argument("--yes", action="store_true")
    update.add_argument("--allow-network", action="store_true")
    update.add_argument("--ack-third-party", action="store_true")
    update.add_argument("--ack-model-download", action="store_true")

    uninstall = plugin_sub.add_parser(
        "uninstall",
        help="Remove a plugin virtualenv and caches (user analysis results are preserved)",
    )
    uninstall.add_argument("plugin_id")
    uninstall.add_argument("--yes", action="store_true", help="Confirm uninstall non-interactively")

    enable = plugin_sub.add_parser("enable", help="Enable an installed plugin")
    enable.add_argument("plugin_id")

    disable = plugin_sub.add_parser("disable", help="Disable a plugin without uninstalling it")
    disable.add_argument("plugin_id")

    doctor = plugin_sub.add_parser("doctor", help="Diagnose plugin readiness (never prints credential values)")
    doctor.add_argument("plugin_id", nargs="?", default=None)

    configure = plugin_sub.add_parser(
        "configure",
        help="Set a non-sensitive config key for a plugin (credentials must use environment variables)",
    )
    configure.add_argument("plugin_id")
    configure.add_argument("--key", required=True)
    configure.add_argument("--value", required=True)

    analyze = sub.add_parser(
        "analyze",
        help="Run review-only multi-plugin analysis and aggregate independent evidence packets",
    )
    analyze.add_argument("--target", required=True, help="Symbol, e.g. 600519.SS")
    analyze.add_argument("--target-type", choices=["stock", "index", "sector"], default="stock")
    analyze.add_argument("--market", default="CN")
    analyze.add_argument(
        "--horizon", choices=["intraday", "d1", "d3", "d5", "d10", "d20"], default="d5"
    )
    analyze.add_argument("--data-provider", default=None, help="Data provider plugin id, e.g. akshare")
    analyze.add_argument(
        "--plugins", default="", help="Comma-separated analysis plugin ids, e.g. tradingagents,chronos2"
    )
    analyze.add_argument("--as-of", default=None, help="Analysis reference date (YYYY-MM-DD)")
    analyze.add_argument("--allow-network", action="store_true", help="Allow plugins to access the network")
    analyze.add_argument("--ack-third-party", action="store_true", help="Acknowledge third-party analysis output")
    analyze.add_argument("--output", default=None, help="Optional path to write the aggregated JSON report")


def handle_plugin_command(args: argparse.Namespace) -> int:
    """Dispatch ``smcub plugin ...``. Returns process exit code."""
    try:
        cmd = args.plugin_command
        if cmd == "list":
            _print_json(manager.list_plugins())
            return 0
        if cmd == "info":
            _print_json(manager.plugin_info(args.plugin_id))
            return 0
        if cmd == "install":
            result = installer.install_plugin(
                args.plugin_id,
                yes=args.yes,
                allow_network=args.allow_network,
                ack_third_party=args.ack_third_party,
                ack_model_download=args.ack_model_download,
                upgrade=args.upgrade,
            )
            _print_json(result)
            return 0 if result.get("status") == "ok" else 2
        if cmd == "update":
            result = installer.update_plugin(
                args.plugin_id,
                yes=args.yes,
                allow_network=args.allow_network,
                ack_third_party=args.ack_third_party,
                ack_model_download=args.ack_model_download,
            )
            _print_json(result)
            return 0 if result.get("status") == "ok" else 2
        if cmd == "uninstall":
            result = installer.uninstall_plugin(args.plugin_id, yes=args.yes)
            _print_json(result)
            return 0 if result.get("status") == "ok" else 2
        if cmd == "enable":
            _print_json(manager.set_enabled(args.plugin_id, True))
            return 0
        if cmd == "disable":
            _print_json(manager.set_enabled(args.plugin_id, False))
            return 0
        if cmd == "doctor":
            _print_json(manager.plugin_doctor(args.plugin_id))
            return 0
        if cmd == "configure":
            result = manager.configure_plugin(args.plugin_id, args.key, args.value)
            _print_json(result)
            return 0 if result.get("status") == "ok" else 2
    except PluginError as exc:
        _print_json(_error_payload(exc))
        return 2
    _print_json(
        {
            "status": "error",
            "error": {"code": "unknown_plugin_command", "message": str(args.plugin_command)},
            "safety": SAFETY_DECLARATION,
        }
    )
    return 2


def handle_analyze_command(args: argparse.Namespace) -> int:
    """Dispatch ``smcub analyze``. Returns process exit code."""
    plugin_ids = [item.strip() for item in str(args.plugins).split(",") if item.strip()]
    if not args.ack_third_party and (plugin_ids or args.data_provider):
        _print_json(
            {
                "status": "error",
                "error": {
                    "code": "consent_required",
                    "message": "analysis uses third-party plugins; re-run with --ack-third-party",
                },
                "required_flags": ["--ack-third-party"],
                "safety": SAFETY_DECLARATION,
            }
        )
        return 2
    try:
        request = build_analysis_request(
            symbol=args.target,
            target_type=args.target_type,
            market=args.market,
            horizon=args.horizon,
            data_provider=args.data_provider,
            plugins=plugin_ids,
            as_of=args.as_of,
            network_allowed=args.allow_network,
        )
        report = runner.run_analysis(request)
    except PluginError as exc:
        _print_json(_error_payload(exc))
        return 2
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(redact(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        report["output"] = str(output_path)
    _print_json(report)
    if report.get("status") == "error":
        return 2
    return 0
