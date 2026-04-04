from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.schemas.training_runs import RunStatus


class ParameterSweepCreateRequest(BaseModel):
    model_config_id: UUID
    objective: str = Field(min_length=1)
    search_space: dict[str, Any] = Field(default_factory=dict)


class ParameterSweepResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    model_config_id: UUID
    objective: str
    search_space: dict[str, Any] = Field(default_factory=dict)
    job_id: UUID
    status: RunStatus = RunStatus.QUEUED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
