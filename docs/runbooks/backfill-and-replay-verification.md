# Backfill and replay verification runbook

Use this runbook for historical backfills and deterministic replay validation before and after production changes.

## When to use

- schema evolution affecting event payloads or derived state
- materialized-view corruption or gap repair
- release qualification requiring replay parity evidence

## Preconditions

1. Identify affected time window, topics, and downstream consumers.
2. Confirm schema compatibility checks are passing.
3. Prepare isolated output namespace/table prefixes for backfill writes.
4. Confirm current replay baseline artifacts are available.

## Backfill procedure (recommended order)

1. **Dry-run scope audit**
   - estimate event count and storage impact
   - verify no overlap with active mutation workflows
2. **Run backfill in shadow mode**
   - write to shadow tables/topics only
3. **Run replay parity validation**
   - compare baseline vs shadow outcomes
4. **Promote shadow outputs** if parity passes
5. **Publish completion report** with counts, checksums, and diffs

## Replay verification criteria

A replay pass is valid only if all conditions hold:

- event count parity: exact match (or documented intentional filter deltas)
- terminal state parity: no unauthorized drift
- risk decision parity: identical allow/deny outcomes for canonical scenarios
- numerical tolerance parity: configured tolerances respected for floating-point metrics

## Failure handling

If parity fails:

1. Stop promotion immediately.
2. Classify mismatch (schema decode, ordering, stateful dependency, nondeterminism).
3. Open incident and attach first-diff evidence.
4. Fix root cause and rerun from clean shadow namespace.

## Evidence checklist

- backfill command metadata and version identifiers
- replay parity report artifact location
- mismatch ledger (if any) and disposition
- approval sign-off from application and ops owners
