# Blameless postmortem template

Use this template for every SEV-1/SEV-2 incident and any SEV-3 incident that repeats.

## Quick-start implementation tasks (recommended order)

1. **Open incident record** with incident ID, severity, and incident class.
2. **Build timeline** from first symptom through full recovery.
3. **Document impact** (users, duration, financial/operational impact).
4. **Identify root cause** and **contributing factors** using evidence.
5. **Create CAPAs** (corrective and preventive actions) with all mandatory fields.
6. **Schedule weekly CAPA review** until every CAPA is closed.
7. **Update recurrence tracking** for the incident class and report trend.

## 1) Incident metadata

- Incident ID:
- Title:
- Date opened (UTC):
- Date resolved (UTC):
- Severity (SEV-1/2/3):
- Incident class (e.g., API, WS, Redis, Postgres, Risk, Data):
- Incident commander:
- Participants:

## 2) Executive summary

- What happened:
- Customer/business impact:
- Recovery summary:

## 3) Timeline (UTC)

| Timestamp | Event | Owner | Evidence/Link |
|---|---|---|---|
|  |  |  |  |

## 4) Detection and response

- Detection source (alert, user report, synthetic check):
- Time to detect (TTD):
- Time to mitigate (TTM):
- Time to recover (TTR):
- What worked well:
- What was difficult:

## 5) Root cause analysis (blameless)

### Root cause

- Primary root cause statement:
- Supporting evidence:
- Why this was possible in the system:

### Contributing factors

List each contributing factor separately.

1. Factor:
   - Evidence:
   - Control gap:
2. Factor:
   - Evidence:
   - Control gap:

## 6) CAPA plan (mandatory fields)

> Every CAPA must include owner, due date, and verification evidence.

| CAPA ID | Type (Corrective/Preventive) | Action description | **Owner (mandatory)** | **Due date (mandatory)** | **Verification evidence (mandatory)** | Status (Open/In progress/Closed) |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  | Open |

## 7) CAPA governance

- Weekly CAPA review cadence: Every **Monday** (or next business day) until all CAPAs are closed.
- Review owner:
- Escalation rule: CAPAs overdue by >7 days escalate to Engineering + Risk leadership.

## 8) Recurrence tracking

Track recurrence by incident class to verify that CAPAs reduce repeat failures.

- Incident class:
- Lookback window (recommended 90 days):
- Total incidents in class:
- Recurring incidents in class:
- **Recurrence rate** = recurring incidents / total incidents
- Trend vs prior period (up/down/flat):
- Required follow-up if rate increases:

## 9) Follow-up documentation updates

- Runbooks updated:
- Architecture/ADR updates:
- Monitoring/alert updates:
- Training or process changes:

## 10) Sign-off

- Incident commander sign-off:
- Engineering lead sign-off:
- Risk/Compliance sign-off (if applicable):
- Closure date (UTC):
