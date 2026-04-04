# api-control-plane

Placeholder package for the component at path `apps/api-control-plane`.

## Purpose

This directory is reserved for future implementation.

## Status

- Skeleton only.
- No domain implementation logic yet.

## After making code updates

Use this quick checklist each time you change code and want to restart the API server:

1. Reinstall dependencies for the package (from repo root):
   ```bash
   uv pip install -e apps/api-control-plane
   ```
2. Run the API test suite:
   ```bash
   pytest apps/api-control-plane/tests -q
   ```
3. Restart the server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Docker workflow

If you run the server in Docker, rebuild and restart after code updates:

```bash
docker compose -f infra/compose/docker-compose.dev.yml build api-control-plane
docker compose -f infra/compose/docker-compose.dev.yml up -d api-control-plane
```
