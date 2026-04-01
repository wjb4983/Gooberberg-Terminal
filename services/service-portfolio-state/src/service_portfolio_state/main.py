"""Entry module for service_portfolio_state."""

import asyncio
import json
import os
from datetime import UTC, datetime

from service_portfolio_state.schemas import PortfolioSnapshot, Position

PORTFOLIO_SNAPSHOT_CHANNEL = os.getenv("GB_PORTFOLIO_SNAPSHOT_CHANNEL", "portfolio.snapshot")
PORTFOLIO_SNAPSHOT_STREAM = os.getenv("GB_PORTFOLIO_SNAPSHOT_STREAM", "portfolio:snapshots")
PUBLISH_INTERVAL_SECONDS = float(os.getenv("GB_PORTFOLIO_PUBLISH_INTERVAL_SECONDS", "2"))

try:
    from redis.asyncio import Redis
except Exception:  # pragma: no cover
    Redis = None  # type: ignore[misc, assignment]


def _build_mock_snapshot(seq: int) -> PortfolioSnapshot:
    now = datetime.now(UTC)
    market_price = 210.0 + (seq % 20) * 0.75
    quantity = 120
    avg = 198.5
    market_value = market_price * quantity
    unrealized = (market_price - avg) * quantity
    gross = market_value + 30_000
    net = market_value - 30_000

    return PortfolioSnapshot(
        account_id="paper-main",
        timestamp=now,
        equity=100_000 + unrealized,
        cash=35_000,
        buying_power=130_000,
        gross_exposure=gross,
        net_exposure=net,
        unrealized_pnl=unrealized,
        realized_pnl=420.0,
        positions=[
            Position(
                symbol="AAPL",
                quantity=quantity,
                average_price=avg,
                market_price=market_price,
                market_value=market_value,
                unrealized_pnl=unrealized,
                side="long",
            )
        ],
    )


async def run() -> None:
    redis_dsn = os.getenv("GB_REDIS_DSN")
    if not Redis or not redis_dsn:
        print("service-portfolio-state idle: redis unavailable")
        return

    client = Redis.from_url(redis_dsn, encoding="utf-8", decode_responses=True)
    await client.ping()
    print("service-portfolio-state connected to redis")

    seq = 0
    try:
        while True:
            snapshot = _build_mock_snapshot(seq)
            payload = snapshot.model_dump(mode="json")
            payload_json = json.dumps(payload)
            await client.publish(PORTFOLIO_SNAPSHOT_CHANNEL, payload_json)
            await client.xadd(PORTFOLIO_SNAPSHOT_STREAM, {"payload": payload_json}, maxlen=10_000, approximate=True)
            seq += 1
            await asyncio.sleep(PUBLISH_INTERVAL_SECONDS)
    finally:
        await client.aclose()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
