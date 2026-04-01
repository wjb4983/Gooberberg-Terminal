from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class JobEnvelope(BaseModel):
    job_id: UUID
    trace_id: str
    job_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    queued_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class JobLifecycleEvent(BaseModel):
    job_id: UUID
    trace_id: str
    status: JobStatus
    detail: str
    result_ref: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


JOB_QUEUE_KEY = "gb:jobs:queue"
JOB_STATE_KEY_PREFIX = "gb:jobs:state:"
