# Backtest Leakage Checks Playbook

## Purpose
Run deterministic research QA checks before every backtest to catch data leakage and invalidate unsafe runs early.

## Recommended quick-start order
1. **Define required metadata in request parameters**
   - `point_in_time_constituents: true`
   - `event_timestamp_field` and `asof_timestamp_field` with the same field name
   - `target_in_features: false`
   - `allow_lookahead: false` (or omit)
2. **Run backtest preflight** to size the run and gather confirmation token for large windows.
3. **Submit backtest create request**. Leakage checks run automatically before queueing.
4. **Review pass/fail summary** in stored run metadata under `research_qa.leakage_checks`.
5. **Handle invalid runs immediately**: if leakage is detected, API fails fast with `BACKTEST_LEAKAGE_DETECTED` and `status=invalid`.

## Checks executed before every backtest
- **look_ahead**: fails if `parameters.allow_lookahead=true`
- **survivorship_bias**: fails if `parameters.point_in_time_constituents=false`; warns if omitted
- **timestamp_alignment**: fails unless `event_timestamp_field == asof_timestamp_field`
- **target_leakage**: fails if `parameters.target_in_features=true`

## Pass/fail summary contract
The backtest flow writes:
- `status`: `pass` or `fail`
- `is_valid`: boolean
- `checked_at`: ISO-8601 UTC timestamp
- `checks`: per-check records with `name`, `status`, and `detail`

## Failure behavior
- Any failing leakage check causes immediate API rejection (`422`).
- Rejection includes:
  - `reason_code: BACKTEST_LEAKAGE_DETECTED`
  - `run_valid: false`
  - `status: invalid`
  - full `summary` payload for debugging/remediation.
