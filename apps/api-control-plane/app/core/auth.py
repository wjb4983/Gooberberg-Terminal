from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings


class BearerTokenAuthMiddleware(BaseHTTPMiddleware):
    """Pragmatic static bearer token auth for private deployments.

    v1 behavior validates a single configured token and stores a scope placeholder
    on request state for future per-endpoint authorization.
    """

    def __init__(self, app, *, health_paths: set[str] | None = None) -> None:
        super().__init__(app)
        self._health_paths = health_paths or {"/api/v1/health", "/healthz"}

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        request.state.auth_scope = settings.api_auth_scope

        if not settings.api_auth_token or request.url.path in self._health_paths:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        expected = f"Bearer {settings.api_auth_token}"
        if auth_header != expected:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Unauthorized",
                    "scope": settings.api_auth_scope,
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)
