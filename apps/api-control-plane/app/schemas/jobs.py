from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.jobs.models import JobStatus


class JobCreateRequest(BaseModel):
    job_type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    run_id: UUID | None = None
    run_type: str | None = None


class JobResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    job_type: str
    status: JobStatus
    payload: dict[str, Any]
    trace_id: str
    run_id: UUID | None = None
    run_type: str | None = None
    accepted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class JobStatusResponse(BaseModel):
    id: UUID
    status: JobStatus
    detail: str
    trace_id: str
    run_id: UUID | None = None
    run_type: str | None = None
    progress_pct: float = 0.0
    message: str = ""
    result_ref: str | None = None
    updated_at: datetime


class JobLifecycleUpdateRequest(BaseModel):
    status: JobStatus
    detail: str = Field(min_length=1)
    run_id: UUID | None = None
    run_type: str | None = None
    progress_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    message: str = ""
    result_ref: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
