from __future__ import annotations

import json
import re
from pathlib import Path

from smartmoney_cub_harness.schemas import SAFETY_DECLARATION
from smartmoney_cub_harness.uzi import uzi_scan, uzi_status


ABSOLUTE_PATH_RE = re.compile(r"(?i)([A-Z]:\\|/Users/|/home/)")


def make_fake_uzi(root: Path) -> Path:
    plugin = root / "fake_uzi"
    plugin.mkdir()
    manifest_dir = plugin / ".claude-plugin"
    manifest_dir.mkdir()
    (manifest_dir / "plugin.json").write_text(json.dumps({"version": "9.9.9-test"}), encoding="utf-8")
    (plugin / "run.py").write_text(
        """
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("ticker")
parser.add_argument("--depth")
parser.add_argument("--school")
parser.add_argument("--no-browser", action="store_true")
parser.add_argument("--output-dir", required=True)
args = parser.parse_args()

out = Path(args.output_dir)
out.mkdir(parents=True, exist_ok=True)
generated_at = os.environ.get("FAKE_UZI_GENERATED_AT") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
(out / "index.html").write_text("<html><body>fake uzi report</body></html>", encoding="utf-8")
(out / "one-liner.txt").write_text("fake short-horizon observation", encoding="utf-8")
(out / "report.meta.json").write_text(json.dumps({
    "schema": 1,
    "ticker": args.ticker,
    "depth": args.depth,
    "generated_at": generated_at,
    "report_dir": str(out.resolve()),
    "index": "index.html",
    "one_liner": "fake short-horizon observation",
}, ensure_ascii=False), encoding="utf-8")

buy_zones = {}
if os.environ.get("FAKE_UZI_NO_INVALIDATION") != "1":
    if os.environ.get("FAKE_UZI_NO_TECHNICAL") != "1":
        buy_zones["technical"] = {"price": "9.87"}
    buy_zones["youzi"] = {"price": 8.88}

cache = Path(__file__).parent / "skills" / "deep-analysis" / "scripts" / ".cache" / args.ticker
cache.mkdir(parents=True, exist_ok=True)
(cache / "synthesis.json").write_text(json.dumps({
    "ticker": args.ticker,
    "buy_zones": buy_zones,
    "overall_score": 61.2,
}, ensure_ascii=False), encoding="utf-8")
(cache / "panel.json").write_text(json.dumps({"ticker": args.ticker, "panel_consensus": 55.0}), encoding="utf-8")
(cache / "raw_data.json").write_text(json.dumps({"ticker": args.ticker, "dimensions": {}}), encoding="utf-8")
print(json.dumps({"status": "fake-ok", "ticker": args.ticker}, ensure_ascii=False))
""".lstrip(),
        encoding="utf-8",
    )
    return plugin


def read_run_json(root: Path, result: dict, name: str) -> dict:
    return json.loads((root / result["run_dir"] / name).read_text(encoding="utf-8"))


def test_uzi_status_reports_requires_integration_when_missing(tmp_path: Path):
    result = uzi_status(root=tmp_path)

    assert result["status"] == "requires_integration"
    assert result["installed"] is False
    assert result["scan_network_required"] is True
    assert result["safety"] == SAFETY_DECLARATION


def test_uzi_status_reports_installed_fake_repo(tmp_path: Path):
    plugin = make_fake_uzi(tmp_path)

    result = uzi_status(root=tmp_path, path=plugin)

    assert result["status"] == "installed"
    assert result["installed"] is True
    assert result["version"] == "9.9.9-test"
    assert result["safety"] == SAFETY_DECLARATION


def test_uzi_scan_writes_watch_decision_and_uses_technical_invalidation(tmp_path: Path):
    plugin = make_fake_uzi(tmp_path)

    result = uzi_scan(
        "000001.SZ",
        root=tmp_path,
        path=plugin,
        decision_time="2026-07-04T10:31:00+08:00",
        env_overrides={"FAKE_UZI_GENERATED_AT": "2026-07-04T10:30:00+08:00"},
    )

    assert result["status"] == "ok"
    assert result["manifest_validation"]["ok"] is True
    decision = read_run_json(tmp_path, result, "decision.json")
    manifest = read_run_json(tmp_path, result, "run_manifest.json")
    observation = json.loads((tmp_path / result["observation_path"]).read_text(encoding="utf-8"))

    assert decision["action_label"] == "WATCH"
    assert decision["symbol"] == "000001.SZ"
    assert decision["invalidation_price"] == 9.87
    assert decision["invalidation_source"] == "synthesis.buy_zones.technical.price"
    assert decision["time_stop"] == "D1/D3 review"
    assert decision["give_up_conditions"]
    assert decision["safety"] == SAFETY_DECLARATION
    assert manifest["network_required"] is True
    assert manifest["data_sources"][0]["data_quality_flag"] == "ok"
    assert observation["report_meta"]["report_dir"] == "artifacts/uzi_report"
    assert not ABSOLUTE_PATH_RE.search(json.dumps(decision, ensure_ascii=False))
    assert not ABSOLUTE_PATH_RE.search(json.dumps(manifest, ensure_ascii=False))
    assert not ABSOLUTE_PATH_RE.search(json.dumps(observation, ensure_ascii=False))


def test_uzi_scan_falls_back_to_youzi_invalidation(tmp_path: Path):
    plugin = make_fake_uzi(tmp_path)

    result = uzi_scan(
        "000002.SZ",
        root=tmp_path,
        path=plugin,
        decision_time="2026-07-04T10:31:00+08:00",
        env_overrides={
            "FAKE_UZI_GENERATED_AT": "2026-07-04T10:30:00+08:00",
            "FAKE_UZI_NO_TECHNICAL": "1",
        },
    )

    decision = read_run_json(tmp_path, result, "decision.json")

    assert result["status"] == "ok"
    assert decision["invalidation_price"] == 8.88
    assert decision["invalidation_source"] == "synthesis.buy_zones.youzi.price"


def test_uzi_scan_writes_error_when_invalidation_is_missing(tmp_path: Path):
    plugin = make_fake_uzi(tmp_path)

    result = uzi_scan(
        "000003.SZ",
        root=tmp_path,
        path=plugin,
        decision_time="2026-07-04T10:31:00+08:00",
        env_overrides={
            "FAKE_UZI_GENERATED_AT": "2026-07-04T10:30:00+08:00",
            "FAKE_UZI_NO_INVALIDATION": "1",
        },
    )

    decision = read_run_json(tmp_path, result, "decision.json")
    manifest = read_run_json(tmp_path, result, "run_manifest.json")

    assert result["status"] == "error"
    assert decision["action_label"] == "ERROR"
    assert decision["error_reason"] == "missing_derived_invalidation_price"
    assert manifest["data_sources"][0]["data_quality_flag"] == "partial"
    assert (tmp_path / result["report_index"]).exists()


def test_uzi_scan_manifest_fails_future_leakage(tmp_path: Path):
    plugin = make_fake_uzi(tmp_path)

    result = uzi_scan(
        "000004.SZ",
        root=tmp_path,
        path=plugin,
        decision_time="2026-07-04T10:29:00+08:00",
        env_overrides={"FAKE_UZI_GENERATED_AT": "2026-07-04T10:30:00+08:00"},
    )

    validation = result["manifest_validation"]

    assert result["status"] == "invalid_manifest"
    assert validation["ok"] is False
    assert "future_leakage:uzi_skill_short_horizon" in validation["errors"]

