from __future__ import annotations

import json
from importlib.resources import files


def load_toy_prices() -> dict[str, object]:
    resource = files("smartmoney_cub_harness").joinpath("data", "sample_prices.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def main() -> int:
    prices = load_toy_prices()
    symbol = "TOY.CUB"
    series = prices[symbol]
    decision_day = "20260601"
    close = float(series[decision_day]["close"])
    invalidation = round(close * 0.94, 2)
    payload = {
        "schema": "toy_observation.v1",
        "observation_candidates": [
            {
                "symbol": symbol,
                "thesis": "toy pullback observation with explicit invalidation and delayed review",
                "invalidation_price": invalidation,
            }
        ],
        "note": "toy data only; not financial advice",
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
