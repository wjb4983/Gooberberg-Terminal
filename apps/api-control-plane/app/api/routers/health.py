from datetime import UTC, datetime
import asyncio
import logging
import time

from fastapi import APIRouter, Request
from sqlalchemy import text

from app.core.config import get_settings
from app.schemas import DependencyStatus, HealthResponse, QueueHealthResponse

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger(__name__)

_DEPENDENCY_PROBE_TIMEOUT_SECONDS = 0.2
_OVERALL_HEALTH_DEADLINE_SECONDS = 0.5


def _dependency_checks_enabled() -> bool:
    return get_settings().health_prod_dependency_checks_enabled


def _run_postgres_probe(request: Request) -> None:
    with request.app.state.db.session_factory() as session:
        session.execute(text("SELECT 1"))


async def _postgres_status(request: Request, *, timeout_seconds: float) -> DependencyStatus:
    settings = get_settings()
    configured = bool(settings.postgres_dsn)
    if not configured:
        return DependencyStatus(configured=False, reachable=False, detail="postgres dsn not configured")
    if not _dependency_checks_enabled():
        return DependencyStatus(configured=True, reachable=False, detail="dependency checks disabled by GB_HEALTH_PROD_DEPENDENCY_CHECKS_ENABLED")

    start = time.monotonic()
    try:
        await asyncio.wait_for(asyncio.to_thread(_run_postgres_probe, request), timeout=timeout_seconds)
        return DependencyStatus(configured=True, reachable=True, detail=f"postgres probe ok ({(time.monotonic()-start)*1000:.1f}ms)")
    except TimeoutError:
        return DependencyStatus(configured=True, reachable=False, detail=f"postgres probe timed out at {timeout_seconds * 1000:.0f}ms budget")
    except Exception as exc:
        return DependencyStatus(configured=True, reachable=False, detail=f"postgres probe failed: {type(exc).__name__}")


async def _redis_status(request: Request, *, timeout_seconds: float) -> DependencyStatus:
    settings = get_settings()
    configured = bool(settings.redis_dsn)
    if not configured:
        return DependencyStatus(configured=False, reachable=False, detail="redis dsn not configured")
    if not _dependency_checks_enabled():
        return DependencyStatus(configured=True, reachable=False, detail="dependency checks disabled by GB_HEALTH_PROD_DEPENDENCY_CHECKS_ENABLED")

    client = getattr(request.app.state, "redis_client", None)
    if client is None:
        return DependencyStatus(configured=True, reachable=False, detail="redis client not initialized")

    start = time.monotonic()
    try:
        pong = await asyncio.wait_for(client.ping(), timeout=timeout_seconds)
        return DependencyStatus(configured=True, reachable=bool(pong), detail=f"redis probe ok ({(time.monotonic()-start)*1000:.1f}ms)")
    except TimeoutError:
        return DependencyStatus(configured=True, reachable=False, detail=f"redis probe timed out at {timeout_seconds * 1000:.0f}ms budget")
    except Exception as exc:
        return DependencyStatus(configured=True, reachable=False, detail=f"redis probe failed: {type(exc).__name__}")


@router.get("", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = get_settings()
    probe_started = time.monotonic()

    postgres = await _postgres_status(request, timeout_seconds=_DEPENDENCY_PROBE_TIMEOUT_SECONDS)
    remaining = _OVERALL_HEALTH_DEADLINE_SECONDS - (time.monotonic() - probe_started)
    if remaining <= 0:
        redis = DependencyStatus(configured=bool(settings.redis_dsn), reachable=False, detail="skipped: overall health deadline exceeded")
    else:
        redis = await _redis_status(request, timeout_seconds=min(_DEPENDENCY_PROBE_TIMEOUT_SECONDS, remaining))

    status = "ok" if postgres.reachable and redis.reachable else "degraded"
    return HealthResponse(service=settings.app_name, status=status, version=settings.app_version, postgres=postgres, redis=redis)


@router.get("/deep", response_model=HealthResponse)
async def health_deep(request: Request) -> HealthResponse:
    return await health(request)


@router.get("/queue", response_model=QueueHealthResponse)
async def queue_health(request: Request) -> QueueHealthResponse:
    settings = get_settings()
    backend = type(getattr(request.app.state.job_queue, "_client", None)).__name__
    probe_started = time.monotonic()
    try:
        queue_depth = await request.app.state.job_queue.depth()
    except Exception:
        logger.exception("queue health dependency call failed")
        return QueueHealthResponse(status="degraded", backend_type=backend, probe_latency_ms=(time.monotonic()-probe_started)*1000, queue_depth=None, worker_heartbeat_at=None, worker_heartbeat_age_seconds=None, detail="queue backend check failed")

    probe_latency_ms = (time.monotonic() - probe_started) * 1000
    heartbeat_at: datetime | None = request.app.state.last_worker_heartbeat_at
    heartbeat_age_seconds = (datetime.now(UTC) - heartbeat_at).total_seconds() if heartbeat_at else None

    if queue_depth is None:
        return QueueHealthResponse(status="degraded", backend_type=backend, probe_latency_ms=probe_latency_ms, queue_depth=None, worker_heartbeat_at=heartbeat_at.isoformat() if heartbeat_at else None, worker_heartbeat_age_seconds=heartbeat_age_seconds, detail="queue backend is not configured (safe degrade)")

    if heartbeat_age_seconds is None:
        status, detail = "degraded", "queue is available but no worker heartbeat observed yet"
    elif heartbeat_age_seconds > settings.worker_heartbeat_stale_after_seconds:
        status = "degraded"
        detail = f"worker heartbeat stale: last={heartbeat_at.isoformat()} now={datetime.now(UTC).isoformat()} age={heartbeat_age_seconds:.1f}s threshold={settings.worker_heartbeat_stale_after_seconds:.1f}s"
    else:
        status, detail = "ok", "queue depth and worker heartbeat are healthy"

    return QueueHealthResponse(status=status, backend_type=backend, probe_latency_ms=probe_latency_ms, queue_depth=queue_depth, worker_heartbeat_at=heartbeat_at.isoformat() if heartbeat_at else None, worker_heartbeat_age_seconds=heartbeat_age_seconds, detail=detail)


@router.post("/queue/heartbeat")
def record_queue_worker_heartbeat(request: Request) -> dict[str, str]:
    now = datetime.now(UTC)
    request.app.state.last_worker_heartbeat_at = now
    return {"status": "ok", "recorded_at": now.isoformat()}
