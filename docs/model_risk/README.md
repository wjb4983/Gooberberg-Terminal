# Model Risk Cards

This directory defines the required model-card workflow for promotion decisions.

## Requirements

1. A model card based on `docs/model_risk/model_card_template.md` must be fully filled before any promotion decision.
2. Each production strategy must define a challenger model that is evaluated against the current champion.
3. Champion-vs-challenger comparisons must run monthly using out-of-sample quality and risk-adjusted metrics.
4. Promotion is blocked unless the approval checklist is complete, including:
   - Research lead sign-off
   - Risk reviewer sign-off
5. Every monthly comparison requires a written decision to keep the champion, replace with the challenger, or retrain.
6. Every decision must be recorded in `model_change_log`.
7. Signed model cards must be archived in `docs/model_risk/cards/` using the naming format:
   - `<model-id>__<version>__<yyyy-mm-dd>.md`

## Quick start (recommended order)

1. Copy the template and create a candidate card.
2. Fill objective, assumptions, features, and training window.
3. Fill known failure modes, limits, and monitoring thresholds.
4. Define one challenger model for each production strategy and document comparison metrics.
5. Run monthly out-of-sample and risk-adjusted champion-vs-challenger evaluation.
6. Write the decision (keep champion, replace, or retrain) and update `model_change_log`.
7. Complete the approval checklist and gather required sign-offs.
8. Save signed card in `docs/model_risk/cards/`.
9. Reference the archived card in promotion artifacts/PR.
