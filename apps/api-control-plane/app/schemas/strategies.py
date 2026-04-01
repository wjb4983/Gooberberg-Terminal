from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from gb_core.schemas import StrategyIntent


class StrategyMode(StrEnum):
    PAPER = "paper"
    LIVE = "live"


class StrategyInstanceStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    STOPPED = "stopped"


class StrategyInstance(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    strategy_key: str = Field(min_length=1)
    mode: StrategyMode
    status: StrategyInstanceStatus
    intent: StrategyIntent = Field(default_factory=StrategyIntent)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    stopped_at: datetime | None = None


class StrategyInstanceCreateRequest(BaseModel):
    strategy_key: str = Field(min_length=1)
    mode: StrategyMode
    intent: StrategyIntent = Field(default_factory=StrategyIntent)


class StrategyInstanceActionResponse(BaseModel):
    instance: StrategyInstance
    detail: str
