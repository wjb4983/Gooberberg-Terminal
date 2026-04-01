import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Any

from fastapi import FastAPI
from pydantic import ValidationError

from app.schemas import PortfolioSnapshot

logger = logging.getLogger(__name__)

PORTFOLIO_SNAPSHOT_CHANNEL = "portfolio.snapshot"


class PortfolioSnapshotCache:
    def __init__(self) -> None:
        self._snapshot: PortfolioSnapshot | None = None

    def set_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        self._snapshot = snapshot

    def get_snapshot(self) -> PortfolioSnapshot:
        if self._snapshot is not None:
            return self._snapshot
        return PortfolioSnapshot(
            account_id="paper-main",
            equity=100_000.0,
            cash=35_000.0,
            buying_power=130_000.0,
            gross_exposure=65_000.0,
            net_exposure=45_000.0,
            unrealized_pnl=1_240.5,
            realized_pnl=250.0,
            positions=[],
        )


@asynccontextmanager
async def lifespan_portfolio_cache(app: FastAPI) -> AsyncIterator[None]:
    app.state.portfolio_cache = PortfolioSnapshotCache()
    redis_client = getattr(app.state, "redis_client", None)
    if redis_client is None:
        logger.info("portfolio cache using in-memory fallback only")
        yield
        return

    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    await pubsub.subscribe(PORTFOLIO_SNAPSHOT_CHANNEL)
    task = asyncio.create_task(_consume_portfolio_snapshots(app, pubsub))
    logger.info("portfolio snapshot subscription started", extra={"channel": PORTFOLIO_SNAPSHOT_CHANNEL})
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        await pubsub.unsubscribe(PORTFOLIO_SNAPSHOT_CHANNEL)
        await pubsub.aclose()


async def _consume_portfolio_snapshots(app: FastAPI, pubsub: Any) -> None:
    while True:
        message = await pubsub.get_message(timeout=1.0)
        if not message or message.get("type") != "message":
            await asyncio.sleep(0.05)
            continue

        data = message.get("data")
        if not isinstance(data, str):
            logger.warning("portfolio snapshot message ignored: non-string payload")
            continue

        try:
            payload = json.loads(data)
            snapshot = PortfolioSnapshot.model_validate(payload)
        except (json.JSONDecodeError, ValidationError):
            logger.exception("failed to parse portfolio snapshot message")
            continue

        app.state.portfolio_cache.set_snapshot(snapshot)
