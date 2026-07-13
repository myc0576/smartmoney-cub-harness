from __future__ import annotations

import json
from pathlib import Path

from smartmoney_cub_harness.memory import save_memory_record
from smartmoney_cub_harness.schemas import SAFETY_DECLARATION


def test_save_memory_redacts_email_phone_token_cookie_account_and_paths(tmp_path: Path):
    case_record = tmp_path / "case_record.json"
    case_record.write_text(
        json.dumps(
            {
                "case_id": "case-secret",
                "source": "offline_run",
                "status": "normalized",
                "symbol": "TOY.CUB",
                "action_label": "ALERT",
                "payloads": {
                    "decision": {
                        "thesis": (
                            "contact trader@example.test phone 13800138000 "
                            "token=abc cookie=session account=123 "
                            "C:\\Users\\Trader\\secret.txt /home/trader/private.txt"
                        ),
                        "invalidation_price": 9.4,
                        "time_stop": "D1/D3 review",
                        "give_up_conditions": ["email trader@example.test", "token=abc"],
                        "data_source": "toy_strategy",
                        "available_at": "2026-06-01T15:30:00+08:00",
                        "data_quality_flag": "ok",
                    },
                    "outcome": {"horizon": "d1", "d1_return_pct": 5.0},
                    "evaluation": {"grade": "useful_alert", "failure_tags": []},
                },
                "safety": SAFETY_DECLARATION,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = save_memory_record(case_record)
    memory = Path(result["memory_record_path"]).read_text(encoding="utf-8")

    assert result["safety"] == SAFETY_DECLARATION
    assert "trader@example.test" not in memory
    assert "13800138000" not in memory
    assert "abc" not in memory
    assert "session" not in memory
    assert "account=123" not in memory
    assert "C:\\Users\\Trader" not in memory
    assert "/home/trader" not in memory
    assert "[REDACTED]" in memory
