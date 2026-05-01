# Trading Incident Runbooks

## 1) Stale Market Data

### Detection
- Market data freshness monitor flags `last_tick_age_ms` above threshold for any subscribed symbol group.
- Cross-venue parity checks show one feed static while peer venues continue updating.
- Trader/UI alerts indicate frozen quotes while order acknowledgements continue.

### Triage Owner
- **Primary:** Operations (Market Data Ops)
- **Secondary:** Research (signal health) and Risk (exposure validation)

### Immediate Containment
1. Disable strategy modules that require real-time quote updates.
2. Shift routing to validated backup feed(s) and enable conservative price collars.
3. Freeze new discretionary order entry for impacted symbols until freshness recovers.
4. Recompute portfolio valuation using fallback mid/last-known-safe pricing source.

### Rollback Path
1. Confirm feed freshness below recovery threshold for at least 5 consecutive intervals.
2. Re-enable strategies in phased batches (low-risk books first).
3. Remove temporary collars after spread/volatility sanity checks pass.
4. Close incident only after 30-minute post-restore monitoring window.

### Comms Template
> **Incident:** Stale Market Data  
> **Start Time (UTC):** <YYYY-MM-DD HH:MM>  
> **Impact:** Delayed/unchanged quotes for <symbols/venues>; strategy throttling enabled.  
> **Containment:** Switched to backup feeds, paused affected strategy modules, tightened collars.  
> **Risk Posture:** Net exposure reviewed; no uncontrolled order flow.  
> **Next Update:** <time in 15–30 min>

---

## 2) Bad Corporate Actions

### Detection
- Corporate action reconciliation job detects split/dividend mismatch against reference vendor(s).
- Sudden unexplained PnL jump/drop around ex-date for single issuer.
- Position quantities/cost basis differ between portfolio-state service and broker confirms.

### Triage Owner
- **Primary:** Research (data correctness)
- **Secondary:** Operations (booking) and Risk (limit integrity)

### Immediate Containment
1. Halt trading for impacted issuers and related derivatives.
2. Lock CA-adjusted analytics outputs and switch to last verified snapshot.
3. Block automated rebalancing that depends on adjusted shares/weights.
4. Trigger manual reconciliation with broker and golden vendor feed.

### Rollback Path
1. Correct CA event in security master and regenerate adjusted history.
2. Rebuild affected positions, NAV, and factor exposures from corrected effective date.
3. Validate with dual-source checks and sign-off from Research + Operations.
4. Resume trading for impacted names with reduced size limits for first session.

### Comms Template
> **Incident:** Bad Corporate Action Processing  
> **Start Time (UTC):** <YYYY-MM-DD HH:MM>  
> **Impact:** Incorrect adjustment for <ticker/event>; trading paused on impacted instruments.  
> **Containment:** CA-dependent models frozen; manual reconciliation in progress.  
> **Risk Posture:** Exposure and limits under manual supervision.  
> **Next Update:** <time in 30 min>

---

## 3) Model Drift Spike

### Detection
- Online drift monitor reports PSI/KS thresholds breached for key features.
- Live hit-rate/slippage degradation exceeds control-band for 3+ intervals.
- Shadow model divergence alarms fire between production and benchmark outputs.

### Triage Owner
- **Primary:** Research (model owner)
- **Secondary:** Risk (performance-to-risk impact) and Operations (runtime controls)

### Immediate Containment
1. Reduce model-driven participation rate and max order size via kill-switch profile.
2. Route impacted strategies to fallback model or rules-based execution mode.
3. Disable auto-parameter adaptation while investigation proceeds.
4. Snapshot feature distributions, predictions, and outcomes for forensic replay.

### Rollback Path
1. Validate root cause (feature pipeline shift, regime change, bug, or bad labels).
2. Restore last known good model artifact + feature contract.
3. Run replay/backtest gate and short shadow period before full promotion.
4. Re-scale limits gradually as live KPIs return within control-band.

### Comms Template
> **Incident:** Model Drift Spike  
> **Start Time (UTC):** <YYYY-MM-DD HH:MM>  
> **Impact:** Elevated drift and degraded execution quality in <strategy/model>.  
> **Containment:** Switched to fallback mode; reduced participation and sizing.  
> **Risk Posture:** Tightened risk envelope active.  
> **Next Update:** <time in 30 min>

---

## 4) Order Reject Storm

### Detection
- Reject-rate monitor exceeds threshold (e.g., >5% over 5 minutes) by venue/broker.
- Burst of identical reject codes (session, price bands, throttle, permissions).
- Order queue growth with falling fill-rate and rising retry counts.

