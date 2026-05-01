# Release Stage Gates: Research → Paper → Prod

This checklist defines required stage-gate exits and promotion blockers for model lifecycle transitions from **Research** to **Paper** to **Prod**.

## Promotion Policy (Hard Block)

A promotion request is **automatically blocked** when any required artifact is missing, stale, or unapproved for the current candidate build.

- Missing artifact status: **BLOCKED**
- Artifact exists but not approved/signed: **BLOCKED**
- Artifact not traceable to exact candidate version: **BLOCKED**

No manual override is allowed without explicit risk-committee exception documented in the risk sign-off.

## Required Artifacts (for every promotion)

1. **Experiment metadata**
   - Includes: hypothesis, dataset/version, feature set hash, training config, code commit SHA, run IDs, metrics summary.
2. **QA report**
   - Includes: test scope, deterministic replay checks, regression results, failure analysis, pass/fail verdict.
3. **Model card**
   - Includes: intended use, non-goals, performance by segment, limitations, monitoring thresholds.
4. **Risk sign-off**
   - Includes: model risk review outcome, approver names/roles, dated approval, residual risk acceptance.
5. **Rollback plan**
   - Includes: trigger conditions, owner on-call, rollback steps, data backfill/reconciliation plan, max recovery time.

---

## Stage Gate Checklist

### Gate 1: Research Exit (Research → Paper)

**Exit criteria (all required):**

- [ ] Experiment metadata is complete and attached to the candidate.
- [ ] QA report for research scope is complete with explicit pass verdict.
- [ ] Draft model card is created with known limits and intended use.
- [ ] Preliminary risk sign-off is recorded by model owner + risk reviewer.
- [ ] Draft rollback plan exists for paper deployment environment.

**Promotion decision:**

- If **any** item above is unchecked: **BLOCKED**.
- If all items are checked: **APPROVED for Paper gate intake**.

### Gate 2: Paper Exit (Paper → Prod Candidate)

**Exit criteria (all required):**

- [ ] Experiment metadata updated to paper candidate version (immutable links).
- [ ] Full QA report includes integration, load, and replay validation.
- [ ] Model card is updated with paper evaluation results and caveats.
- [ ] Formal risk sign-off approved by designated risk authority.
- [ ] Tested rollback plan validated in paper/staging environment.

**Promotion decision:**

- If **any** item above is unchecked: **BLOCKED**.
- If all items are checked: **APPROVED for Prod readiness review**.

### Gate 3: Prod Exit (Prod Candidate → Prod)

**Exit criteria (all required):**

- [ ] Final experiment metadata matches exact production artifact digest/version.
- [ ] Production QA report includes go-live checks and canary acceptance.
- [ ] Final model card published in canonical model risk repository.
- [ ] Final risk sign-off includes date/time, approver, and deployment scope.
- [ ] Production rollback plan is approved and on-call team acknowledged.

**Promotion decision:**

- If **any** item above is unchecked: **BLOCKED**.
- If all items are checked: **APPROVED for production rollout**.

---

## Quick-Start Tasks (Recommended Order)

1. Create/attach **experiment metadata** for the candidate build.
2. Run validation and publish **QA report**.
3. Update and publish **model card** with current metrics/limits.
4. Obtain **risk sign-off** from required approvers.
5. Finalize and test **rollback plan**.
6. Execute stage-gate checklist and record pass/block decision.

## Audit Record Template

For each promotion request, capture:

- Candidate ID / model version:
- Source stage → target stage:
- Artifact links (metadata, QA, model card, risk sign-off, rollback):
- Decision (APPROVED/BLOCKED):
- Reviewer:
- Timestamp (UTC):
- Notes / exceptions:
