# compose

- `docker-compose.dev.yml`: local development stack with convenience defaults.
- `docker-compose.prod.yml`: production-oriented, hardened baseline with deny-by-default exposure.
  - Postgres/Redis are private-only.
  - API is internal by default.
  - Optional profiles:
    - `nginx` profile for TLS termination via reverse proxy.
    - `loopback` profile for 127.0.0.1-bound API access.
