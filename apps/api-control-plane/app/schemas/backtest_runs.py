from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class BacktestRunCreateRequest(BaseModel):
    strategy_key: str = Field(min_length=1)
    model_config_id: UUID | None = None
    window_start: datetime
    window_end: datetime
    parameters: dict[str, Any] = Field(default_factory=dict)


class BacktestRunResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    strategy_key: str
    model_config_id: UUID | None = None
    window_start: datetime
    window_end: datetime
    parameters: dict[str, Any] = Field(default_factory=dict)
    status: str = "queued"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
