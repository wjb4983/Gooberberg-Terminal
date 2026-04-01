import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC
from uuid import UUID

from fastapi import FastAPI
from pydantic import ValidationError

from app.core.config import get_settings
from app.jobs.models import JOB_QUEUE_KEY, JOB_STATE_KEY_PREFIX, JobEnvelope, JobLifecycleEvent

logger = logging.getLogger(__name__)

try:
    from redis.asyncio import Redis
except Exception:  # pragma: no cover - optional dependency import guard
    Redis = None  # type: ignore[misc, assignment]


class JobRedisRepository:
    def __init__(self, client: Redis | None) -> None:
        self._client = client

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def enqueue(self, envelope: JobEnvelope, event: JobLifecycleEvent) -> None:
        if not self._client:
            return
        state_key = f"{JOB_STATE_KEY_PREFIX}{envelope.job_id}"
        pipe = self._client.pipeline()
        pipe.hset(state_key, mapping=self._event_mapping(event))
        pipe.rpush(JOB_QUEUE_KEY, envelope.model_dump_json())
        await pipe.execute()

    async def persist_event(self, event: JobLifecycleEvent) -> None:
        if not self._client:
            return
        await self._client.hset(
            f"{JOB_STATE_KEY_PREFIX}{event.job_id}",
            mapping=self._event_mapping(event),
        )

    async def get_latest_event(self, job_id: UUID) -> JobLifecycleEvent | None:
        if not self._client:
            return None
        payload: dict[str, str] = await self._client.hgetall(f"{JOB_STATE_KEY_PREFIX}{job_id}")
        if not payload:
            return None
        try:
            return JobLifecycleEvent.model_validate(payload)
        except ValidationError:
            logger.exception("failed to decode redis event payload", extra={"job_id": str(job_id)})
            return None

    @staticmethod
    def _event_mapping(event: JobLifecycleEvent) -> dict[str, str]:
        mapping = {
            "job_id": str(event.job_id),
            "trace_id": event.trace_id,
            "status": event.status.value,
            "detail": event.detail,
            "updated_at": event.updated_at.astimezone(UTC).isoformat(),
        }
        if event.result_ref:
            mapping["result_ref"] = event.result_ref
        return mapping


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
            logger.exception("redis ping failed; api continues with in-memory fallback")
            await client.aclose()
            client = None

    app.state.redis_client = client
    app.state.job_repo = JobRedisRepository(client)
    try:
        yield
    finally:
        if client:
            await client.aclose()
