"""Entry module for service_portfolio_state."""

import asyncio
import json
import os
from datetime import UTC, datetime

from service_portfolio_state.schemas import PortfolioSnapshot, Position

FILL_STREAM = os.getenv("GB_PORTFOLIO_FILL_STREAM", "portfolio:fills")
ORDER_STREAM = os.getenv("GB_PORTFOLIO_ORDER_STREAM", "portfolio:orders")
POSITION_HASH = os.getenv("GB_PORTFOLIO_POSITION_HASH", "portfolio:positions")
CASH_KEY = os.getenv("GB_PORTFOLIO_CASH_KEY", "portfolio:cash")


PORTFOLIO_SNAPSHOT_CHANNEL = os.getenv("GB_PORTFOLIO_SNAPSHOT_CHANNEL", "portfolio.snapshot")
PORTFOLIO_SNAPSHOT_STREAM = os.getenv("GB_PORTFOLIO_SNAPSHOT_STREAM", "portfolio:snapshots")
PUBLISH_INTERVAL_SECONDS = float(os.getenv("GB_PORTFOLIO_PUBLISH_INTERVAL_SECONDS", "2"))

try:
    from redis.asyncio import Redis
except Exception:  # pragma: no cover
    Redis = None  # type: ignore[misc, assignment]


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


async def _build_snapshot(client: Redis) -> PortfolioSnapshot:
    now = datetime.now(UTC)
    raw_positions = await client.hgetall(POSITION_HASH)
    prices = await client.hgetall(f"{POSITION_HASH}:prices")
    cash = _to_float(await client.get(CASH_KEY), 100_000.0)
    realized = 0.0
    fills = await client.xrevrange(FILL_STREAM, count=200)
    for _, payload in fills:
        realized += _to_float(payload.get("realized_pnl"))

    positions: list[Position] = []
    gross_exposure = 0.0
    net_exposure = 0.0
    unrealized = 0.0
    for symbol, qty_raw in raw_positions.items():
        qty = _to_float(qty_raw)
        avg = _to_float(await client.hget(f"{POSITION_HASH}:avg", symbol), 0.0)
        px = _to_float(prices.get(symbol), avg)
        mv = qty * px
        upnl = (px - avg) * qty
        gross_exposure += abs(mv)
        net_exposure += mv
        unrealized += upnl
        positions.append(Position(symbol=symbol, quantity=qty, average_price=avg, market_price=px, market_value=mv, unrealized_pnl=upnl, side="long" if qty >= 0 else "short"))

    equity = cash + net_exposure
    open_orders = await client.xrevrange(ORDER_STREAM, count=100)
    reserved = sum(_to_float(p.get("notional")) for _, p in open_orders if p.get("status") in {"new", "open", "working"})

    return PortfolioSnapshot(account_id="paper-main", timestamp=now, equity=equity, cash=cash, buying_power=max(cash*2-reserved,0.0), gross_exposure=gross_exposure, net_exposure=net_exposure, unrealized_pnl=unrealized, realized_pnl=realized, positions=positions)



async def run() -> None:
    redis_dsn = os.getenv("GB_REDIS_DSN")
    if not Redis or not redis_dsn:
        print("service-portfolio-state idle: redis unavailable")
        return

    client = Redis.from_url(redis_dsn, encoding="utf-8", decode_responses=True)
    await client.ping()
    print("service-portfolio-state connected to redis")

    try:
        while True:
            snapshot = await _build_snapshot(client)
            payload = snapshot.model_dump(mode="json")
            payload_json = json.dumps(payload)
            await client.publish(PORTFOLIO_SNAPSHOT_CHANNEL, payload_json)
            await client.xadd(PORTFOLIO_SNAPSHOT_STREAM, {"payload": payload_json}, maxlen=10_000, approximate=True)
            await asyncio.sleep(PUBLISH_INTERVAL_SECONDS)
    finally:
        await client.aclose()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
