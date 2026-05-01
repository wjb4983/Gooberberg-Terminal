# KPI Catalog: Observability Dashboards

This catalog defines the minimum production dashboards, KPI owners, thresholds, and audience segmentation for model/research observability.

## Quick-start implementation order (recommended)

1. **Baseline data quality and freshness** (unblocks trust in all downstream KPIs).
2. **Validation failures dashboard + alerting** (fastest path to catching broken pipelines).
3. **Feature drift dashboard + alerting** (guards model validity over time).
4. **Signal distribution shift dashboard + alerting** (guards alpha/signal regime changes).
5. **Execution quality dashboard (fill/slippage)** (trading performance health).
6. **PnL attribution dashboard** (explains outcomes and supports governance).
7. **Audience-specific views** for research, risk, and ops using shared KPI definitions.

---

## Minimum dashboards and KPI definitions

### 1) Data Freshness Dashboard

**Purpose:** Detect stale, delayed, or missing market/features/signal inputs before they affect decisions.

| KPI | Definition | Computation | Cadence |
|---|---|---|---|
| Source latency (p50/p95/p99) | End-to-end lag from event timestamp to availability in serving store | `availability_ts - event_ts` by source | 1 min |
| Freshness SLA breach rate | % intervals where latency exceeds source SLA | `breaches / total_intervals` | 5 min |
| Staleness duration | Continuous time a critical dataset is older than SLA | wall-clock duration while stale | realtime |
| Missing partition ratio | % expected partitions/windows not landed | `missing / expected` | 5 min |

**Alerting thresholds and owners**

| KPI | Warning threshold | Critical threshold | Owner (primary) | Secondary |
|---|---|---|---|---|
| Source latency p95 | > 0.8 × SLA for 10 min | > SLA for 5 min | Data Platform On-call | Ops On-call |
| Freshness SLA breach rate | > 5% in 30 min | > 15% in 30 min | Data Platform On-call | Risk Duty Officer |
| Staleness duration | > 5 min (tier-0 feeds) | > 15 min (tier-0 feeds) | Ops On-call | Research On-call |
| Missing partition ratio | > 1% per hour | > 5% per hour | Data Platform On-call | Ops On-call |

---

### 2) Validation Failures Dashboard

**Purpose:** Surface schema, range, null, and integrity failures in ETL/feature pipelines.

| KPI | Definition | Computation | Cadence |
|---|---|---|---|
| Validation failure rate | % records failing one or more checks | `failed_records / checked_records` | 5 min |
| Critical rule failure count | Count of failures on severity=critical rules | grouped by rule_id | 5 min |
| Null spike index | Relative null-rate increase vs 7d baseline | `(null_rate_now / baseline_null_rate)` | 5 min |
| Contract mismatch count | Number of schema/contract mismatches per run | parser/validator count | per run |

**Alerting thresholds and owners**

| KPI | Warning threshold | Critical threshold | Owner (primary) | Secondary |
|---|---|---|---|---|
| Validation failure rate | > 0.5% for 3 runs | > 2% any run | Data Quality Owner | Data Platform On-call |
| Critical rule failure count | >= 1 for 2 runs | >= 1 for 1 run (tier-0) | Data Quality Owner | Risk Duty Officer |
| Null spike index | > 2.0 for 30 min | > 4.0 for 15 min | Feature Owner | Data Platform On-call |
| Contract mismatch count | >= 1 in non-prod | >= 1 in prod | Data Platform On-call | Ops On-call |

---

### 3) Feature Drift Dashboard

**Purpose:** Detect training-serving skew and temporal drift that can invalidate model assumptions.

| KPI | Definition | Computation | Cadence |
|---|---|---|---|
| PSI per feature | Population Stability Index between reference and current windows | PSI(current, reference) | hourly |
| KS statistic per feature | Kolmogorov-Smirnov statistic for continuous features | KS(current, reference) | hourly |
| Drifted feature ratio | % monitored features breaching drift threshold | `drifted / monitored` | hourly |
| Training-serving skew rate | % rows where online feature differs from offline recomputation beyond tolerance | `skew_rows / checked_rows` | 15 min |

**Alerting thresholds and owners**

