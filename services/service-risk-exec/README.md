# service-risk-exec

Risk/execution-authority skeleton that consumes strategy intent events.

## Behavior
- Subscribes to `strategy.intent` (override with `GB_STRATEGY_INTENT_CHANNEL`).
- Evaluates each `StrategyIntent` using shared risk authority.
- Publishes decision payloads to `risk.decision` (override with `GB_RISK_DECISION_CHANNEL`).
- Exposes `GET /health` (default `:8092`).
- Explicit boundary: emits decisions only; order adapters are external.

## Key environment variables
- `GB_REDIS_DSN`
- `GB_STRATEGY_INTENT_CHANNEL`
- `GB_RISK_DECISION_CHANNEL`
- `GB_RISK_HEALTH_HOST`
- `GB_RISK_HEALTH_PORT`
