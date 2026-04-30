from gb_core.lineage import LineageSpec
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from app.schemas.run_constraints import RunConstraints, extract_constraints_from_parameters
from app.schemas.training_runs import RunStatus


class TestingRunMode(StrEnum):
    SMOKE = "smoke"
    ACCEPTANCE = "acceptance"
    REGRESSION = "regression"


class TestingTargetReference(BaseModel):
    target_type: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    label: str | None = None


class TestingArtifactReference(BaseModel):
    artifact_type: str = Field(min_length=1)
    artifact_ref: str = Field(min_length=1)
    label: str | None = None


class TestingResultSummary(BaseModel):
    passed_checks: list[str] = Field(default_factory=list)
    failed_checks: list[str] = Field(default_factory=list)
    log_artifacts: list[TestingArtifactReference] = Field(default_factory=list)


class TestingRunCreateRequest(BaseModel):
    lineage: LineageSpec
    mode: TestingRunMode
    target_refs: list[TestingTargetReference] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    constraints: RunConstraints | None = None


class TestingRunResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    mode: TestingRunMode
    target_refs: list[TestingTargetReference] = Field(default_factory=list)
    status: RunStatus = RunStatus.QUEUED
    parameters: dict[str, Any] = Field(default_factory=dict)
    constraints: RunConstraints | None = None
    result_summary: TestingResultSummary | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def hydrate_constraints_from_parameters(self) -> "TestingRunResponse":
        if self.constraints is None:
            self.constraints = extract_constraints_from_parameters(self.parameters)
        return self
