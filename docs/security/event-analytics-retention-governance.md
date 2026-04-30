# Event and Analytics Data Governance Boundaries

## Access roles and least-privilege boundaries

The control plane enforces three operational roles that map to API scopes:

1. `viewer` (`control-plane:read`): can read datasets, lineage, and audit records.
2. `operator` (`control-plane:write`): can execute non-admin mutations such as job submissions.
3. `admin` (`control-plane:admin`): can perform privileged governance actions such as model-config mutation.

Least privilege expectations:

- Human users should be provisioned as `viewer` by default and elevated only for explicit workflows.
- Service-to-service tokens should use the narrowest role and be rotated with bounded expiry.
- Audit/replay query access should be limited to `viewer`+ and tracked via immutable access records.

## Immutable audit-access logging

Sensitive audit query surfaces (decision/order/fill/trace lookups, event listing, and replay queries) must emit an append-only access record that captures:

- timestamp (`queried_at`)
- token identity (`token_id`)
- granted scope (`scope`)
- query endpoint (`endpoint`)
- query filters (`filters`)

The implementation is append-only and does not expose mutation or deletion APIs. Operational tamper resistance depends on shipping copies to durable centralized logs (SIEM/WORM storage) during deployment.

## Retention and archival policy boundaries

### Event dataset boundary

Event datasets include raw market events, strategy lifecycle events, risk decisions, and execution telemetry.

- **Hot retention:** 30 days in primary OLTP/event stores for low-latency operational queries.
- **Warm retention:** 180 days in lower-cost query stores for investigations and post-incident replay.
- **Cold archive:** 7 years in immutable object storage for regulatory and legal hold requirements.

### Analytics dataset boundary

Analytics datasets include derived KPIs, model-evaluation aggregates, and dashboard-serving summaries.

- **Hot retention:** 90 days for active dashboards.
- **Warm retention:** 365 days for trend and seasonality analysis.
- **Cold archive:** 3 years unless tied to regulated decision support, where 7-year archival applies.

## Compliance constraints

- PII or secrets must not be included in event payloads unless explicitly approved and encrypted at rest/in transit.
- Deletion workflows for privacy requests apply to identity-linked analytical projections, while legally required regulated event records may be exempt and moved to restricted archive tiers.
- Cross-border replication must respect data residency policy before enabling multi-region backups.

## Quick-start implementation order

1. Provision `viewer`/`operator`/`admin` tokens and migrate existing broad scopes to least-privilege mappings.
2. Enable immutable audit-access ledger emission on all sensitive audit query endpoints.
3. Export append-only audit access logs to centralized immutable storage.
4. Configure lifecycle policies for event and analytics datasets (hot/warm/cold tiers).
5. Validate compliance controls (encryption, residency, privacy exceptions) in release checklists.
