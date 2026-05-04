from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.training_runs import TrainingRunCreateRequest, TrainingRunResponse


class TrainingLaunchResponse(BaseModel):
    run: TrainingRunResponse
    job_id: UUID
    tracking: dict[str, str] = Field(default_factory=dict)


class ModelLeaderboardEntry(BaseModel):
    model_family: str
    model_name: str
    score: float
    rank: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class ServiceConnectivityStatus(BaseModel):
    service: str
    mode: str
    connected: bool
    status: str
    detail: str
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    endpoint: str | None = None
    upstream_http_status: int | None = None
    heartbeat_at: datetime | None = None
    heartbeat_age_seconds: float | None = None
    pnl: float | None = None
    exposure: float | None = None


class ExternalServicesStatusResponse(BaseModel):
    paper: ServiceConnectivityStatus
    live: ServiceConnectivityStatus
