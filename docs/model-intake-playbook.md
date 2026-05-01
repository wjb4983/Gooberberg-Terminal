# Model Intake Playbook

This playbook defines the required path for onboarding a model from initial idea through rollout tracking.

## Scope and dependency

- Complexity: **Small**
- Dependency: **Task 15 must be complete before intake starts**
- Validation method: **Manual docs review checklist**

## PR reference checklist (copy into PR description)

Use this checklist as the reference block in every model-intake PR.

- [ ] **Idea stage complete**: problem statement, expected user impact, and success criteria are documented.
- [ ] **Metadata stage complete**: required model metadata fields are present and reviewed.
- [ ] **Adapter scaffold stage complete**: scaffold generated and ownership assigned.
- [ ] **Validation stage complete**: safety and quality gates pass, including all default QA scenarios.
- [ ] **Rollout status stage complete**: rollout state is set and linked to monitoring.
- [ ] **Required documentation attached**: all required fields and evidence links are included.

## Required workflow

### 1) Idea

Create a short intake brief before any code change.

Required outputs:

- Problem statement
- Intended users / workflows
- Baseline vs target outcome
- Success metrics and measurement plan
- Risks, assumptions, and unknowns
- Owner and reviewer

Safety gate:

- **Stop** if the model goal conflicts with policy, introduces unmitigated harm risk, or lacks an accountable owner.

### 2) Metadata

Define model metadata in the repository catalog and documentation.

Required metadata fields:

- Model name and unique ID
- Version and lifecycle phase (proposal, experimental, staged, production, deprecated)
- Model family / type
- Training data provenance summary
- Intended use and out-of-scope use
- Input/output schema contract
- Safety constraints and guardrails
- Evaluation datasets and acceptance thresholds
- Runtime requirements (latency, memory, cost budget)
- Monitoring signals and alert thresholds
- Rollback criteria and fallback behavior
- Owners (engineering + product + on-call)

Safety gates:

- **Stop** if provenance or usage boundaries are missing.
- **Stop** if acceptance thresholds are undefined.
- **Stop** if rollback criteria are not documented.

### 3) Adapter scaffold

Create the adapter scaffold that connects runtime interfaces to model-specific logic.

Required scaffold components:

- Adapter entrypoint and interface implementation
- Config template with defaults and environment mapping
- Structured logging hooks
- Metrics hooks (success/error/latency)
- Feature flag or rollout guard
- Basic failure handling and fallback path
- Ownership annotation in code/docs

Safety gates:

- **Stop** if adapter bypasses existing authn/authz or safety middleware.
- **Stop** if fallback behavior is undefined for adapter failure.

### 4) Validation

Run pre-rollout validation and record evidence links.

Required validation documentation:

- Functional checks against declared input/output contract
- Default dataset split policy documented and applied: **time-ordered train/validate/test split** plus **walk-forward window results**
- Evaluation results against acceptance thresholds
- Mandatory stress scenarios: **high-volatility regime**, **low-liquidity regime**, and **spread-widening regime**
- Strategy report sections: **robustness**, **turnover stability**, **capacity**, and **slippage sensitivity**
- Safety review outcomes (known bad-case coverage)
- Operational checks (latency/cost/retry behavior)
- Manual docs review checklist completion

Safety gates:

- **Stop** if any critical safety scenario fails.
- **Stop** if any mandatory stress scenario fails (high-volatility, low-liquidity, spread-widening).
- **Stop** if observed quality is below documented threshold.
- **Stop** if operational budget limits are exceeded.

### 5) Rollout status

Track rollout state explicitly and keep status current.

Allowed rollout states:

- `proposal`
- `experimental`
- `paper-trading`
- `staged`
- `production`
- `paused`
- `rollback`
- `deprecated`

Required rollout status fields:

- Current state
- Change date (UTC)
- Approver
- Linked validation artifact(s)
- Blast radius and enablement scope
- Monitoring dashboard link
- Incident/rollback link (if applicable)

Safety gates:

- **Stop** production promotion without staged validation evidence.
- **Stop** promotion to `staged` or `paper-trading` unless **all default QA scenarios pass**.
- **Stop** state transition if monitoring and on-call ownership are missing.

## Required documentation fields (single reference list)

Every intake record/PR must include:

- Intake summary
- Metadata field set (from section 2)
- Adapter scaffold location(s)
- Validation evidence links
- Rollout status fields
- Risk log and open issues
- Owner + reviewer sign-off

## Manual docs review checklist

- [ ] Playbook steps are followed in order: idea → metadata → adapter scaffold → validation → rollout status.
- [ ] Validation includes default split policy (time-ordered train/validate/test + walk-forward windows).
- [ ] Validation includes mandatory stress scenarios (high-volatility, low-liquidity, spread-widening).
- [ ] Strategy report includes robustness, turnover stability, capacity, and slippage sensitivity sections.
- [ ] PR checklist block is present and fully completed.
- [ ] Required documentation fields are complete and non-placeholder.
- [ ] Safety gates are acknowledged with pass/fail outcomes.
- [ ] Rollout status is set with date, approver, and monitoring links.
