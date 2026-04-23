from __future__ import annotations

from collections.abc import Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings

_READ_ONLY_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_READ_SCOPES = frozenset(
    {
        "control-plane:read",
        "control-plane:write",
        "control-plane:full",
        "control-plane:admin",
    }
)
_MUTATING_SCOPES = frozenset({"control-plane:write", "control-plane:full", "control-plane:admin"})


class BearerTokenAuthMiddleware(BaseHTTPMiddleware):
    """Static bearer token auth with route-level scope checks.

    The middleware validates a configured bearer token and enforces least-privilege
    scopes based on HTTP action class:
      * read-only control-plane routes: ``control-plane:read`` or stronger
      * mutating control-plane routes: ``control-plane:write`` or stronger
    """

    def __init__(self, app, *, health_paths: set[str] | None = None) -> None:
        super().__init__(app)
        self._health_paths = health_paths or {"/api/v1/health", "/healthz"}

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        granted_scopes = _normalize_scopes(settings.api_auth_scope)
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

        required_scope, allowed_scopes = _required_scope_for_request(request)
        if not granted_scopes.intersection(allowed_scopes):
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Forbidden",
                    "required_scope": required_scope,
                    "granted_scope": settings.api_auth_scope,
                },
            )

        return await call_next(request)


def _normalize_scopes(scope_config: str) -> set[str]:
    tokens: Iterable[str] = scope_config.split(",") if scope_config else ()
    return {token.strip() for token in tokens if token.strip()}


def _required_scope_for_request(request: Request) -> tuple[str, frozenset[str]]:
    if request.method.upper() in _READ_ONLY_METHODS:
        return "control-plane:read", _READ_SCOPES

    return "control-plane:write", _MUTATING_SCOPES
