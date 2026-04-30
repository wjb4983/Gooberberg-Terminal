# SLOs and latency objectives

This runbook defines service-level objectives (SLOs), error budgets, and operational thresholds for event durability, audit API responsiveness, decision-loop timing, and alert handling.

## 1) Event loss rate SLO

### SLI definition

- **SLI:** `1 - (missing_events / expected_events)` measured from producer acknowledgements to durable consumer visibility.
- Missing event criteria:
  - Event ID acknowledged by producer but not visible in durable storage and replay stream within 60 seconds.
  - Event envelope exists but fails schema decode and is dead-lettered without successful remediation.

### Objective and budget

- **Target:** event loss rate <= **0.01%** per rolling 30 days (durability >= 99.99%).
- **Burn alert:**
  - page when projected 30-day burn > 25% budget in 6 hours.
  - ticket when projected 30-day burn > 10% budget in 24 hours.

### Measurement notes

- Partition by topic (`risk.decision`, `jobs.lifecycle`, `portfolio.snapshot`).
- Track both raw drops and irrecoverable decode failures.
- Exclude intentionally filtered events with explicit policy labels.

## 2) Audit API latency SLO

### SLI definition

- **Endpoint scope:** `/api/v1/audit/*` read routes.
- **Latency SLI:** server-side request latency measured at API boundary.

### Objective

- **p50 <= 120 ms**
- **p95 <= 350 ms**
- **p99 <= 800 ms**
- Error rate for audit routes <= **0.1%** per rolling 30 days.

### Alert thresholds

- Page when p95 > 500 ms for 15 minutes or error rate > 1% for 10 minutes.
- Ticket when p95 > 350 ms for 30 minutes.

## 3) Decision loop latency budget

The decision loop budget covers intent ingestion through risk decision publication.

## End-to-end budget

- **Total budget (p95): <= 1,500 ms**

Budget allocation:

1. Intake + validation: **200 ms**
2. Feature/materialized state fetch: **500 ms**
3. Risk policy evaluation + scoring: **400 ms**
4. Decision persistence + event publish: **250 ms**
5. Safety margin: **150 ms**

### Guardrails

- Any stage exceeding its budget for > 10 minutes opens an incident ticket.
- If end-to-end p95 > 1,500 ms for 15 minutes, trigger SEV-2 response.
- If end-to-end p99 > 3,000 ms for 10 minutes, trigger SEV-1 response when live trading is impacted.

## 4) Alerting MTTA and MTTR SLOs

### Definitions

- **MTTA:** mean time from alert fire to human acknowledgement.
- **MTTR:** mean time from incident creation to mitigated service restoration.

### Objectives

- **SEV-1:** MTTA <= 5 minutes, MTTR <= 45 minutes.
- **SEV-2:** MTTA <= 15 minutes, MTTR <= 4 hours.
- **SEV-3:** MTTA <= 1 business day, MTTR <= 5 business days.

### Breach policy

- Two consecutive monthly breaches require corrective action plan with owner and due date.
- Quarterly review must adjust staffing, alert routing, or automation where breach root cause is operational toil.

## 5) Review cadence and ownership

- **Primary owner:** Platform/Ops lead.
- **Review cadence:** monthly SLO scorecard, quarterly target recalibration.
- **Inputs:** incident timeline docs, replay parity reports, audit latency dashboards, and on-call metrics.
