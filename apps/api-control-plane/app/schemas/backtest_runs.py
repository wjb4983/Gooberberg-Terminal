from gb_core.lineage import LineageReference, LineageSpec
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.schemas.training_runs import RunStatus


class BacktestRunCreateRequest(BaseModel):
    lineage: LineageSpec | None = None
    lineage_ref: LineageReference | None = None
    strategy_key: str = Field(min_length=1)
    model_config_id: UUID | None = None
    window_start: datetime
    window_end: datetime
    parameters: dict[str, Any] = Field(default_factory=dict)
    deterministic_mode: bool = False
    scenario_id: str = Field(default="baseline", min_length=1)
    git_sha: str = ""
    data_snapshot_id: str = ""
    random_seed: int = 0
    engine_version: str = ""
    feature_set_version: str = ""
    timezone: str = "UTC"
    calendar_id: str = ""
    environment_fingerprint: dict[str, Any] = Field(default_factory=dict)
    confirmation_token: str | None = None


class BacktestRunPreflightRequest(BaseModel):
    strategy_key: str = Field(min_length=1)
    model_config_id: UUID | None = None
    window_start: datetime
    window_end: datetime
    parameters: dict[str, Any] = Field(default_factory=dict)
    deterministic_mode: bool = False
    scenario_id: str = Field(default="baseline", min_length=1)


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
    deterministic_mode: bool = False
    scenario_id: str = "baseline"
    git_sha: str = ""
    config_hash: str = ""
    data_snapshot_id: str = ""
    random_seed: int = 0
    engine_version: str = ""
    feature_set_version: str = ""
    timezone: str = "UTC"
    calendar_id: str = ""
    resolved_config: dict[str, Any] = Field(default_factory=dict)
    environment_fingerprint: dict[str, Any] = Field(default_factory=dict)
    run_checksum: str = ""
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


class ReplayEvent(BaseModel):
    type: str = Field(min_length=1)
    order_id: str | None = None
    symbol: str | None = None
    side: str | None = None
    quantity: float | None = None
    price: float | None = None
    fee: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BacktestReplayValidationRequest(BaseModel):
    strategy_version: str = Field(min_length=1)
    config_hash: str = Field(min_length=1)
    events: list[ReplayEvent] = Field(default_factory=list)
    expected_outcomes: dict[str, Any] = Field(default_factory=dict)


class BacktestReplayValidationResponse(BaseModel):
    run_id: UUID
    replay: dict[str, Any]
    validation: dict[str, Any]
