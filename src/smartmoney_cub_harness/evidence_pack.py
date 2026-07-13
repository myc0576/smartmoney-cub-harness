from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from smartmoney_cub_harness.evaluator import evaluate_decision
from smartmoney_cub_harness.manifest import validate_run_manifest
from smartmoney_cub_harness.registry import promotion_blockers
from smartmoney_cub_harness.safety import safety_envelope
from smartmoney_cub_harness.schemas import EVIDENCE_PACK_SCHEMA, EVIDENCE_REPLAY_SCHEMA, SAFETY_DECLARATION


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _write_frozen(path: Path, payload: dict[str, Any]) -> str:
    frozen = safety_envelope(payload)
    frozen["safety"] = SAFETY_DECLARATION
    content = _canonical_bytes(frozen)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path.name}")
    return value


def _stable_sample_id(manifest: dict[str, Any], index: int) -> str:
    run_id = str(manifest.get("run_id") or f"sample-{index + 1}")
    safe = "".join(character if character.isalnum() or character in "-_" else "-" for character in run_id)
    return safe.strip("-") or f"sample-{index + 1}"


def _review_status(failure_count: int, trailing_failures: int, metrics: dict[str, Any]) -> str:
    if trailing_failures >= 3:
        return "blocked"
    if failure_count:
        return "pending_review"
    return "challenger" if promotion_blockers(metrics) else "ready_for_review"

def build_evidence_pack(
    output_dir: str | Path,
    sample_dirs: list[str | Path],
    rule_candidate: dict[str, Any],
    horizon: str = "d1",
) -> dict[str, Any]:
    if not sample_dirs:
        raise ValueError("evidence pack requires at least one sample")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    sample_records: list[dict[str, Any]] = []
    score_totals = {"false_alert": 0, "missed_opportunity": 0, "risk_contract_violation": 0}
    future_leakage_count = 0
    failures: list[bool] = []

    rule_path = "rule_candidate.json"
    hashes[rule_path] = _write_frozen(output_path / rule_path, rule_candidate)

    used_ids: set[str] = set()
    for index, source_dir in enumerate(sample_dirs):
        source = Path(source_dir)
        manifest = _read_json(source / "run_manifest.json")
        decision = _read_json(source / "decision.json")
        outcome = _read_json(source / f"outcome_{horizon}.json")
        manifest_validation = validate_run_manifest(manifest)
        evaluation = evaluate_decision(decision, outcome)
        sample_id = _stable_sample_id(manifest, index)
        if sample_id in used_ids:
            sample_id = f"{sample_id}-{index + 1}"
        used_ids.add(sample_id)

        prefix = f"samples/{sample_id}"
        paths = {
            "manifest": f"{prefix}/run_manifest.json",
            "decision": f"{prefix}/decision.json",
            "outcome": f"{prefix}/outcome_{horizon}.json",
            "evaluation": f"{prefix}/evaluation.json",
        }
        frozen_payloads = {
            "manifest": manifest,
            "decision": decision,
            "outcome": outcome,
            "evaluation": evaluation,
        }
        for name, relative_path in paths.items():
            hashes[relative_path] = _write_frozen(output_path / relative_path, frozen_payloads[name])

        scores = evaluation.get("scores") or {}
        for score_name in score_totals:
            score_totals[score_name] += int(scores.get(score_name) or 0)
        future_leakage_count += sum(
            1 for error in manifest_validation.get("errors", []) if str(error).startswith("future_leakage:")
        )
        failed = not manifest_validation.get("ok") or evaluation.get("grade") in {"invalid", "not_evaluated"}
        failures.append(bool(failed))
        sample_records.append(
            safety_envelope(
                {
                    "sample_id": sample_id,
                    "paths": paths,
                    "manifest_validation": manifest_validation,
                    "evaluation_grade": evaluation.get("grade"),
                    "failed": bool(failed),
                }
            )
        )

    sample_count = len(sample_records)
    metrics = {
        "sample_count": sample_count,
        "false_alert_rate": score_totals["false_alert"] / sample_count,
        "missed_opportunity_rate": score_totals["missed_opportunity"] / sample_count,
        "future_leakage_count": future_leakage_count,
        "risk_contract_violation_rate": score_totals["risk_contract_violation"] / sample_count,
    }
    trailing_failures = 0
    for failed in reversed(failures):
        if not failed:
            break
        trailing_failures += 1
    failure_count = sum(failures)
    review_status = _review_status(failure_count, trailing_failures, metrics)
    pack = safety_envelope(
        {
            "schema": EVIDENCE_PACK_SCHEMA,
            "horizon": horizon,
            "rule_candidate_path": rule_path,
            "samples": sample_records,
            "hashes": hashes,
            "metrics": metrics,
            "failure_count": failure_count,
            "trailing_consecutive_failure_count": trailing_failures,
            "review_status": review_status,
            "promotion_gate": {
                "eligible_for_human_review": review_status == "ready_for_review",
                "human_confirmation_required": True,
                "champion_mutated": False,
                "core_rules_mutated": False,
            },
        }
    )
    (output_path / "evidence_pack.json").write_bytes(_canonical_bytes(pack))
    return pack


