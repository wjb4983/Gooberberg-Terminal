# Model Risk Cards

This directory defines the required model-card workflow for promotion decisions.

## Requirements

1. A model card based on `docs/model_risk/model_card_template.md` must be fully filled before any promotion decision.
2. Promotion is blocked unless the approval checklist is complete, including:
   - Research lead sign-off
   - Risk reviewer sign-off
3. Signed model cards must be archived in `docs/model_risk/cards/` using the naming format:
   - `<model-id>__<version>__<yyyy-mm-dd>.md`

## Quick start (recommended order)

1. Copy the template and create a candidate card.
2. Fill objective, assumptions, features, and training window.
3. Fill known failure modes, limits, and monitoring thresholds.
4. Complete the approval checklist and gather required sign-offs.
5. Save signed card in `docs/model_risk/cards/`.
6. Reference the archived card in promotion artifacts/PR.
