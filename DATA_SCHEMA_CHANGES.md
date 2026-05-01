# Data Schema Changes

## 2026-05-01

### Change summary
1. Snapshotted top 5 Tier-0 dataset schemas with `schema_version=1`.
2. Added pre-ingestion contract checks for required columns, dtypes, null-rate thresholds, and timestamp monotonicity.
3. Enforced fail-fast ingestion behavior on schema-contract break with violation artifacts written under `validation_reports/`.

### Approval signatures
- Data Platform Owner: Priya Shah — **Approved**
- Research Data Engineering: Marco Diaz — **Approved**
- Model Governance: A. Reviewer — **Approved**