def replay_evidence_pack(pack_dir: str | Path) -> dict[str, Any]:
    root = Path(pack_dir)
    pack = _read_json(root / "evidence_pack.json")
    hash_mismatches: list[str] = []
    result_mismatches: list[str] = []

    for relative_path, expected_hash in (pack.get("hashes") or {}).items():
        artifact = _relative_artifact(root, str(relative_path))
        if not artifact.is_file() or hashlib.sha256(artifact.read_bytes()).hexdigest() != expected_hash:
            hash_mismatches.append(str(relative_path))

    score_totals = {"false_alert": 0, "missed_opportunity": 0, "risk_contract_violation": 0}
    future_leakage_count = 0
    failures: list[bool] = []
    replayed_samples: list[dict[str, Any]] = []
    for sample in pack.get("samples") or []:
        sample_id = str(sample.get("sample_id") or "unknown")
        paths = sample.get("paths") or {}
        try:
            manifest = _read_json(_relative_artifact(root, str(paths["manifest"])))
            decision = _read_json(_relative_artifact(root, str(paths["decision"])))
            outcome = _read_json(_relative_artifact(root, str(paths["outcome"])))
            frozen_evaluation = _read_json(_relative_artifact(root, str(paths["evaluation"])))
            manifest_validation = validate_run_manifest(manifest)
            evaluation = evaluate_decision(decision, outcome)
            mismatched = False
            if safety_envelope(evaluation) != frozen_evaluation:
                result_mismatches.append(f"evaluation:{sample_id}")
                mismatched = True
            if manifest_validation != sample.get("manifest_validation"):
                result_mismatches.append(f"manifest_validation:{sample_id}")
                mismatched = True
            scores = evaluation.get("scores") or {}
            for score_name in score_totals:
                score_totals[score_name] += int(scores.get(score_name) or 0)
            future_leakage_count += sum(
                1 for error in manifest_validation.get("errors", []) if str(error).startswith("future_leakage:")
            )
            failed = (
                not manifest_validation.get("ok")
                or evaluation.get("grade") in {"invalid", "not_evaluated"}
                or mismatched
                or any(str(path).startswith(f"samples/{sample_id}/") for path in hash_mismatches)
            )
        except (KeyError, OSError, ValueError, json.JSONDecodeError):
            result_mismatches.append(f"unreadable_sample:{sample_id}")
            failed = True
        failures.append(bool(failed))
        replayed_samples.append(safety_envelope({"sample_id": sample_id, "failed": bool(failed)}))

    sample_count = len(replayed_samples)
    if sample_count == 0:
        raise ValueError("evidence pack requires at least one sample")
    metrics = {
        "sample_count": sample_count,
        "false_alert_rate": score_totals["false_alert"] / sample_count,
        "missed_opportunity_rate": score_totals["missed_opportunity"] / sample_count,
        "future_leakage_count": future_leakage_count,
        "risk_contract_violation_rate": score_totals["risk_contract_violation"] / sample_count,
    }
    if metrics != pack.get("metrics"):
        result_mismatches.append("metrics")
    trailing_failures = 0
    for failed in reversed(failures):
        if not failed:
            break
        trailing_failures += 1
    failure_count = sum(failures)
    if failure_count != pack.get("failure_count"):
        result_mismatches.append("failure_count")
    if trailing_failures != pack.get("trailing_consecutive_failure_count"):
        result_mismatches.append("trailing_consecutive_failure_count")

    mismatched = bool(hash_mismatches or result_mismatches)
    if trailing_failures >= 3:
        evidence_status = "blocked"
    elif failure_count or mismatched:
        evidence_status = "pending_review"
    else:
        evidence_status = "verified"
    report = safety_envelope(
        {
            "schema": EVIDENCE_REPLAY_SCHEMA,
            "evidence_status": evidence_status,
            "hash_mismatches": hash_mismatches,
            "result_mismatches": result_mismatches,
            "metrics": metrics,
            "failure_count": failure_count,
            "trailing_consecutive_failure_count": trailing_failures,
            "samples": replayed_samples,
            "promotion_gate": {
                "eligible_for_human_review": (
                    evidence_status == "verified"
                    and failure_count == 0
                    and not promotion_blockers(metrics)
                ),
                "human_confirmation_required": True,
                "champion_mutated": False,
                "core_rules_mutated": False,
            },
        }
    )
    (root / "replay_report.json").write_bytes(_canonical_bytes(report))
    return report


def _relative_artifact(root: Path, relative_path: str) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("evidence artifacts must use relative paths")
    return root / relative
