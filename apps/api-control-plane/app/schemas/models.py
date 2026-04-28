from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ModelDeploymentStatus(StrEnum):
    DEPLOYING = "deploying"
    ACTIVE = "active"
    INACTIVE = "inactive"


class ModelDeployment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    model_name: str = Field(min_length=2, max_length=80, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]{1,79}$")
    model_version: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$")
    artifact_ref: str = Field(min_length=3, max_length=255, pattern=r"^[a-zA-Z0-9:/._-]{3,255}$")
    status: ModelDeploymentStatus
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ModelDeploymentCreateRequest(BaseModel):
    model_name: str = Field(min_length=2, max_length=80, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]{1,79}$")
    model_version: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$")
    artifact_ref: str = Field(min_length=3, max_length=255, pattern=r"^[a-zA-Z0-9:/._-]{3,255}$")


class ModelDeploymentActionResponse(BaseModel):
    deployment: ModelDeployment
    detail: str


class ModelDeploymentEvent(BaseModel):
    deployment_id: UUID
    model_name: str
    model_version: str
    artifact_ref: str
    status: ModelDeploymentStatus
    previous_status: ModelDeploymentStatus | None = None
    event_type: str
    detail: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ModelCatalogItem(BaseModel):
    model_family: str
    model_name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    validator_adapter: str
