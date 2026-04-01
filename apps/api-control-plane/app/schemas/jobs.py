from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.jobs.models import JobStatus


class JobCreateRequest(BaseModel):
    job_type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class JobResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    job_type: str
    status: JobStatus
    payload: dict[str, Any]
    trace_id: str
    accepted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class JobStatusResponse(BaseModel):
    id: UUID
    status: JobStatus
    detail: str
    trace_id: str
    updated_at: datetime


class JobLifecycleUpdateRequest(BaseModel):
    status: JobStatus
    detail: str = Field(min_length=1)