| KPI | Warning threshold | Critical threshold | Owner (primary) | Secondary |
|---|---|---|---|---|
| PSI per feature | > 0.10 for 2 hours | > 0.25 for 1 hour | Model Owner (Research) | MRM/Risk |
| KS statistic per feature | > 0.10 | > 0.20 | Model Owner (Research) | MRM/Risk |
| Drifted feature ratio | > 10% | > 25% | Model Owner (Research) | Research Lead |
| Training-serving skew rate | > 0.5% | > 2% | ML Platform Owner | Ops On-call |

---

### 4) Signal Distribution Shift Dashboard

**Purpose:** Track behavior changes in model outputs/signals that may indicate regime shift or silent model degradation.

| KPI | Definition | Computation | Cadence |
|---|---|---|---|
| Signal mean/std shift | Z-score deviation vs rolling baseline | `(x_now - mean_30d)/std_30d` | 15 min |
| Tail mass shift | Change in probability mass in top/bottom deciles | `P_t(decile) - P_ref(decile)` | hourly |
| Sign-flip rate | % entities where signal sign flips vs prior interval | `flips / total` | 15 min |
| Correlation-to-benchmark shift | Change in correlation of signal vs benchmark factor set | `corr_now - corr_ref` | hourly |

**Alerting thresholds and owners**

| KPI | Warning threshold | Critical threshold | Owner (primary) | Secondary |
|---|---|---|---|---|
| Signal mean/std shift | \|z\| > 2 for 1 hour | \|z\| > 3 for 30 min | Research On-call | Risk Duty Officer |
| Tail mass shift | > 5 pp change | > 10 pp change | Research On-call | Model Owner |
| Sign-flip rate | > 20% | > 35% | Research On-call | Ops On-call |
| Correlation shift | \|Δcorr\| > 0.15 | \|Δcorr\| > 0.30 | Model Owner | MRM/Risk |

---

### 5) Fill / Slippage Dashboard

**Purpose:** Measure execution quality and market impact versus assumptions.

| KPI | Definition | Computation | Cadence |
|---|---|---|---|
| Fill ratio | % child/parent order quantity filled | `filled_qty / sent_qty` | 5 min |
| Slippage (bps) | Execution price vs decision or arrival benchmark | signed bps difference | 5 min |
| Rejection rate | % orders rejected by venue/broker | `rejected / sent` | 5 min |
| Time-to-fill p95 | p95 duration from submit to fill | `fill_ts - submit_ts` | 5 min |

**Alerting thresholds and owners**

| KPI | Warning threshold | Critical threshold | Owner (primary) | Secondary |
|---|---|---|---|---|
| Fill ratio | < 85% for 30 min | < 70% for 15 min | Execution Ops | Trading Ops Lead |
| Slippage (bps) | > +5 bps vs baseline | > +10 bps vs baseline | Execution Ops | Risk Duty Officer |
| Rejection rate | > 2% | > 5% | Broker Connectivity Owner | Ops On-call |
| Time-to-fill p95 | > 2× 30d median | > 3× 30d median | Execution Ops | Trading Systems On-call |

---

### 6) PnL Attribution Dashboard

**Purpose:** Explain realized and unrealized performance by source components.

| KPI | Definition | Computation | Cadence |
|---|---|---|---|
| Daily gross/net PnL | Total gross and net (after costs) PnL | strategy books aggregation | daily + intraday preview |
| PnL by factor/signal bucket | Contribution by risk factor, sector, signal quantile | additive attribution model | hourly/daily |
| Cost attribution | PnL impact from fees, spread, slippage, borrow | transaction cost model | hourly/daily |
| Hit rate / payoff ratio | Fraction winning trades and avg win/avg loss | trade outcome stats | daily |

**Alerting thresholds and owners**

| KPI | Warning threshold | Critical threshold | Owner (primary) | Secondary |
|---|---|---|---|---|
| Intraday net PnL drawdown | < -1.5σ vs 60d intraday distribution | < -3σ | Risk Duty Officer | PM/Research Lead |
| Factor bucket divergence | Any bucket contribution > 2σ from 60d | > 3σ | Research Lead | Risk Duty Officer |
| Cost attribution spike | Costs > 1.5× 30d median | > 2× 30d median | Execution Ops | PM |
| Hit rate collapse | drop > 15 pp vs 30d baseline | drop > 25 pp | PM/Research Lead | MRM/Risk |

