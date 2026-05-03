import contextvars
import json
import logging
import sys
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

request_id_ctx_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


class JsonFormatter(logging.Formatter):
    """Small JSON formatter suitable for structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "service": "api-control-plane",
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", request_id_ctx_var.get()),
            "trace_id": getattr(record, "trace_id", request_id_ctx_var.get()),
            "job_id": getattr(record, "job_id", "-"),
        }
        for field in (
            "event",
            "connection_id",
            "client",
            "topics",
            "last_seq",
            "replay_status",
            "replayed_count",
            "oldest_seq",
            "latest_seq",
            "path",
            "method",
            "auth_result",
            "required_scope",
            "granted_scopes",
            "token_id",
            "response_status",
            "duration_ms",
            "error_code",
            "dependency",
            "dependency_state",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


class RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIDFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Adds X-Request-ID support and binds the value to log context."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = request_id_ctx_var.set(request_id)
        request.state.request_id = request_id
        request.state.trace_id = request.headers.get("X-Trace-ID", request_id)
        request.state.auth_result = "unknown"
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            _log_request_summary(
                request=request,
                response_status=response.status_code,
                elapsed_ms=(time.perf_counter() - started_at) * 1000,
            )
            if response.status_code >= 400:
                return _normalize_error_response(request=request, response=response)
            return response
        except Exception:
            _log_request_summary(
                request=request,
                response_status=500,
                elapsed_ms=(time.perf_counter() - started_at) * 1000,
                error_code="internal_error",
            )
            raise
        finally:
            request_id_ctx_var.reset(token)


def _normalize_error_response(*, request: Request, response: Response) -> Response:
    if response.headers.get("content-type", "").startswith("application/json"):
        return response
    envelope = {
        "request_id": getattr(request.state, "request_id", request_id_ctx_var.get()),
        "error_code": "request_failed",
        "detail": "Request failed",
    }
    normalized = JSONResponse(status_code=response.status_code, content=envelope)
    normalized.headers.update(response.headers)
    normalized.headers["X-Request-ID"] = envelope["request_id"]
    return normalized


def _log_request_summary(*, request: Request, response_status: int, elapsed_ms: float, error_code: str | None = None) -> None:
    logging.getLogger("app.request").info(
        "request completed",
        extra={
            "event": "request_summary",
            "trace_id": getattr(request.state, "trace_id", request_id_ctx_var.get()),
            "path": request.url.path,
            "method": request.method.upper(),
            "auth_result": getattr(request.state, "auth_result", "unknown"),
            "response_status": response_status,
            "duration_ms": round(elapsed_ms, 2),
            "error_code": error_code,
        },
    )
