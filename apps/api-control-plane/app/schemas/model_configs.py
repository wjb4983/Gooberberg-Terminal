from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ModelConfigCreateRequest(BaseModel):
    model_family: str = Field(min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)


class ModelConfigUpdateRequest(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)


class ModelConfigResponse(BaseModel):
    id: UUID
    model_family: str
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
