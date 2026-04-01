# Release notes template

## Release metadata

- Version: `vX.Y.Z`
- Date (UTC): `YYYY-MM-DD`
- Commit SHA: `<short-sha>`
- Release manager: `<name>`

## Summary

Brief summary of what changed and why.

## Highlights

- Feature:
- Fix:
- Internal:

## Compatibility and migration notes

- Breaking changes:
- Required migrations:
- Rollback notes:

## Artifact manifest

- Desktop artifact location: `dist/desktop/...`
- Version metadata: `dist/version-metadata.json`
- Server image tags:
  - `ghcr.io/<org>/gooberberg-terminal/api-control-plane:vX.Y.Z`
  - `ghcr.io/<org>/gooberberg-terminal/orchestrator:vX.Y.Z`
  - `ghcr.io/<org>/gooberberg-terminal/service-data:vX.Y.Z`
  - `ghcr.io/<org>/gooberberg-terminal/service-inference-live:vX.Y.Z`
  - `ghcr.io/<org>/gooberberg-terminal/service-portfolio-state:vX.Y.Z`
  - `ghcr.io/<org>/gooberberg-terminal/service-risk-exec:vX.Y.Z`
  - `ghcr.io/<org>/gooberberg-terminal/worker-research:vX.Y.Z`
  - `ghcr.io/<org>/gooberberg-terminal/worker-training:vX.Y.Z`

## Validation checklist

- [ ] Lint checks passed.
- [ ] Tests passed.
- [ ] Desktop build completed.
- [ ] Server images built.
- [ ] Optional image push completed.
- [ ] No cloud deployment performed from this workflow.
