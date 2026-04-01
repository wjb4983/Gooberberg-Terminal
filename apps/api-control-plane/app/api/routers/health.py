from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas import DependencyStatus, HealthResponse

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
