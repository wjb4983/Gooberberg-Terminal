from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from app.schemas.run_constraints import RunConstraints, extract_constraints_from_parameters


class RunStatus(StrEnum):
    QUEUED = "queued"
    WAITING_FOR_DATA = "waiting_for_data"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(StrEnum):
    TIME_SERIES_MOMENTUM = "time_series_momentum"
    CROSS_SECTIONAL = "cross_sectional"
    VOLATILITY = "volatility"
    REGIME_SWITCHING = "regime_switching"


class SubtaskType(StrEnum):
    RANKING = "ranking"
    ENTRY_SIGNAL = "entry_signal"
    EXIT_SIGNAL = "exit_signal"
    REGIME_STATE = "regime_state"
    OTHER = "other"


class TaskSubtypeValidatedModel(BaseModel):
    task_type: TaskType
    subtask_type: SubtaskType

    @model_validator(mode="after")
    def validate_task_subtask_compatibility(self) -> "TaskSubtypeValidatedModel":
        if self.subtask_type == SubtaskType.REGIME_STATE and self.task_type != TaskType.REGIME_SWITCHING:
            raise ValueError("subtask_type 'regime_state' is only valid for task_type 'regime_switching'")
        return self


class TrainingRunCreateRequest(TaskSubtypeValidatedModel):
    model_config_id: UUID
    dataset_id: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    constraints: RunConstraints | None = None


class TrainingRunResponse(TaskSubtypeValidatedModel):
    id: UUID = Field(default_factory=uuid4)
    model_config_id: UUID
    dataset_id: str
    dataset_spec_hash: str = ""
    dataset_manifest_version: str = "v1"
    resolved_symbol_count: int = 0
    resolved_member_count: int = 0
    model_config_version_tag: str = "unknown"
    job_id: UUID
    status: RunStatus = RunStatus.QUEUED
    parameters: dict[str, Any] = Field(default_factory=dict)
    constraints: RunConstraints | None = None
    constraint_profile_version: str = "v1"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def hydrate_constraints_from_parameters(self) -> "TrainingRunResponse":
        if self.constraints is None:
            self.constraints = extract_constraints_from_parameters(self.parameters)
        return self