### Triage Owner
- **Primary:** Operations (execution ops)
- **Secondary:** Risk (duplicate/rogue flow control) and Research (order logic if systematic)

### Immediate Containment
1. Enable reject-storm circuit breaker: stop automated retries beyond safe cap.
2. Pause new order submissions to affected broker/venue sessions.
3. Drain/cancel non-essential working orders; preserve hedges and risk-reducing orders.
4. Apply static price/size clamps and validate session/auth state.

### Rollback Path
1. Confirm broker/venue health and successful test order acknowledgements.
2. Reopen flow by strategy tier (hedging first, alpha second).
3. Monitor reject taxonomy and retry counters for 20-minute stabilization.
4. Remove temporary clamps after stable acceptance/fill metrics.

### Comms Template
> **Incident:** Order Reject Storm  
> **Start Time (UTC):** <YYYY-MM-DD HH:MM>  
> **Impact:** Elevated rejects on <broker/venue>; reduced order throughput.  
> **Containment:** Submission pause + circuit breaker enabled; retries capped.  
> **Risk Posture:** Hedging flow prioritized; duplicate risk constrained.  
> **Next Update:** <time in 15 min>

---

## 5) Latency Blowout

### Detection
- p95/p99 order path latency breaches SLO for 3 consecutive windows.
- Queue-depth alarms on risk checks, routing, or market-data normalization stages.
- Synthetic connectivity checks show RTT and timeout spikes.

### Triage Owner
- **Primary:** Operations (platform/runtime)
- **Secondary:** Research (latency-sensitive strategy gating) and Risk (execution slippage risk)

### Immediate Containment
1. Throttle or pause latency-sensitive strategies.
2. Shift traffic to healthy region/instance pool or degraded-but-stable path.
3. Increase timeout guards and disable non-critical synchronous enrichments.
4. Enforce wider slippage caps and minimum liquidity thresholds.

### Rollback Path
1. Identify bottleneck layer (network, broker gateway, risk service, or datastore).
2. Roll back recent deploy/config change if correlated with onset.
3. Restore normal routing weights after p95/p99 remain within SLO for 30 minutes.
4. Re-enable paused strategies progressively with live guardrails.

### Comms Template
> **Incident:** Latency Blowout  
> **Start Time (UTC):** <YYYY-MM-DD HH:MM>  
> **Impact:** Elevated execution latency in <path/service>; fill quality at risk.  
> **Containment:** Strategy throttles active; traffic shifted to healthy path.  
> **Risk Posture:** Slippage controls tightened.  
> **Next Update:** <time in 15 min>

---

## 6) Risk-Limit Breach

### Detection
- Real-time risk engine flags hard-limit breach (gross/net, sector, factor, or VaR).
- Pre-trade controls reject orders for limit exceedance across multiple strategies.
- Manual desk/risk dashboard confirms breach persistence beyond transient window.

### Triage Owner
- **Primary:** Risk
- **Secondary:** Operations (execution controls) and Research (strategy intent/context)

### Immediate Containment
1. Trigger firmwide risk kill-switch for offending books/strategies.
2. Block new risk-increasing orders; allow only risk-reducing/flattening orders.
3. Launch supervised de-risk plan with prioritized unwind ladder.
4. Increase monitoring cadence to 1–5 minute checkpoints until back inside limits.

### Rollback Path
1. Verify exposures are back under hard limits with independent confirmation.
2. Keep soft caps tightened for cooling-off window (e.g., 1 session).
3. Re-enable strategies only after Risk sign-off and postmortem action checks.
4. Restore normal limits through staged approvals.

### Comms Template
> **Incident:** Risk-Limit Breach  
> **Start Time (UTC):** <YYYY-MM-DD HH:MM>  
> **Impact:** Breach of <limit type> in <book/strategy>; risk controls engaged.  
> **Containment:** Kill-switch active; only risk-reducing flow permitted.  
> **Risk Posture:** Active de-risk in progress under Risk command.  
> **Next Update:** <time in 10–15 min>

---

## Review and Approval Workflow (Research, Risk, Operations)

### Recommended Quick-Start Order of Execution
1. **Research review:** Validate detection signals and rollback scientific integrity.
2. **Risk review:** Validate containment controls, risk posture language, and breach handling.
3. **Operations review:** Validate triage ownership, operational feasibility, and on-call readiness.
4. **Joint sign-off meeting:** Resolve comments and approve final version.
5. **Publish and drill:** Announce adoption and schedule tabletop exercise.

### Approval Record
- **Research Approver:** <name> — <date> — <status>
- **Risk Approver:** <name> — <date> — <status>
- **Operations Approver:** <name> — <date> — <status>
- **Final Approved Version:** <version/tag>
