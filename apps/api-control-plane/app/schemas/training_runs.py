from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from app.domain.task_definitions import get_task_subtask_definition
from app.domain.training_runs.validation_profiles import ValidationProfile
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
    RETURN_FORECAST = "return_forecast"
    VOL_FORECAST = "vol_forecast"
    ALLOCATION = "allocation"
    REGIME_STATE = "regime_state"
    OTHER = "other"


class TaskSubtypeValidatedModel(BaseModel):
    task_type: TaskType
    subtask_type: SubtaskType

    @model_validator(mode="after")
    def validate_task_subtask_compatibility(self) -> "TaskSubtypeValidatedModel":
        get_task_subtask_definition(task_type=self.task_type, subtask_type=self.subtask_type)
        return self


class TrainingRunCreateRequest(TaskSubtypeValidatedModel):
    task_type: TaskType = TaskType.TIME_SERIES_MOMENTUM
    subtask_type: SubtaskType = SubtaskType.RANKING
    model_config_id: UUID
    dataset_id: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    constraints: RunConstraints | None = None
    validation_profile: ValidationProfile | None = None


class TrainingRunValidationRequest(TaskSubtypeValidatedModel):
    task_type: TaskType = TaskType.TIME_SERIES_MOMENTUM
    subtask_type: SubtaskType = SubtaskType.RANKING
    model_config_id: UUID
    dataset_id: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    constraints: RunConstraints | None = None
    validation_profile: ValidationProfile | None = None


class TrainingIntent(TaskSubtypeValidatedModel):
    task_type: TaskType
    subtask_type: SubtaskType
    model_family: str = Field(min_length=1)
    model_config_id: UUID
    dataset_id: str = Field(min_length=1)
    parameter_set_id: UUID | None = None
    validation_profile: ValidationProfile
    override_parameters: dict[str, Any] = Field(default_factory=dict)


class TrainingRunValidationResponse(BaseModel):
    normalized_payload: TrainingRunCreateRequest
    training_intent: TrainingIntent
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    compatible: bool = False
    valid: bool = False


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
