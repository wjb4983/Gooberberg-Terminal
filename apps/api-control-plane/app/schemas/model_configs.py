from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ModelFamily(StrEnum):
    HMM_REGIME_SWITCHING = "hmm_regime_switching"


class ModelConfigCreateRequest(BaseModel):
    model_family: ModelFamily
    config: dict[str, Any] = Field(default_factory=dict)


class ModelConfigUpdateRequest(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)


class ModelConfigResponse(BaseModel):
    id: UUID
    model_family: ModelFamily
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
