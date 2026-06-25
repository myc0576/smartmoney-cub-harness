# Decision Schema

The public schema is deliberately small.

```json
{
  "schema": "smartmoney_cub_decision.v1",
  "run_id": "20260601_153000-after-close",
  "decision_time": "2026-06-01T15:30:00+08:00",
  "mode": "after-close",
  "action_label": "ALERT",
  "symbol": "TOY.CUB",
  "invalidation_price": 9.4,
  "time_stop": "D1/D3 review",
  "give_up_conditions": ["observation thesis is no longer supported by recorded evidence"],
  "data_source": "toy_strategy",
  "available_at": "2026-06-01T15:30:00+08:00",
  "data_quality_flag": "ok",
  "safety": "READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE"
}
```

## Required for Non-Silent Decisions

- `invalidation_price`
- `time_stop`
- `give_up_conditions`
- `data_source`
- `available_at`
- `data_quality_flag`

Missing any of these fields makes the evaluation invalid.
