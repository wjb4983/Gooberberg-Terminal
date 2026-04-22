from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.schemas.training_runs import RunStatus


class BacktestRunCreateRequest(BaseModel):
    strategy_key: str = Field(min_length=1)
    model_config_id: UUID | None = None
    window_start: datetime
    window_end: datetime
    parameters: dict[str, Any] = Field(default_factory=dict)
    confirmation_token: str | None = None


class BacktestRunPreflightRequest(BaseModel):
    strategy_key: str = Field(min_length=1)
    model_config_id: UUID | None = None
    window_start: datetime
    window_end: datetime
    parameters: dict[str, Any] = Field(default_factory=dict)


class BacktestRunPreflightResponse(BaseModel):
    symbol_count: int
    date_span_days: int
    estimated_units: int
    oversized_threshold: int
    requires_confirmation: bool
    confirmation_token: str | None = None
    heuristic: str


class BacktestRunResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    strategy_key: str
    model_config_id: UUID | None = None
    window_start: datetime
    window_end: datetime
    parameters: dict[str, Any] = Field(default_factory=dict)
    job_id: UUID
    status: RunStatus = RunStatus.QUEUED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BacktestStatusResponse(BaseModel):
    run_id: UUID
    job_id: UUID
    status: RunStatus
    summary: str
    updated_at: datetime


class BacktestPagedResponse(BaseModel):
    items: list[dict[str, Any]]
    offset: int
    limit: int
    next_offset: int | None
