# Contributing

Thanks for contributing to the Gooberberg Terminal monorepo.

## Scope

This repository currently provides structure and documentation only. Please keep early contributions focused on:

- clear service/library boundaries,
- developer tooling,
- reproducible build and lint workflows,
- architecture and runbook documentation.

Avoid adding deep domain logic unless the relevant service contract and ownership are documented first.

## Branching & PRs

- Use short-lived feature branches.
- Keep PRs focused and atomic.
- Include a concise summary, rationale, and follow-up items.

## Conventions

- Favor explicit naming and small modules.
- Keep service interfaces explicit and versionable.
- Route all live execution intent through central risk/execution authority (`service-risk-exec`).

## Documentation Expectations

When adding or changing components:

- Update the nearest `README.md` with purpose, interfaces, and dependencies.
- Update runbooks in `docs/runbooks` if operational behavior changes.
- Keep examples and commands non-interactive and automation-friendly.
