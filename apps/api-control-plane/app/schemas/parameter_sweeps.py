from gb_core.lineage import LineageSpec
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from app.schemas.training_runs import RunStatus, TaskSubtypeValidatedModel


class ParameterSweepCreateRequest(TaskSubtypeValidatedModel):
    lineage: LineageSpec
    model_config_id: UUID
    parameter_set_id: UUID | None = None
    objective: str = Field(min_length=1)
    search_space: dict[str, Any] = Field(default_factory=dict)
    provenance_snapshot: dict[str, Any] = Field(default_factory=dict)


class ParameterSweepResponse(TaskSubtypeValidatedModel):
    id: UUID = Field(default_factory=uuid4)
    model_config_id: UUID
    parameter_set_id: UUID | None = None
    objective: str
    search_space: dict[str, Any] = Field(default_factory=dict)
    provenance_snapshot: dict[str, Any] = Field(default_factory=dict)
    job_id: UUID
    status: RunStatus = RunStatus.QUEUED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
