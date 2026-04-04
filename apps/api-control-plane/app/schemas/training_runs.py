from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrainingRunCreateRequest(BaseModel):
    model_config_id: UUID
    dataset_id: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)


class TrainingRunResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    model_config_id: UUID
    dataset_id: str
    job_id: UUID
    status: RunStatus = RunStatus.QUEUED
    parameters: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
