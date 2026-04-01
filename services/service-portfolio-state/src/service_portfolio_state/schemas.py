from datetime import UTC, datetime

from pydantic import BaseModel, Field


class Position(BaseModel):
    symbol: str = Field(min_length=1)
    quantity: float
    average_price: float
    market_price: float
    market_value: float
    unrealized_pnl: float
    side: str = Field(default="long")


class PortfolioSnapshot(BaseModel):
    account_id: str = Field(min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    equity: float
    cash: float
    buying_power: float
    gross_exposure: float
    net_exposure: float
    unrealized_pnl: float
    realized_pnl: float
    positions: list[Position] = Field(default_factory=list)
