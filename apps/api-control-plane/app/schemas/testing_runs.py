from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

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
    mode: TestingRunMode
    target_refs: list[TestingTargetReference] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)


class TestingRunResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    mode: TestingRunMode
    target_refs: list[TestingTargetReference] = Field(default_factory=list)
    status: RunStatus = RunStatus.QUEUED
    parameters: dict[str, Any] = Field(default_factory=dict)
    result_summary: TestingResultSummary | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
