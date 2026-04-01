# service-inference-live

Live inference skeleton for generating **strategy intents** only.

## Behavior
- Emits mock `StrategyIntent` payloads for active strategy instances on a configurable timer.
- Includes `trace_id` and `confidence` fields in each intent message.
- Publishes to Redis pub/sub topic `strategy.intent` (override with `GB_STRATEGY_INTENT_CHANNEL`).
- Exposes a simple health endpoint at `GET /health` (default `:8091`).
- **Does not place orders**; execution authority is delegated to `service-risk-exec`.

## Key environment variables
- `GB_REDIS_DSN`
- `GB_ACTIVE_STRATEGY_INSTANCE_IDS` (comma-separated UUIDs)
- `GB_INFERENCE_INTENT_INTERVAL_SECONDS`
- `GB_STRATEGY_INTENT_CHANNEL`
- `GB_INFERENCE_HEALTH_HOST`
- `GB_INFERENCE_HEALTH_PORT`
