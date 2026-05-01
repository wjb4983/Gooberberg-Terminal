# Tier-0 Strategy Lineage

This directory tracks end-to-end lineage for Tier-0 strategies in the required mapping format:

`source dataset → transformations → features → model → signal → execution`

## Quick-start (recommended order)

1. Update each strategy lineage file when a pipeline change merges.
2. Verify dataset and transform lineage against `docs/governance/data-inventory.md` and runtime code paths.
3. Confirm model/signal/execution sections still match deployed behavior.
4. Set `last_verified_date` (UTC) and owner in the strategy file.
5. Run monthly lineage review on the first business day of each month.

## Lineage files

- `tier0-momentum-v1.md`

## Monthly review policy

- **Cadence:** monthly (minimum), and additionally after any pipeline/materialization/model/execution contract change.
- **Owner responsibility:** strategy owner must update the lineage within 1 business day after merged changes.
- **Verification evidence:** include PR or commit reference in the "Verification notes" section of each file.
