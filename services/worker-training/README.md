# worker-training

Training execution worker for model runs.

## Pipeline rollout controls

To migrate safely from compatibility mode to strict mode without breaking existing runs,
the worker supports feature flags:

- `GB_TRAINING_PIPELINE_STRICT_MODE`
  - Default: `false`
  - When `true`, strict-mode routing can be enabled.
- `GB_TRAINING_PIPELINE_STRICT_MODEL_FAMILIES`
  - Default: empty
  - Comma-separated list of model families to route through strict mode.
  - Empty means strict mode applies to all model families when strict mode is enabled.

Recommended rollout:

1. Deploy with `GB_TRAINING_PIPELINE_STRICT_MODE=false` (global compatibility mode).
2. Enable strict mode for a small family set via `GB_TRAINING_PIPELINE_STRICT_MODEL_FAMILIES`.
3. Expand family coverage progressively until all families are on strict mode.
