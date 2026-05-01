# Trading Resilience Drill Log — 2026-05-01

## Scope
This log records completion of:
1. Tabletop drill #1 (data corruption scenario).
2. Tabletop drill #2 (execution venue outage scenario).
3. One controlled live drill in non-prod with alerting + rollback.
4. MTTA/MTTR measurements and action items.

## Recommended Quick-Start Order of Execution
1. **Pre-brief + success criteria** (participants, timeline, observer, comms channel, rollback owner).
2. **Tabletop drill #1** (data corruption scenario).
3. **Tabletop drill #2** (execution venue outage scenario).
4. **Controlled live drill in non-prod** (alerting + rollback validation).
5. **Metrics + retro** (MTTA/MTTR capture, action items, owners, due dates).

---

## Drill #1 — Tabletop (Data Corruption Scenario)
- **Scenario:** Corrupted corporate actions payload causes incorrect adjusted positions and PnL skew.
- **Date (UTC):** 2026-05-01
- **Scheduled:** 13:00–13:45
- **Executed:** 13:02–13:41
- **Facilitator:** Operations on-call
- **Attendees:** Research, Risk, Operations, Platform observer

### Timeline
- **13:02** Injected scenario prompt into incident channel.
- **13:05** Acknowledgement by incident commander (IC).
- **13:10** Trading halt for impacted symbols proposed and approved.
- **13:16** Fallback snapshot + CA reconciliation workflow selected.
- **13:28** Recovery validation checklist completed.
- **13:41** Scenario closed with post-incident notes.

### Outcomes
- Correctly selected containment: halt impacted issuers, freeze CA-dependent analytics, run dual-source reconciliation.
- Rollback path was correctly sequenced and required dual sign-off.

### Measured Metrics
- **MTTA:** 3 minutes (13:02 → 13:05)
- **MTTR (tabletop simulated):** 39 minutes (13:02 → 13:41)

---

## Drill #2 — Tabletop (Execution Venue Outage Scenario)
- **Scenario:** Primary venue session unavailable; order rejects spike and fills collapse.
- **Date (UTC):** 2026-05-01
- **Scheduled:** 14:00–14:45
- **Executed:** 14:01–14:36
- **Facilitator:** Execution operations lead
- **Attendees:** Operations, Risk, Research, Platform observer

### Timeline
- **14:01** Outage scenario declared; reject storm alarms simulated.
- **14:04** IC acknowledges and opens incident bridge.
- **14:08** Pause new submissions to affected venue, cap retries.
- **14:14** Route hedging flow to backup venue; apply conservative collars.
- **14:26** Health-check criteria met in scenario; phased reopen planned.
- **14:36** Incident closed after stabilization checklist walkthrough.

### Outcomes
- Correctly prioritized risk-reducing/hedging flows.
- Team followed phased reopen criteria before removing temporary clamps.

### Measured Metrics
- **MTTA:** 3 minutes (14:01 → 14:04)
- **MTTR (tabletop simulated):** 35 minutes (14:01 → 14:36)

---

## Drill #3 — Controlled Live Drill (Non-Prod)
- **Scenario:** Synthetic market-data freshness degradation in non-prod; validate alerting, on-call response, mitigation, rollback.
- **Date (UTC):** 2026-05-01
- **Scheduled:** 15:00–15:40
- **Executed:** 15:00–15:33
- **Environment:** non-prod
- **Guardrails:** No production credentials; synthetic symbols only; pre-approved rollback owner assigned.

### Steps Executed
1. Enabled synthetic fault injection for data freshness lag.
2. Verified alert fired in monitoring + page routed to on-call.
3. Acknowledged incident and applied mitigation profile.
4. Executed rollback (clear injection, restore baseline routing/threshold profile).
5. Confirmed alert auto-resolved and service health returned to baseline.

### Timeline
- **15:00** Fault injection enabled.
- **15:02** Alert fired.
- **15:05** On-call acknowledged and opened incident channel.
- **15:11** Mitigation profile active.
- **15:22** Rollback initiated (fault cleared + baseline config restored).
- **15:30** Alert resolved.
- **15:33** Live drill closed.

### Measured Metrics
- **MTTA:** 3 minutes (15:02 → 15:05)
- **MTTR:** 28 minutes (15:02 → 15:30)

---

## Consolidated MTTA / MTTR Summary
| Drill | Type | MTTA | MTTR |
|---|---|---:|---:|
| #1 Data Corruption | Tabletop | 3m | 39m |
| #2 Venue Outage | Tabletop | 3m | 35m |
| #3 Non-Prod Live | Controlled live | 3m | 28m |

- **Average MTTA:** 3 minutes
- **Average MTTR:** 34 minutes

## Action Items
1. **Automate incident bridge creation on page receipt** to reduce coordination overhead.
   - **Owner:** Platform Ops
   - **Due:** 2026-05-08
2. **Add explicit “hedging-only mode” checklist card** to venue outage runbook for faster execution.
   - **Owner:** Execution Ops
   - **Due:** 2026-05-06
3. **Add CA dual-source reconciliation quick command snippets** to corruption runbook.
   - **Owner:** Research Engineering
   - **Due:** 2026-05-07
4. **Add dashboard panel for drill MTTA/MTTR trendline** (tabletop vs live).
   - **Owner:** Observability
   - **Due:** 2026-05-13

## Sign-Off
- **Research:** Approved (2026-05-01)
- **Risk:** Approved (2026-05-01)
- **Operations:** Approved (2026-05-01)
