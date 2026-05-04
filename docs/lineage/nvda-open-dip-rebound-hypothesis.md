# NVDA Open-Dip-Rebound Hypothesis (Research-Only)

## Purpose and Scope

This document defines a **research hypothesis** for an intraday NVDA setup in which an early-session downward move is followed by a rebound. It establishes expected failure modes, validation methodology, and risk controls that are required **before any real-capital deployment decision** is considered.

> **Important repository boundary:** This repository does **not** execute live trades. It provides research, simulation, monitoring, and integration surfaces that interact with external paper/live broker or execution services through status and control contracts only.

## Hypothesis Statement

### Core hypothesis

On selected sessions, NVDA may show a repeatable microstructure pattern:

1. A meaningful drawdown from the opening print during the first portion of regular trading hours.
2. A statistically significant rebound within a bounded time horizon.
3. Net positive expectancy after transaction costs and slippage under constrained entry/exit rules.

### Working definition (to be parameterized)

- **Universe:** NVDA only (single-name pilot).
- **Session:** US regular trading hours.
- **Dip event:** Price decline from opening reference exceeding a configured threshold.
- **Rebound event:** Recovery from dip low to a recovery threshold before timeout.
- **Trade abstraction:** Simulated long-entry on confirmation; deterministic exits via stop, timeout, or target.

All thresholds must remain configuration-driven and captured in lineage metadata; no discretionary overrides in backtests.

## Expected Failure Modes

The hypothesis is expected to fail in one or more of the following conditions:

1. **Trend-day continuation risk**
   - Opening dip is not mean-reverting; sell pressure persists all session.
2. **Gap-and-go mismatch**
   - Overnight information shock causes regime shift where historical dip/rebound behavior no longer applies.
3. **Volatility regime break**
   - Intraday volatility or spread widens beyond assumed bounds; slippage invalidates modeled expectancy.
4. **Liquidity/queue-position degradation**
   - Simulated fills become unrealizable under realistic queue dynamics.
5. **Event-driven discontinuities**
   - Earnings, guidance, macro headlines, or sector-wide halts dominate micro-pattern behavior.
6. **Time-of-day instability**
   - Strategy edge concentrates in narrow windows and degrades when session timing shifts.
7. **Overfitting / selection bias**
   - Apparent edge arises from threshold mining rather than robust signal.
8. **Data quality and survivorship artifacts**
   - Bad ticks, clock drift, stale bars, or vendor-specific corrections create false positives.
9. **Cost model underestimation**
   - Backtest assumes tighter spreads/fees than executable reality.
10. **Operational dependency failures**
    - Connectivity, auth, status heartbeat, or control-plane degradation blocks safe operation.

## Validation Methodology

Validation must be deterministic, auditable, and repeatable.

### 1) Data and lineage requirements

- Use versioned datasets with documented vendor/source provenance.
- Record timezone, session calendar, corporate action handling, and bar construction rules.
- Persist parameter set IDs, code commit hash, and random seeds (if any).
- Reject runs with unresolved data gaps or schema mismatches.

### 2) Experimental design

- **In-sample / out-of-sample split** with fixed date boundaries.
- **Walk-forward validation** across multiple market regimes.
- **Sensitivity sweeps** around dip, rebound, stop, and timeout thresholds.
- **Ablation tests** isolating each rule component.
- **Null benchmarks** (e.g., random-timed entries, open-to-close baselines).

### 3) Metrics (minimum)

- Expectancy per trade (net of modeled costs).
- Win rate, payoff ratio, and drawdown profile.
- Tail-risk metrics (worst day, worst run, CVaR proxy if available).
- Fill realism indicators (modeled vs conservative slippage scenarios).
- Stability metrics across months/regimes (not only aggregate totals).

### 4) Robustness and falsification checks

- Recompute results under conservative cost/slippage assumptions.
- Verify no lookahead leakage in feature construction and timestamp joins.
- Confirm edge survives small perturbations in thresholds.
- Require consistent sign and magnitude in out-of-sample windows.
- Explicitly document where/when the hypothesis fails.

### 5) Paper-trading gate (external service)

Before any deployment discussion, run prolonged external paper-trading observation with:

- Contract-level status/heartbeat monitoring.
- Deterministic replay parity checks (research vs paper signals).
- Daily exception review and kill-switch drill evidence.

## Risk Controls Required Before Real-Capital Consideration

Real-capital consideration is blocked unless all controls below are complete and signed off:

1. **Governance and approvals**
   - Strategy specification, model card, and change log approved.
   - Independent review of methodology and assumptions.
2. **Hard risk limits**
   - Max position size, max daily loss, max consecutive losses, and session stop-out.
   - Global kill switch and automatic fail-safe transitions.
3. **Execution safety controls (external integrations)**
   - Explicit status-contract health requirements.
   - Control-contract acknowledgement/timeout semantics validated.
   - No order intent issued when connectivity/auth state is degraded.
4. **Operational readiness**
   - Runbooks for auth failures, reconnect storms, stale heartbeats, and safe restart validated.
   - On-call ownership and incident escalation paths assigned.
5. **Monitoring and alerting**
   - Real-time telemetry for latency, rejects, drift, and risk limit proximity.
   - Alert thresholds tested in tabletop and paper scenarios.
6. **Post-trade and auditability**
   - Immutable event logs sufficient for reconstruction.
   - Daily reconciliations between strategy intents and broker acknowledgements.

## Quick-Start Tasks (Recommended Order)

1. **Finalize hypothesis spec**
   - Lock event definitions, thresholds, and allowed parameter ranges.
2. **Establish lineage-complete dataset**
   - Freeze data snapshot and capture metadata/provenance.
3. **Build deterministic backtest harness configuration**
   - Ensure reproducible runs and artifact capture.
4. **Run baseline + null benchmarks**
   - Measure whether signal exceeds naive alternatives.
5. **Execute walk-forward and sensitivity analyses**
   - Test stability across regimes and parameter perturbations.
6. **Perform failure-mode stress tests**
   - Simulate trend days, volatility spikes, and elevated cost environments.
7. **Complete independent model-risk review**
   - Document assumptions, limitations, and falsification outcomes.
8. **Integrate external paper-service status/control contracts**
   - Validate health checks, acknowledgements, and safe-block conditions.
9. **Paper-trading observation period with incident drills**
   - Verify operational readiness and monitoring effectiveness.
10. **Go/No-Go committee decision**
   - Real capital remains disallowed without formal sign-off.

## Non-Goals

- This document is not a promise of profitability.
- This document does not authorize autonomous live order placement in this repository.
- This document does not replace legal, compliance, or broker-specific obligations.
