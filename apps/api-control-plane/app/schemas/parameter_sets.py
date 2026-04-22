from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ParameterSetCreateRequest(BaseModel):
    model_config_id: UUID
    name: str = Field(min_length=1, max_length=255)
    parameters: dict[str, Any] = Field(default_factory=dict)
    version_tag: str = Field(min_length=1, max_length=64)
    parent_set_id: UUID | None = None
    provenance_metadata: dict[str, Any] = Field(default_factory=dict)


class ParameterSetCloneRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    version_tag: str | None = Field(default=None, min_length=1, max_length=64)
    parameters: dict[str, Any] | None = None
    provenance_metadata: dict[str, Any] | None = None


class ParameterSetResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    model_config_id: UUID
    name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    version_tag: str
    parent_set_id: UUID | None = None
    provenance_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
