import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.jobs.models import JOB_QUEUE_KEY, JobEnvelope

logger = logging.getLogger(__name__)

try:
    from redis.asyncio import Redis
except Exception:  # pragma: no cover - optional dependency import guard
    Redis = None  # type: ignore[misc, assignment]


class JobRedisQueue:
    def __init__(self, client: Redis | None) -> None:
        self._client = client

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def enqueue(self, envelope: JobEnvelope) -> None:
        if not self._client:
            return
        await self._client.rpush(JOB_QUEUE_KEY, envelope.model_dump_json())


@asynccontextmanager
async def lifespan_redis(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    client = None
    if Redis and settings.redis_dsn:
        client = Redis.from_url(settings.redis_dsn, encoding="utf-8", decode_responses=True)
        try:
            await client.ping()
            logger.info("redis connected for api-control-plane")
        except Exception:
            logger.exception("redis ping failed; api continues with no queue backend")
            await client.aclose()
            client = None

    app.state.redis_client = client
    app.state.job_queue = JobRedisQueue(client)
    try:
        yield
    finally:
        if client:
            await client.aclose()
