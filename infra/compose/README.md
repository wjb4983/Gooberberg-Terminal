# compose

Compose files are retained for local development and production-oriented service builds, but the primary supported local developer topology is the dev compose stack:

- `docker-compose.dev.yml`: supported local development stack with Postgres, Redis, and `api-control-plane` published on `127.0.0.1:8000`.
- `docker-compose.prod.yml`: production-oriented baseline used by ops scripts and server image workflows; it is not the primary local quick-start path.

## Supported local quick start

Run from the repository root:

```bash
# 1) Start backend dependencies/API
timeout 240s docker compose -f infra/compose/docker-compose.dev.yml up -d --build postgres redis api-control-plane

# 2) Start the frontend dev server
timeout 8h pnpm --filter @gb/desktop-tauri dev -- --host 0.0.0.0

# 3) Open the VS Code forwarded/browser URL for port 1420
# 4) Confirm the frontend API base URL is http://127.0.0.1:8000

# 5) Run finite smoke checks from a second terminal
timeout 60s ./scripts/dev/check-local-fullstack.sh
```

Stop the local backend stack with:

```bash
timeout 120s pnpm dev:local:down
```
