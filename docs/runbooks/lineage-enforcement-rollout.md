# Lineage Enforcement Rollout Plan

## Scope
This runbook defines the recommended rollout order for lineage enforcement flags covering:
- lineage payload completeness,
- artifact manifest completeness,
- lineage schema version compatibility.

## Quick-start tasks (recommended order)
1. **Baseline observability first**: ship counters/dashboards before any blocking behavior.
2. **Enable Observe mode** in all non-prod and canary prod slices.
3. **Promote to Soft gate** after Observe acceptance criteria are met.
4. **Promote to Hard gate** after Soft gate error-rate and migration targets are met.
5. **Enable legacy cutoff date block** for deprecated lineage versions.
6. **Remove deprecated lineage write paths** after cutoff soak window.

---

## Phase 1 — Observe mode (no hard failures)

### Flag behavior
- `GB_LINEAGE_ENFORCEMENT_MODE=observe`
- Requests are accepted even if lineage/artifact fields are incomplete.
- Service emits structured warnings and gate-evaluation telemetry for every run.

### Acceptance criteria
- 100% of run creation requests emit a gate evaluation event with reason codes.
- 0 hard rejections attributable to lineage gate logic.
- Dashboard data quality check passes for 7 consecutive days:
  - gate failure reasons populated,
  - lineage version tags populated,
  - environment and service dimensions present.

### Dashboard metrics (required)
- `lineage_gate_evaluations_total{mode="observe", outcome="warn|pass", reason_code}`
- `lineage_gate_missing_fields_total{field, severity}`
- `lineage_version_adoption_ratio{lineage_version}`
  - definition: `runs_with_version / total_runs`

### Internal announcement + migration doc updates
- Publish "Observe mode starts" announcement to engineering + ML channels.
- Link migration doc section: "How to supply full lineage and manifest fields".
- Include warning reason taxonomy and sample payload snippets.

---

## Phase 2 — Soft gate (block severe-only)

### Flag behavior
- `GB_LINEAGE_ENFORCEMENT_MODE=soft_gate`
- Fail requests only for severe missing fields.
- Continue warnings for non-severe deficiencies.

### Severe fields (block list)
- `lineage.dataset_fingerprint`
- `lineage.code_hash`
- `lineage.config_digest`
- `lineage.seed`

### Non-severe fields (warn list)
- optional lineage enrichment fields,
- non-critical manifest metadata fields,
- optional integrity decorations.

### Acceptance criteria
- Severe-missing rejection rate < 1% for 7 consecutive days in each target environment.
- 95%+ of new runs include full required lineage core fields.
- No increase >10% in run submission p95 latency caused by gate checks.

### Dashboard metrics (required)
- `lineage_gate_failures_total{mode="soft_gate", reason_code, severity="severe"}`
- `lineage_gate_warnings_total{mode="soft_gate", reason_code, severity="warning"}`
- `lineage_version_adoption_ratio{lineage_version}` with SLO alert when deprecated version usage > 5%.

### Internal announcement + migration doc updates
- Publish "Soft gate enabled" with exact severe block list.
- Provide remediation cookbook mapping `reason_code -> fix`.
- Document dry-run endpoint/CLI (if available) to pre-validate payloads.

---

## Phase 3 — Hard gate (full enforcement)

### Flag behavior
- `GB_LINEAGE_ENFORCEMENT_MODE=hard_gate`
- Enforce full required lineage and artifact manifest completeness before run acceptance.

### Required success conditions
A run is accepted only when all are present and valid:
1. Full required lineage core fields.
2. Required lineage schema version is supported.
3. Artifact manifest is present with required roles and integrity metadata.

### Acceptance criteria
- 99%+ successful first-attempt submissions from migrated producers for 14 consecutive days.
- 0 accepted runs with missing required lineage core fields.
- 0 accepted runs with incomplete required artifact manifest roles.

### Dashboard metrics (required)
- `lineage_gate_failures_total{mode="hard_gate", reason_code}`
- `lineage_artifact_manifest_failures_total{reason_code, artifact_role}`
- `lineage_version_adoption_ratio{lineage_version}` with deprecation burn-down chart.

### Internal announcement + migration doc updates
- Publish "Hard gate go-live" date at least 2 weeks before enablement.
- Share owner-by-owner migration status and exception process.
- Update runbook with incident triage for top hard-fail reason codes.

---

## Phase 4 — Legacy cutoff date (deprecated version block)

### Flag behavior
- `GB_LINEAGE_DEPRECATED_VERSION_CUTOFF_UTC=<ISO-8601 timestamp>`
- After cutoff, new runs using deprecated lineage schema versions are rejected.

### Acceptance criteria
- 0 successful submissions using deprecated lineage versions after cutoff timestamp.
- 100% of active producers on supported lineage versions before cutoff day.
- Exception list is empty (or formally approved with expiration) by cutoff + 7 days.

### Dashboard metrics (required)
- `lineage_legacy_version_block_total{lineage_version, reason_code="DEPRECATED_VERSION_CUTOFF"}`
- `lineage_version_adoption_ratio{lineage_version}` with explicit supported/deprecated grouping.
- `lineage_cutoff_readiness{producer_id, lineage_version}` for migration tracking.

### Internal announcement + migration doc updates
- Announce exact cutoff timestamp in UTC and local business timezone.
- Send reminders at T-14d, T-7d, T-3d, T-24h.
- Publish final migration FAQ and support escalation path.

---

## Timeline template (fill with concrete dates)
- **T0:** Observe mode enabled.
- **T0 + 2 weeks:** Soft gate enabled.
- **T0 + 4 weeks:** Hard gate enabled.
- **T0 + 6 weeks:** Deprecated lineage version cutoff enforced.

If acceptance criteria are not met, do not advance phases; extend current phase by 1 week and re-evaluate.

## Migration doc checklist (must exist before Soft gate)
- Producer payload examples for compliant lineage + manifest.
- Field-by-field requirements table (required vs optional, severe vs warning).
- Reason-code remediation guide.
- Version compatibility policy and deprecation lifecycle.
