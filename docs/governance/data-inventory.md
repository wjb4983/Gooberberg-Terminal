# Data Inventory (Interim Spreadsheet)

This document is the interim single-table system of record for market, fundamental, and alternative datasets currently used by model configs and task definitions.

## Severity tiers

- **Tier 0 (critical):** Dataset outage or corruption can halt live decisioning, risk controls, or mandatory compliance flows.
- **Tier 1 (high):** Dataset outage or corruption materially degrades model quality, coverage, or intraday responsiveness, but deterministic fallback paths may still run.
- **Tier 2 (medium):** Dataset outage or corruption affects enrichment, research speed, or non-critical features without halting core operations.

## `data_inventory`

| dataset_name | source | owner | schema_version | refresh_cadence | SLA | downstream_consumers | retention_policy | severity_tier |
|---|---|---|---|---|---|---|---|---|
| dataset.ohlcv.adjusted | Massive market data adapter | Priya Shah (Market Data Platform) | v1 | 1m intraday + daily EOD | 99.9% monthly availability; <5m lag intraday | task_catalog baseline backtest; training pipelines | 24 months hot, 5 years cold archive | Tier 0 |
| ohlcv.close | Massive market data adapter | Priya Shah (Market Data Platform) | v1 | 1m intraday + daily EOD | 99.9% monthly availability; <5m lag intraday | phase1/arima/torch/hmm model families | 24 months hot, 5 years cold archive | Tier 0 |
| ohlcv.volume | Massive market data adapter | Priya Shah (Market Data Platform) | v1 | 1m intraday + daily EOD | 99.9% monthly availability; <5m lag intraday | phase1/arima model families | 24 months hot, 5 years cold archive | Tier 1 |
| dataset.returns.windowed | Derived from adjusted OHLCV | Marco Diaz (Research Data Engineering) | v1 | hourly + daily recompute | 99.5% monthly availability; <30m build lag | task_catalog rolling-window research tasks | 12 months hot, 3 years cold archive | Tier 1 |
| returns.log | Derived from adjusted OHLCV | Marco Diaz (Research Data Engineering) | v1 | hourly + daily recompute | 99.5% monthly availability; <30m build lag | hmm_regime_switching; phase1/phase4 models | 12 months hot, 3 years cold archive | Tier 1 |
| returns.intraday_1m | Derived from adjusted OHLCV | Marco Diaz (Research Data Engineering) | v1 | every 1 minute | 99.5% monthly availability; <10m lag | phase2 intraday regime models | 12 months hot, 3 years cold archive | Tier 1 |
| returns.intraday_5m | Derived from adjusted OHLCV | Marco Diaz (Research Data Engineering) | v1 | every 5 minutes | 99.5% monthly availability; <15m lag | phase2 earnings drift models | 12 months hot, 3 years cold archive | Tier 1 |
| returns.daily | Derived from adjusted OHLCV | Marco Diaz (Research Data Engineering) | v1 | daily EOD | 99.5% monthly availability; complete by 02:00 UTC | phase2 cross-sectional models | 10 years archive | Tier 1 |
| returns.forward_1d | Label pipeline from daily returns | Marco Diaz (Research Data Engineering) | v1 | daily EOD | 99.5% monthly availability; complete by 03:00 UTC | phase2 supervised labeling tasks | 10 years archive | Tier 1 |
| macro.calendar | Macro events provider feed | Evelyn Kim (Alt Data) | v1 | daily + event-driven | 99.0% monthly availability | phase1 macro-aware models | 5 years archive | Tier 2 |
| macro.features | Derived macro feature store | Evelyn Kim (Alt Data) | v1 | daily | 99.0% monthly availability | phase1 macro feature models | 5 years archive | Tier 2 |
| fundamentals.point_in_time | Point-in-time fundamentals provider | Daniel Okafor (Fundamentals) | v1 | daily + filing-triggered | 99.7% monthly availability; filing ingest <60m | phase2 fundamental cross-sectional models | 7 years archive | Tier 1 |
| earnings.surprise_pct | Earnings events provider | Daniel Okafor (Fundamentals) | v1 | event-driven | 99.7% monthly availability; <15m after release | phase2 earnings drift models | 7 years archive | Tier 1 |
| earnings.announcement_timestamp | Earnings events provider | Daniel Okafor (Fundamentals) | v1 | event-driven | 99.7% monthly availability; <15m after release | phase2 earnings drift models | 7 years archive | Tier 1 |
| earnings.point_in_time_calendar | Earnings calendar provider | Daniel Okafor (Fundamentals) | v1 | daily + revisions | 99.7% monthly availability | phase2 earnings drift models | 7 years archive | Tier 1 |
| earnings.next_announcement_date | Earnings calendar provider | Daniel Okafor (Fundamentals) | v1 | daily + revisions | 99.7% monthly availability | phase2 event scheduling features | 7 years archive | Tier 2 |
| sentiment.score | News/NLP sentiment feed | Evelyn Kim (Alt Data) | v1 | hourly | 99.0% monthly availability; <2h lag | phase1 multi-signal models | 2 years hot, 5 years cold archive | Tier 2 |
| sentiment.guidance_tone | Earnings call NLP feed | Evelyn Kim (Alt Data) | v1 | event-driven | 99.0% monthly availability; <6h lag post-call | phase2 earnings drift models | 5 years archive | Tier 2 |
| options.iv_surface | Options chain provider | Sara Nguyen (Derivatives Data) | v1 | every 15 minutes | 99.5% monthly availability | phase2 options skew reversion models | 18 months hot, 5 years cold archive | Tier 1 |
| options.skew_25d | Options chain provider | Sara Nguyen (Derivatives Data) | v1 | every 15 minutes | 99.5% monthly availability | phase2 options skew reversion models | 18 months hot, 5 years cold archive | Tier 1 |
| options.open_interest | Options chain provider | Sara Nguyen (Derivatives Data) | v1 | daily + intraday refresh | 99.5% monthly availability | phase2 options skew reversion models | 5 years archive | Tier 2 |
| options.chain_snapshot_timestamp | Options chain provider | Sara Nguyen (Derivatives Data) | v1 | every 15 minutes | 99.5% monthly availability | phase2 options skew reversion models | 18 months hot, 5 years cold archive | Tier 2 |
| options.volume | Options chain provider | Sara Nguyen (Derivatives Data) | v1 | every 15 minutes | 99.5% monthly availability | phase2 options skew reversion models | 5 years archive | Tier 2 |

## Governance cadence

- **Weekly standup:** 30-minute **Data Governance Standup** every Tuesday, 15:00 UTC.
- **Required attendees:** all named dataset owners above + model governance representative.
- **Agenda order (recommended quick-start execution order):**
  1. Tier 0 incidents, SLA misses, and mitigation status (5 min).
  2. Tier 1 schema/quality drift review (10 min).
  3. Tier 2 backlog and enrichment priorities (5 min).
  4. Owner reassignment and new dataset intake approvals (5 min).
  5. Action item confirmation and due dates (5 min).
