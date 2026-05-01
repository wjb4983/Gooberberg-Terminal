# service-risk-exec

Risk/execution-authority skeleton that consumes strategy intent events.

## Behavior
- Subscribes to `strategy.intent` (override with `GB_STRATEGY_INTENT_CHANNEL`).
- Evaluates each `StrategyIntent` using shared risk authority.
- Enforces runtime guardrails loaded from `config/strategy_risk_limits.json`.
- Publishes decision payloads to `risk.decision` (override with `GB_RISK_DECISION_CHANNEL`).
- Exposes `GET /health` (default `:8092`).
- Explicit boundary: emits decisions only; order adapters are external.

## Runtime guardrails
Per-strategy hard limits are machine-readable and currently include:
- `max_intraday_drawdown`
- `max_position_concentration`
- `max_daily_turnover`
- `max_slippage_deviation_bps`

On breach:
- Intraday drawdown breach triggers `de_risk`.
- Concentration/turnover/slippage breach triggers `block_new_orders`.

Decision payloads include a `runtime_guard` object with `action` and `breached_rules`.

## Quick-start tasks (recommended order)
1. Define limits in `config/strategy_risk_limits.json` for each `strategy_key`.
2. Start service and publish representative strategy intents.
3. Observe `runtime_guard` decisions on `risk.decision` events.
4. Run simulated breach tests to verify blocking/de-risking behavior.

## Key environment variables
- `GB_REDIS_DSN`
- `GB_STRATEGY_INTENT_CHANNEL`
- `GB_RISK_DECISION_CHANNEL`
- `GB_RISK_HEALTH_HOST`
- `GB_RISK_HEALTH_PORT`
