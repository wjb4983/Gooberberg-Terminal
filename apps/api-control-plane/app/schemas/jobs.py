from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.jobs.models import JobStatus

JOB_CANCELABLE_STATES: frozenset[JobStatus] = frozenset(
    {JobStatus.QUEUED, JobStatus.WAITING_FOR_DATA, JobStatus.RUNNING}
)
JOB_RETRYABLE_STATES: frozenset[JobStatus] = frozenset({JobStatus.FAILED, JobStatus.CANCELLED})


class RunType(StrEnum):
    TRAINING = "training"
    PARAMETER_SWEEP = "parameter_sweep"
    BACKTEST = "backtest"


class JobCreateRequest(BaseModel):
    job_type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    run_id: UUID | None = None
    run_type: RunType | None = None


class JobResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    job_type: str
    status: JobStatus
    payload: dict[str, Any]
    trace_id: str
    run_id: UUID | None = None
    run_type: RunType | None = None
    accepted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class JobStatusResponse(BaseModel):
    id: UUID
    status: JobStatus
    detail: str
    trace_id: str
    run_id: UUID | None = None
    run_type: RunType | None = None
    progress_pct: float = 0.0
    message: str = ""
    result_ref: str | None = None
    updated_at: datetime


class JobLifecycleUpdateRequest(BaseModel):
    status: JobStatus
    detail: str = Field(min_length=1)
    run_id: UUID | None = None
    run_type: RunType | None = None
    progress_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    message: str = ""
    result_ref: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
    artifact_checksum: str | None = Field(default=None, min_length=8, max_length=128)
    artifact_size_bytes: int | None = Field(default=None, ge=0)
    artifact_retention_class: str = Field(default="standard", min_length=1, max_length=32)
    artifact_manifest: list[dict[str, Any]] = Field(default_factory=list)
    lineage: dict[str, Any] = Field(default_factory=dict)
    expected_runtime: dict[str, Any] = Field(default_factory=dict)
    runtime_observed: dict[str, Any] = Field(default_factory=dict)
    mismatch_policy: str = Field(default="strict", min_length=1, max_length=32)


class JobProgressEventPayload(BaseModel):
    job_id: UUID
    run_id: UUID | None = None
    status: JobStatus
    progress_pct: float = Field(ge=0.0, le=100.0)
    message: str = ""
    timestamp: datetime
    updated_at: datetime


class JobLogEventPayload(JobProgressEventPayload):
    pass


class ArtifactSummaryResponse(BaseModel):
    id: int
    run_id: UUID
    run_type: RunType
    job_id: UUID
    artifact_ref: str
    checksum: str
    size_bytes: int = Field(ge=0)
    best_metric: float | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_accessed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    retention_class: str


class ArtifactDetailResponse(ArtifactSummaryResponse):
    metrics: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
