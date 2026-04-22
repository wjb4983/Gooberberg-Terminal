from datetime import UTC, datetime

from fastapi import APIRouter, Request

from app.core.config import get_settings
from app.schemas import DependencyStatus, HealthResponse, QueueHealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    postgres_configured = bool(settings.postgres_dsn)
    redis_configured = bool(settings.redis_dsn)

    return HealthResponse(
        service=settings.app_name,
        status="ok",
        version=settings.app_version,
        postgres=DependencyStatus(
            configured=postgres_configured,
            reachable=None,
            detail="placeholder: postgres connectivity check not implemented",
        ),
        redis=DependencyStatus(
            configured=redis_configured,
            reachable=None,
            detail="placeholder: redis connectivity check not implemented",
        ),
    )


@router.get("/queue", response_model=QueueHealthResponse)
async def queue_health(request: Request) -> QueueHealthResponse:
    settings = get_settings()
    queue_depth = await request.app.state.job_queue.depth()
    heartbeat_at: datetime | None = request.app.state.last_worker_heartbeat_at
    heartbeat_age_seconds = (datetime.now(UTC) - heartbeat_at).total_seconds() if heartbeat_at else None

    if queue_depth is None:
        return QueueHealthResponse(
            status="degraded",
            queue_depth=None,
            worker_heartbeat_at=heartbeat_at.isoformat() if heartbeat_at else None,
            worker_heartbeat_age_seconds=heartbeat_age_seconds,
            detail="queue backend is not configured",
        )

    if heartbeat_age_seconds is None:
        status = "degraded"
        detail = "queue is available but worker heartbeat has not been observed yet"
    elif heartbeat_age_seconds > settings.worker_heartbeat_stale_after_seconds:
        status = "degraded"
        detail = "worker heartbeat is stale"
    else:
        status = "ok"
        detail = "queue and worker heartbeat are healthy"

    return QueueHealthResponse(
        status=status,
        queue_depth=queue_depth,
        worker_heartbeat_at=heartbeat_at.isoformat() if heartbeat_at else None,
        worker_heartbeat_age_seconds=heartbeat_age_seconds,
        detail=detail,
    )


@router.post("/queue/heartbeat")
def record_queue_worker_heartbeat(request: Request) -> dict[str, str]:
    now = datetime.now(UTC)
    request.app.state.last_worker_heartbeat_at = now
    return {"status": "ok", "recorded_at": now.isoformat()}
