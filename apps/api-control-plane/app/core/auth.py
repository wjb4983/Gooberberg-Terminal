from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
import hmac
import logging

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
_ADMIN_SCOPES = frozenset({"control-plane:admin", "control-plane:full"})
_ADMIN_PATH_PREFIXES = ("/api/v1/model-configs",)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthCredential:
    token_id: str
    token: str
    scopes: frozenset[str]
    expires_at: datetime | None


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
        credentials = _load_credentials(settings)
        revoked_token_ids = _normalize_scopes(settings.api_auth_revoked_token_ids)
        request.state.auth_scope = settings.api_auth_scope

        if not credentials or request.url.path in self._health_paths or request.method.upper() == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            _log_auth_failure(request, auth_result="missing_header")
            return _auth_error_response(detail="Unauthorized", status_code=401, auth_result="missing_header")

        provided_token = auth_header[len("Bearer ") :]
        matching_credential = next(
            (credential for credential in credentials if hmac.compare_digest(provided_token, credential.token)),
            None,
        )
        if matching_credential is None:
            _log_auth_failure(request, auth_result="invalid_token")
            return _auth_error_response(detail="Unauthorized", status_code=401, auth_result="invalid_token")

        request.state.auth_scope = ",".join(sorted(matching_credential.scopes))
        request.state.auth_token_id = matching_credential.token_id

        if matching_credential.token_id in revoked_token_ids:
            _log_auth_failure(
                request,
                auth_result="revoked_token",
                token_id=matching_credential.token_id,
            )
            return _auth_error_response(
                detail="Unauthorized",
                status_code=401,
                auth_result="revoked_token",
            )

        if matching_credential.expires_at is not None and datetime.now(tz=UTC) >= matching_credential.expires_at:
            _log_auth_failure(
                request,
                auth_result="expired_token",
                token_id=matching_credential.token_id,
            )
            return _auth_error_response(
                detail="Session expired. Please re-authenticate.",
                status_code=401,
                auth_result="expired_token",
            )

        required_scope, allowed_scopes = _required_scope_for_request(request)
        if not matching_credential.scopes.intersection(allowed_scopes):
            _log_auth_failure(
                request,
                auth_result="forbidden_scope",
                token_id=matching_credential.token_id,
                required_scope=required_scope,
                granted_scopes=",".join(sorted(matching_credential.scopes)),
            )
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Forbidden",
                    "required_scope": required_scope,
                    "granted_scope": ",".join(sorted(matching_credential.scopes)),
                },
            )

        response = await call_next(request)
        if len(credentials) > 1:
            response.headers["X-Auth-Token-Mode"] = "dual-accept"
        return response


def _normalize_scopes(scope_config: str) -> set[str]:
    tokens: Iterable[str] = scope_config.split(",") if scope_config else ()
    return {token.strip() for token in tokens if token.strip()}


def _required_scope_for_request(request: Request) -> tuple[str, frozenset[str]]:
    if _requires_admin_scope(request.url.path, request.method):
        return "control-plane:admin", _ADMIN_SCOPES

    if request.method.upper() in _READ_ONLY_METHODS:
        return "control-plane:read", _READ_SCOPES

    return "control-plane:write", _MUTATING_SCOPES


def _requires_admin_scope(path: str, method: str) -> bool:
    if method.upper() in _READ_ONLY_METHODS:
        return False
    return any(path.startswith(prefix) for prefix in _ADMIN_PATH_PREFIXES)


def _load_credentials(settings) -> list[AuthCredential]:
    parsed_credentials = _parse_structured_credentials(settings.api_auth_tokens)
    if parsed_credentials:
        return parsed_credentials

    if not settings.api_auth_token:
        return []

    return [
        AuthCredential(
            token_id="legacy-static",
            token=settings.api_auth_token,
            scopes=frozenset(_normalize_scopes(settings.api_auth_scope)),
            expires_at=None,
        )
    ]


def _parse_structured_credentials(raw_value: str) -> list[AuthCredential]:
    credentials: list[AuthCredential] = []
    for index, token_entry in enumerate(raw_value.split(";"), start=1):
        entry = token_entry.strip()
        if not entry:
            continue
        parts = [part.strip() for part in entry.split("|", maxsplit=3)]
        if len(parts) != 4:
            logger.warning("ignoring invalid auth token record", extra={"event": "auth_config_invalid"})
            continue
        token_id, token_secret, scope_blob, expires_blob = parts
        if not token_secret:
            logger.warning("ignoring empty auth token record", extra={"event": "auth_config_invalid"})
            continue
        try:
            expires_at = _parse_expires_at(expires_blob)
        except ValueError:
            logger.warning(
                "ignoring auth token record with invalid expiry",
                extra={"event": "auth_config_invalid", "token_id": token_id or f"token-{index}"},
            )
            continue
        credentials.append(
            AuthCredential(
                token_id=token_id or f"token-{index}",
                token=token_secret,
                scopes=frozenset(_normalize_scopes(scope_blob)),
                expires_at=expires_at,
            )
        )
    return credentials


def _parse_expires_at(value: str) -> datetime | None:
    normalized_value = value.strip()
    if not normalized_value:
        return None
    normalized = normalized_value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _auth_error_response(*, detail: str, status_code: int, auth_result: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "auth_result": auth_result},
        headers={"WWW-Authenticate": "Bearer"},
    )


def _log_auth_failure(
    request: Request,
    *,
    auth_result: str,
    token_id: str | None = None,
    required_scope: str | None = None,
    granted_scopes: str | None = None,
) -> None:
    logger.warning(
        "auth failed",
        extra={
            "event": "auth_failure",
            "path": request.url.path,
            "method": request.method.upper(),
            "auth_result": auth_result,
            "client": request.client.host if request.client else "unknown",
            "token_id": token_id,
            "required_scope": required_scope,
            "granted_scopes": granted_scopes,
        },
    )