---

## Audience-specific dashboard separation

### Research dashboard view
- Focus: feature drift, signal distribution, model behavior, factor attribution.
- Primary KPIs: PSI/KS, drift ratio, sign-flip rate, correlation shift, PnL by factor/signal bucket.
- Time horizons: intraday + rolling 7d/30d.
- Default filters: model/version, universe, regime tags.

### Risk dashboard view
- Focus: limit breaches, abnormal drawdowns, validation critical failures, concentration of losses.
- Primary KPIs: PnL drawdown z-score, factor divergence, critical validation failure count, cost spikes.
- Time horizons: realtime alerts + EOD supervisory summary.
- Default filters: desk, strategy, legal entity.

### Ops dashboard view
- Focus: data freshness, pipeline health, order routing/execution reliability.
- Primary KPIs: freshness breach rate, staleness duration, contract mismatches, rejection rate, time-to-fill p95.
- Time horizons: 1m/5m operational windows and 24h service review.
- Default filters: source system, venue/broker, region.

---

## Ownership model and escalation

- Each KPI must have a **primary owner** (accountable) and **secondary owner** (backup).
- Critical alerts page the primary immediately; if unacknowledged for 10 minutes, escalate to secondary.
- Repeated critical breaches (>=3 in 24h) open an incident and trigger postmortem requirements.
- Ownership map should be mirrored in pager/on-call schedules and reviewed monthly.

## Drift monitoring policy (core features + signal outputs)

### Scope and configuration

- Configure drift checks on all **core serving features** (tier-0 + tier-1) and all **production signal outputs** before enabling autonomous decision paths.
- Use a fixed **reference window** (30d rolling baseline by default) and a **current window** (1h for features, 15m for signals).
- Required detectors:
  - Features: PSI + KS + training-serving skew.
  - Signals: z-score shift + tail-mass shift + sign-flip rate.
- Required dimensions:
  - Global portfolio view.
  - Per-model/version view.
  - Per-region/venue (when applicable) to prevent localized blind spots.

### Alert levels and response SLAs

| Level | Trigger semantics | Ack SLA | Triage SLA | Mitigation SLA | Auto-escalation |
|---|---|---|---|---|---|
| Info | Early warning threshold crossed, no customer/business impact expected | 4h | 1 business day | Next planned release window | No paging; ticket only |
| Warn | Sustained drift or multi-metric warning with potential model-quality impact | 30m | 2h | 1 business day | Escalate to backup if unacked at 30m |
| Critical | Severe feature/signal drift or training-serving skew breach with active decision risk | 10m | 30m | Immediate containment (pause/guardrail/rollback) within 60m | Page primary on-call and backup contact simultaneously |

### Routing requirements

- **Info** alerts route to observability Slack channel + issue tracker.
- **Warn** alerts route to primary on-call queue; backup receives passive notification.
- **Critical** alerts route to:
  1. Primary on-call pager.
  2. Backup contact pager/SMS.
  3. Incident channel bootstrap automation.
- Critical alerts must include: detector, impacted model versions, top drifted features/signals, first-seen timestamp, and suggested containment action.

### Synthetic drift validation (recommended execution order)

1. Baseline check: verify detector jobs, metric exports, and alert routes are healthy.
2. Inject **feature distribution drift** in staging (e.g., mean/variance shift on selected core features) and confirm expected info/warn transitions.
3. Inject **training-serving skew** (offline/online mismatch) and confirm critical path + dual paging.
4. Inject **signal output shift** (tail mass + sign-flip spike) and confirm warn/critical behavior.
5. Run end-to-end alert delivery test to primary + backup contacts.
6. Execute rollback test: clear injection and verify alert auto-resolution + incident notes closure.
7. Promote to production only after two consecutive synthetic runs pass without routing or SLA misses.

## Governance notes

- Thresholds are defaults and should be calibrated using 30-60 day historical distributions.
- Tier-0 datasets/models may require tighter thresholds than listed here.
- Any threshold or KPI definition change must be versioned with effective date and approver.
