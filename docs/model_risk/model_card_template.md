# Model Card Template

> Complete this template for every model version. Promotion decisions are blocked until all required sections are filled, reviewed, and signed.

## 1) Objective

- Model name / ID:
- Version:
- Owner:
- Objective summary:
- Intended use:
- Out-of-scope use:

## 2) Assumptions

- Data assumptions (availability, latency, quality):
- Market/operational assumptions:
- Statistical assumptions:
- Dependency assumptions (upstream systems, providers):

## 3) Features

- Feature inventory (name, type, source, transform):
- Feature freshness expectations:
- Missing-data handling strategy:
- Leakage prevention controls:

## 4) Training Window

- Training window start (UTC):
- Training window end (UTC):
- Validation window(s):
- Test window(s):
- Retraining cadence:

## 5) Known Failure Modes

- Failure mode 1:
  - Trigger conditions:
  - Expected impact:
  - Detection signal:
  - Mitigation/fallback:
- Failure mode 2:
  - Trigger conditions:
  - Expected impact:
  - Detection signal:
  - Mitigation/fallback:

## 6) Limits

- Operational limits (latency/cost/capacity):
- Decision limits (where model must not be used):
- Data limits (coverage, staleness, drift sensitivity):
- Compliance/policy limits:

## 7) Monitoring Thresholds

- Quality thresholds:
- Drift thresholds:
- Safety/risk thresholds:
- Reliability thresholds:
- Alert routing and on-call owner:

## 8) Champion/Challenger Governance

- Production strategy:
- Current champion model/version:
- Challenger model/version:
- Monthly comparison cadence owner:
- Out-of-sample quality metrics (monthly):
- Risk-adjusted metrics (monthly):

## 9) Monthly Decision Record

- Decision date (UTC):
- Decision outcome (keep champion / replace / retrain):
- Decision rationale (required):
- Effective date (UTC):
- `model_change_log` entry reference:

## 10) Approval Checklist (required for promotion)

- [ ] All sections above are fully completed (no placeholders).
- [ ] Validation evidence links are attached.
- [ ] Monitoring dashboards and alert routes are attached.
- [ ] Rollback criteria are attached and actionable.
- [ ] Research lead sign-off complete.
- [ ] Risk reviewer sign-off complete.

### Sign-off

- Research lead name:
- Research lead signature/date (UTC):
- Risk reviewer name:
- Risk reviewer signature/date (UTC):

## 11) Archive Record

- Signed model card path: `docs/model_risk/cards/<model-id>__<version>__<yyyy-mm-dd>.md`
- Promotion decision date (UTC):
- Promotion decision outcome:
- Decision approver:
