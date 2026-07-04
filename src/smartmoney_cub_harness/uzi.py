from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from smartmoney_cub_harness.manifest import validate_run_manifest
from smartmoney_cub_harness.run_capture import now_iso, safe_name, unique_run_dir
from smartmoney_cub_harness.safety import redact
from smartmoney_cub_harness.schemas import (
    DECISION_SCHEMA,
    MANIFEST_SCHEMA,
    SAFETY_DECLARATION,
    VALID_ACTION_LABELS,
)

UZI_REPO_URL = "https://github.com/wbh604/UZI-Skill.git"
DEFAULT_UZI_PATH = Path("state") / "plugins" / "uzi-skill"
INSTALL_STATE_FILE = ".smcub_uzi_install.json"
UZI_SOURCE_NAME = "uzi_skill_short_horizon"
UZI_ADAPTER_VERSION = "uzi_skill_adapter_v0.1"


def _root_path(root: str | Path) -> Path:
    return Path(root).expanduser().resolve()


def resolve_uzi_path(root: str | Path = ".", path: str | Path | None = None) -> Path:
    candidate = Path(path) if path is not None else DEFAULT_UZI_PATH
    if candidate.is_absolute():
        return candidate.expanduser().resolve()
    return (_root_path(root) / candidate).resolve()


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(redact(str(path)))


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_json(path: Path, payload: dict[str, Any], *, redact_payload: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stored = redact(payload) if redact_payload else payload
    path.write_text(json.dumps(stored, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run(args: list[str], cwd: Path, timeout_seconds: int | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )


def _git_value(plugin_path: Path, *args: str) -> str | None:
    if not (plugin_path / ".git").exists() or shutil.which("git") is None:
        return None
    result = _run(["git", *args], cwd=plugin_path, timeout_seconds=10)
    value = result.stdout.strip()
    return value or None if result.returncode == 0 else None


def _read_uzi_version(plugin_path: Path) -> str | None:
    state = _read_json(plugin_path / INSTALL_STATE_FILE) or {}
    if state.get("version"):
        return str(state["version"])
    manifest = _read_json(plugin_path / ".claude-plugin" / "plugin.json") or {}
    if manifest.get("version"):
        return str(manifest["version"])
    skill = plugin_path / "SKILL.md"
    if skill.exists():
        try:
            for line in skill.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip().startswith("version:"):
                    return line.split(":", 1)[1].strip()
        except OSError:
            return None
    return None


def _venv_python(plugin_path: Path) -> Path | None:
    windows = plugin_path / ".venv" / "Scripts" / "python.exe"
    posix = plugin_path / ".venv" / "bin" / "python"
    if windows.exists():
        return windows
    if posix.exists():
        return posix
    return None


def _plugin_python(plugin_path: Path) -> Path | None:
    state = _read_json(plugin_path / INSTALL_STATE_FILE) or {}
    stored = state.get("python_path")
    if isinstance(stored, str) and stored:
        candidate = Path(stored)
        if candidate.exists():
            return candidate
    venv = _venv_python(plugin_path)
    if venv is not None:
        return venv
    if (plugin_path / "run.py").exists():
        return Path(sys.executable)
    return None


def uzi_status(root: str | Path = ".", path: str | Path | None = None) -> dict[str, Any]:
    root_path = _root_path(root)
    plugin_path = resolve_uzi_path(root_path, path)
    state = _read_json(plugin_path / INSTALL_STATE_FILE) or {}
    run_py = plugin_path / "run.py"
    python_path = _plugin_python(plugin_path)
    installed = run_py.exists() and python_path is not None
    commit = state.get("commit") or _git_value(plugin_path, "rev-parse", "HEAD")
    version = _read_uzi_version(plugin_path) or "unknown"
    status = "installed" if installed else "requires_integration"
    if run_py.exists() and python_path is None:
        status = "needs_repair"

    return {
        "status": status,
        "installed": installed,
        "plugin": "uzi-skill",
        "repo_url": UZI_REPO_URL,
        "path": _relative(plugin_path, root_path),
        "version": version,
        "commit": commit or "unknown",
        "python": str(redact(str(python_path))) if python_path is not None else None,
        "venv_present": _venv_python(plugin_path) is not None,
        "install_state_present": bool(state),
        "network_required": False,
        "scan_network_required": True,
        "install_command": "smcub uzi-install",
        "scan_command": "smcub uzi-scan <symbol>",
        "safety": SAFETY_DECLARATION,
    }


def uzi_install(
    root: str | Path = ".",
    path: str | Path | None = None,
    ref: str = "main",
    repo_url: str = UZI_REPO_URL,
    timeout_seconds: int = 1800,
) -> dict[str, Any]:
    root_path = _root_path(root)
    plugin_path = resolve_uzi_path(root_path, path)
    existing_status = uzi_status(root_path, plugin_path)
    if existing_status["installed"]:
        return {
            **existing_status,
            "status": "already_installed",
            "requested_ref": ref,
            "safety": SAFETY_DECLARATION,
        }
    if plugin_path.exists() and any(plugin_path.iterdir()):
        return {
            "status": "error",
            "reason": "target_path_exists_but_is_not_a_valid_uzi_install",
            "path": _relative(plugin_path, root_path),
            "safety": SAFETY_DECLARATION,
        }
    if shutil.which("git") is None:
        return {
            "status": "error",
            "reason": "git_not_found",
            "path": _relative(plugin_path, root_path),
            "safety": SAFETY_DECLARATION,
        }

    plugin_path.parent.mkdir(parents=True, exist_ok=True)
    clone = _run(
        ["git", "clone", "--depth", "1", "--branch", ref, repo_url, str(plugin_path)],
        cwd=root_path,
        timeout_seconds=timeout_seconds,
    )
    if clone.returncode != 0:
        return {
            "status": "error",
            "reason": "git_clone_failed",
            "returncode": clone.returncode,
            "stdout": redact(clone.stdout or ""),
            "stderr": redact(clone.stderr or ""),
            "path": _relative(plugin_path, root_path),
            "safety": SAFETY_DECLARATION,
        }

    venv_dir = plugin_path / ".venv"
    venv = _run([sys.executable, "-m", "venv", str(venv_dir)], cwd=plugin_path, timeout_seconds=timeout_seconds)
    if venv.returncode != 0:
        return {
            "status": "error",
            "reason": "venv_create_failed",
            "returncode": venv.returncode,
            "stdout": redact(venv.stdout or ""),
            "stderr": redact(venv.stderr or ""),
            "path": _relative(plugin_path, root_path),
            "safety": SAFETY_DECLARATION,
        }

    python_path = _venv_python(plugin_path)
    if python_path is None:
        return {
            "status": "error",
            "reason": "venv_python_not_found",
            "path": _relative(plugin_path, root_path),
            "safety": SAFETY_DECLARATION,
        }

    pip_install = _run(
        [str(python_path), "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=plugin_path,
        timeout_seconds=timeout_seconds,
    )
    if pip_install.returncode != 0:
        return {
            "status": "error",
            "reason": "pip_install_failed",
            "returncode": pip_install.returncode,
            "stdout": redact(pip_install.stdout or ""),
            "stderr": redact(pip_install.stderr or ""),
            "path": _relative(plugin_path, root_path),
            "safety": SAFETY_DECLARATION,
        }

    commit = _git_value(plugin_path, "rev-parse", "HEAD") or "unknown"
    version = _read_uzi_version(plugin_path) or "unknown"
    state = {
        "repo_url": repo_url,
        "ref": ref,
        "commit": commit,
        "version": version,
        "python_path": str(python_path.resolve()),
        "installed_at": now_iso(),
        "safety": SAFETY_DECLARATION,
    }
    _write_json(plugin_path / INSTALL_STATE_FILE, state, redact_payload=False)
    return {
        "status": "installed",
        "plugin": "uzi-skill",
        "repo_url": repo_url,
        "ref": ref,
        "commit": commit,
        "version": version,
        "path": _relative(plugin_path, root_path),
        "python": str(redact(str(python_path))),
        "network_required": True,
        "safety": SAFETY_DECLARATION,
    }


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _normalize_timestamp(value: Any, fallback: str) -> str:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return fallback
    return parsed.isoformat(timespec="seconds")


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
        if match:
            return float(match.group(0))
    return None


def _nested(payload: dict[str, Any] | None, keys: tuple[str, ...]) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def derive_invalidation_price(synthesis: dict[str, Any] | None) -> tuple[float | None, str | None]:
    candidates = [
        (("buy_zones", "technical", "price"), "synthesis.buy_zones.technical.price"),
        (("buy_zones", "youzi", "price"), "synthesis.buy_zones.youzi.price"),
    ]
    for keys, source in candidates:
        value = _as_float(_nested(synthesis, keys))
        if value is not None:
            return value, source
    return None, None


def _scripts_dir(plugin_path: Path) -> Path:
    for candidate in (plugin_path / "skills" / "deep-analysis" / "scripts", plugin_path / "scripts"):
        if candidate.exists():
            return candidate
    return plugin_path / "skills" / "deep-analysis" / "scripts"


def _cache_dirs(plugin_path: Path, symbol: str, report_meta: dict[str, Any]) -> list[Path]:
    cache_root = _scripts_dir(plugin_path) / ".cache"
    if not cache_root.exists():
        return []
    names = []
    for value in (symbol, report_meta.get("ticker")):
        if isinstance(value, str) and value and value not in names:
            names.append(value)
    dirs = [cache_root / name for name in names if (cache_root / name).exists()]
    if dirs:
        return dirs

    found: list[Path] = []
    for candidate in cache_root.iterdir():
        if not candidate.is_dir():
            continue
        synthesis = _read_json(candidate / "synthesis.json") or {}
        raw = _read_json(candidate / "raw_data.json") or {}
        tickers = {str(synthesis.get("ticker") or ""), str(raw.get("ticker") or ""), str(raw.get("name") or "")}
        if symbol in tickers or str(report_meta.get("ticker") or "") in tickers:
            found.append(candidate)
    return sorted(found, key=lambda item: item.stat().st_mtime, reverse=True)


def _load_cache_payloads(plugin_path: Path, symbol: str, report_meta: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    for cache_dir in _cache_dirs(plugin_path, symbol, report_meta):
        payloads: dict[str, dict[str, Any]] = {}
        paths: dict[str, str] = {}
        for name in ("synthesis", "panel", "raw_data"):
            path = cache_dir / f"{name}.json"
            payload = _read_json(path)
            if payload is not None:
                payloads[name] = payload
                paths[name] = path.name
        if payloads:
            return payloads, paths
    return {}, {}


def _move_report(temp_report: Path, artifact_report: Path) -> None:
    artifact_report.parent.mkdir(parents=True, exist_ok=True)
    if temp_report.exists():
        shutil.move(str(temp_report), str(artifact_report))
    else:
        artifact_report.mkdir(parents=True, exist_ok=True)


def _run_uzi_command(
    python_path: Path,
    plugin_path: Path,
    symbol: str,
    depth: str,
    output_dir: Path,
    timeout_seconds: int,
    env_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    argv = [
        str(python_path),
        "run.py",
        symbol,
        "--depth",
        depth,
        "--school",
        "F",
        "--no-browser",
        "--output-dir",
        str(output_dir),
    ]
    env = dict(os.environ)
    env.update(
        {
            "UZI_NO_UPDATE_CHECK": "1",
            "UZI_CLI_ONLY": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    env.pop("UZI_XQ_LOGIN", None)
    if env_overrides:
        env.update(env_overrides)

    started_at = now_iso()
    try:
        completed = _run(argv, cwd=plugin_path, timeout_seconds=timeout_seconds, env=env)
        return {
            "argv": argv,
            "started_at": started_at,
            "finished_at": now_iso(),
            "returncode": completed.returncode,
            "stdout": completed.stdout or "",
            "stderr": completed.stderr or "",
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", errors="replace")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", errors="replace")
        return {
            "argv": argv,
            "started_at": started_at,
            "finished_at": now_iso(),
            "returncode": 124,
            "stdout": stdout,
            "stderr": stderr or f"command timed out after {timeout_seconds}s",
            "timed_out": True,
        }


def uzi_scan(
    symbol: str,
    root: str | Path = ".",
    path: str | Path | None = None,
    depth: str = "lite",
    label: str = "WATCH",
    timeout_seconds: int = 900,
    decision_time: str | None = None,
    env_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    if depth not in {"lite", "medium"}:
        raise ValueError("depth must be lite or medium")
    action_label = label.upper()
    if action_label not in {"WATCH", "ALERT", "AVOID"}:
        raise ValueError("label must be WATCH, ALERT, or AVOID")

    root_path = _root_path(root)
    plugin_path = resolve_uzi_path(root_path, path)
    status = uzi_status(root_path, plugin_path)
    if not status["installed"]:
        return {
            "status": "requires_integration",
            "reason": "uzi_skill_not_installed",
            "plugin_status": status,
            "next_step": "ask_user_then_run_smcub_uzi_install",
            "safety": SAFETY_DECLARATION,
        }

    python_path = _plugin_python(plugin_path)
    if python_path is None:
        return {
            "status": "requires_integration",
            "reason": "uzi_python_not_found",
            "plugin_status": status,
            "safety": SAFETY_DECLARATION,
        }

    temp_root = root_path / "tmp" / "uzi_scan_work" / f"{safe_name(symbol)}-{time.time_ns()}"
    temp_report = temp_root / "uzi_report"
    temp_report.mkdir(parents=True, exist_ok=True)
    command_result = _run_uzi_command(
        python_path=python_path,
        plugin_path=plugin_path,
        symbol=symbol,
        depth=depth,
        output_dir=temp_report,
        timeout_seconds=timeout_seconds,
        env_overrides=env_overrides,
    )

    effective_decision_time = decision_time or command_result["finished_at"]
    run_dir = unique_run_dir(root_path, effective_decision_time, "uzi-scan")
    artifact_dir = run_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_report = artifact_dir / "uzi_report"
    _move_report(temp_report, artifact_report)
    try:
        shutil.rmtree(temp_root)
    except OSError:
        pass

    stdout_path = artifact_dir / "uzi.stdout.txt"
    stderr_path = artifact_dir / "uzi.stderr.txt"
    meta_path = artifact_dir / "uzi.meta.json"
    stdout_path.write_text(str(redact(command_result["stdout"])), encoding="utf-8")
    stderr_path.write_text(str(redact(command_result["stderr"])), encoding="utf-8")
    _write_json(
        meta_path,
        {
            "name": UZI_SOURCE_NAME,
            "argv": command_result["argv"],
            "started_at": command_result["started_at"],
            "finished_at": command_result["finished_at"],
            "returncode": command_result["returncode"],
            "timed_out": command_result["timed_out"],
            "uzi_path": str(plugin_path),
            "safety": SAFETY_DECLARATION,
        },
    )

    report_meta_path = artifact_report / "report.meta.json"
    report_meta = _read_json(report_meta_path) or {}
    if report_meta:
        report_meta["report_dir"] = _relative(artifact_report, run_dir)
        report_meta["artifact_index"] = _relative(artifact_report / "index.html", run_dir)
    if report_meta_path.exists():
        _write_json(report_meta_path, report_meta)
    one_liner_path = artifact_report / "one-liner.txt"
    one_liner = ""
    if one_liner_path.exists():
        try:
            one_liner = one_liner_path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            one_liner = ""

    cache_payloads, cache_paths = _load_cache_payloads(plugin_path, symbol, report_meta)
    cache_artifacts: dict[str, str] = {}
    for name, payload in cache_payloads.items():
        target = artifact_dir / f"uzi_{name}.json"
        _write_json(target, payload)
        cache_artifacts[name] = _relative(target, run_dir)

    synthesis = cache_payloads.get("synthesis")
    invalidation_price, invalidation_source = derive_invalidation_price(synthesis)
    source_available_at = _normalize_timestamp(report_meta.get("generated_at"), command_result["finished_at"])
    source_quality = "ok" if int(command_result["returncode"] or 0) == 0 else "error"
    if source_quality == "ok" and invalidation_price is None:
        source_quality = "partial"

    observation = {
        "schema": "smartmoney_cub_uzi_observation.v1",
        "symbol": symbol,
        "depth": depth,
        "school": "F",
        "requested_label": action_label,
        "read_only": True,
        "network_required": True,
        "execution_integrations": "disabled",
        "uzi_repo_url": UZI_REPO_URL,
        "uzi_version": status.get("version", "unknown"),
        "uzi_commit": status.get("commit", "unknown"),
        "report_meta": report_meta,
        "one_liner": one_liner,
        "cache_files_seen": cache_paths,
        "cache_artifacts": cache_artifacts,
        "invalidation_price": invalidation_price,
        "invalidation_source": invalidation_source,
        "safety": SAFETY_DECLARATION,
    }
    observation_path = artifact_dir / "uzi_observation.json"
    _write_json(observation_path, observation)

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "run_id": run_dir.name,
        "decision_time": effective_decision_time,
        "mode": "intraday",
        "safety": SAFETY_DECLARATION,
        "selection_system_version": UZI_ADAPTER_VERSION,
        "selection_system_refs": [
            "https://github.com/wbh604/UZI-Skill",
            "docs/harness-contract.md",
        ],
        "network_required": True,
        "data_sources": [
            {
                "name": UZI_SOURCE_NAME,
                "fetch_time": source_available_at,
                "available_at": source_available_at,
                "data_quality_flag": source_quality,
                "artifact_stdout": _relative(stdout_path, run_dir),
                "artifact_stderr": _relative(stderr_path, run_dir),
                "artifact_meta": _relative(meta_path, run_dir),
                "artifact_observation": _relative(observation_path, run_dir),
                "artifact_report_index": _relative(artifact_report / "index.html", run_dir),
                "artifact_report_meta": _relative(report_meta_path, run_dir),
                "uzi_repo_url": UZI_REPO_URL,
                "uzi_version": status.get("version", "unknown"),
                "uzi_commit": status.get("commit", "unknown"),
            }
        ],
    }
    manifest_validation = validate_run_manifest(manifest)

    if int(command_result["returncode"] or 0) != 0:
        decision = {
            "schema": DECISION_SCHEMA,
            "run_id": run_dir.name,
            "decision_time": effective_decision_time,
            "mode": "intraday",
            "action_label": "ERROR",
            "failed_sources": [UZI_SOURCE_NAME],
            "error_reason": "uzi_command_failed",
            "safety": SAFETY_DECLARATION,
        }
    elif invalidation_price is None:
        decision = {
            "schema": DECISION_SCHEMA,
            "run_id": run_dir.name,
            "decision_time": effective_decision_time,
            "mode": "intraday",
            "action_label": "ERROR",
            "failed_sources": [UZI_SOURCE_NAME],
            "error_reason": "missing_derived_invalidation_price",
            "data_source": UZI_SOURCE_NAME,
            "available_at": source_available_at,
            "data_quality_flag": source_quality,
            "safety": SAFETY_DECLARATION,
        }
    else:
        decision = {
            "schema": DECISION_SCHEMA,
            "run_id": run_dir.name,
            "decision_time": effective_decision_time,
            "mode": "intraday",
            "action_label": action_label,
            "signal_sources": [UZI_SOURCE_NAME],
            "symbol": symbol,
            "invalidation_price": invalidation_price,
            "invalidation_source": invalidation_source,
            "time_stop": "D1/D3 review",
            "give_up_conditions": [
                "UZI short-horizon observation loses support in recorded evidence",
                f"price below derived invalidation_price {invalidation_price:.4f}",
                "D1/D3 review invalidates the short-horizon observation",
            ],
            "data_source": UZI_SOURCE_NAME,
            "available_at": source_available_at,
            "data_quality_flag": source_quality,
            "read_only_observation": True,
            "safety": SAFETY_DECLARATION,
        }

    _write_json(run_dir / "run_manifest.json", manifest)
    _write_json(run_dir / "manifest_validation.json", manifest_validation)
    _write_json(run_dir / "decision.json", decision)

    result_status = "ok"
    if not manifest_validation["ok"]:
        result_status = "invalid_manifest"
    if decision["action_label"] == "ERROR":
        result_status = "error"

    return {
        "status": result_status,
        "run_dir": _relative(run_dir, root_path),
        "manifest_path": _relative(run_dir / "run_manifest.json", root_path),
        "decision_path": _relative(run_dir / "decision.json", root_path),
        "observation_path": _relative(observation_path, root_path),
        "report_index": _relative(artifact_report / "index.html", root_path),
        "manifest_validation": manifest_validation,
        "decision": decision,
        "plugin_status": status,
        "network_required": True,
        "safety": SAFETY_DECLARATION,
    }
