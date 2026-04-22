from pydantic import BaseModel


class DependencyStatus(BaseModel):
    configured: bool
    reachable: bool | None = None
    detail: str


class HealthResponse(BaseModel):
    service: str
    status: str
    version: str
    postgres: DependencyStatus
    redis: DependencyStatus


class QueueHealthResponse(BaseModel):
    status: str
    queue_depth: int | None = None
    worker_heartbeat_at: str | None = None
    worker_heartbeat_age_seconds: float | None = None
    detail: str
