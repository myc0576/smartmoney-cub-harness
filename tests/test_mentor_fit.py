from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from smartmoney_cub_harness.mentor_fit import build_mentor_fit
from smartmoney_cub_harness.schemas import SAFETY_DECLARATION


def _closed_case(index: int, *, market_phase: str, grade: str = "useful_alert") -> dict:
    return {
        "case_id": f"toy-{index}",
        "status": "normalized",
        "confirmation_status": "confirmed",
        "market_phase": market_phase,
        "action_label": "ALERT" if grade != "correct_no_trade" else "SILENT",
        "reasoning_chain": {
            "stock": {
                "pattern": "龙头反抽",
                "pattern_purity": "高",
                "recognition_level": "高",
            }
        },
        "source_payloads": {
            "decision": {
                "thesis": "toy leader low-buy setup with 1-3 day feedback",
                "time_stop": "D1/D3 review",
                "give_up_conditions": ["no fast feedback"],
            },
            "evaluation": {"grade": grade, "failure_tags": []},
            "outcome": {"met_user_pattern": True, "d1_return_pct": 3.5},
        },
    }


def test_build_mentor_fit_detects_conservative_template_emergence():
    cases = [
        _closed_case(
            i,
            market_phase="主升" if i % 2 == 0 else "分歧修复",
            grade="false_alert" if i in (1, 7) else "useful_alert",
        )
        for i in range(10)
    ]

    result = build_mentor_fit(
        {
            "cases": cases,
            "confirmed_memories": [
                {
                    "status": "confirmed",
                    "text": "用户偏低吸、不打板、怕浮亏，龙头反抽需要快反馈。",
                }
            ],
        }
    )

    assert result["schema"] == "smartmoney_cub_mentor_fit.v1"
    assert result["safety"] == SAFETY_DECLARATION
    assert result["public_case_as_signal"] is False
    assert result["mutates_champion"] is False
    assert result["emergence_status"]["status"] == "emerging"
    assert result["template_matches"][0]["template_id"] == "total_dragon_rebound"
    assert "low_buy_preference" in {item["label"] for item in result["style_labels"]}
    assert result["training_suggestions"]


def test_build_mentor_fit_requires_conservative_evidence_before_emergence():
    result = build_mentor_fit(
        {
            "cases": [_closed_case(i, market_phase="主升") for i in range(3)],
            "confirmed_memories": [],
        }
    )

    assert result["emergence_status"]["status"] == "insufficient_evidence"
    assert result["template_matches"] == []


def test_build_mentor_fit_rejects_public_template_as_buy_trigger():
    with pytest.raises(ValueError, match="public_template_forbidden"):
        build_mentor_fit(
            {
                "cases": [_closed_case(i, market_phase="主升") for i in range(10)],
                "template_registry": [
                    {
                        "template_id": "bad_copy_trade",
                        "source_type": "public_replay",
                        "allowed_use": ["case_study"],
                        "next_day_buy_trigger": "buy tomorrow",
                    }
                ],
            }
        )


def test_cli_mentor_fit_prints_json_without_writing_state(tmp_path: Path):
    payload_path = tmp_path / "mentor_fit_input.json"
    payload_path.write_text(
        json.dumps(
            {
                "cases": [
                    _closed_case(
                        i,
                        market_phase="主升" if i % 2 == 0 else "分歧修复",
                        grade="false_alert" if i in (1, 7) else "useful_alert",
                    )
                    for i in range(10)
                ],
                "confirmed_memories": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    cp = subprocess.run(
        [sys.executable, "-m", "smartmoney_cub_harness.cli", "mentor-fit", str(payload_path)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )

    assert cp.returncode == 0, cp.stderr
    result = json.loads(cp.stdout)
    assert result["schema"] == "smartmoney_cub_mentor_fit.v1"
    assert not (tmp_path / "state").exists()
