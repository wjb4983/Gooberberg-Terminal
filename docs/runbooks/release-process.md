# Release process runbook (skeleton)

## Versioning policy

This monorepo uses **Semantic Versioning** for release tags:

- `MAJOR`: breaking changes.
- `MINOR`: backwards-compatible feature additions.
- `PATCH`: backwards-compatible fixes.

Release tags should use the `v` prefix (example: `v1.4.2`). Script inputs expect plain semver (`1.4.2`) and can be mapped from the tag by removing the prefix.

## Release artifacts

A release produces:

1. Version metadata JSON (`dist/version-metadata.json` by default).
2. Desktop build artifacts (placeholder output path `dist/desktop/`).
3. Container images tagged by release version.

## Operator checklist

1. Confirm branch is clean and checks pass.
2. Select release version and create a release branch/tag.
3. Generate version metadata.
4. Build desktop artifacts.
5. Build server images and optionally push registry tags.
6. Draft notes from `docs/release-notes-template.md`.

## Scripted flow

```bash
VERSION=0.1.0

timeout 2m scripts/release/gen-version-metadata.sh "$VERSION"
timeout 30m scripts/release/build-desktop-artifacts.sh "$VERSION"
timeout 90m scripts/release/build-push-server-images.sh "$VERSION"
```

To push server images:

```bash
PUSH_IMAGES=true timeout 90m scripts/release/build-push-server-images.sh "$VERSION" ghcr.io/<org>/gooberberg-terminal
```

## Non-goals (current state)

- No cloud deployment orchestration.
- No automatic progressive rollout.
- No infrastructure mutation.

This runbook intentionally stops at validated build artifacts and registry push readiness.
