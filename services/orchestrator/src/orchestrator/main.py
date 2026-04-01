"""Orchestrator worker that consumes queued jobs from Redis and emits lifecycle transitions."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("orchestrator")

QUEUE_KEY = "gb:jobs:queue"
STATE_KEY_PREFIX = "gb:jobs:state:"
POLL_INTERVAL_SECONDS = 1.0

try:
    from redis.asyncio import Redis
except Exception:  # pragma: no cover - optional dependency import guard
    Redis = None  # type: ignore[misc, assignment]


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class JobEnvelope(BaseModel):
    job_id: UUID
    trace_id: str
    job_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    queued_at: datetime


class JobLifecycleEvent(BaseModel):
    job_id: UUID
    trace_id: str
    status: JobStatus
    detail: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


async def run_orchestrator() -> None:
    redis_dsn = os.getenv("GB_REDIS_DSN")
    if not Redis or not redis_dsn:
        logger.warning(
            "orchestrator idle: redis dependency unavailable job_id=- trace_id=-"
        )
        # TODO: add durable local queue fallback for orchestrator when Redis is absent.
        while True:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    client = Redis.from_url(redis_dsn, encoding="utf-8", decode_responses=True)
    await client.ping()
    logger.info("orchestrator connected to redis job_id=- trace_id=-")

    try:
        while True:
            popped = await client.blpop(QUEUE_KEY, timeout=1)
            if not popped:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue

            _, payload = popped
            envelope = JobEnvelope.model_validate_json(payload)
            await persist_event(
                client,
                JobLifecycleEvent(
                    job_id=envelope.job_id,
                    trace_id=envelope.trace_id,
                    status=JobStatus.RUNNING,
                    detail="orchestrator started mock execution",
                ),
            )
            await asyncio.sleep(0.5)
            await persist_event(
                client,
                JobLifecycleEvent(
                    job_id=envelope.job_id,
                    trace_id=envelope.trace_id,
                    status=JobStatus.SUCCESS,
                    detail="orchestrator completed mock execution",
                ),
            )
    finally:
        await client.aclose()


async def persist_event(client: Redis, event: JobLifecycleEvent) -> None:
    await client.hset(
        f"{STATE_KEY_PREFIX}{event.job_id}",
        mapping={
            "job_id": str(event.job_id),
            "trace_id": event.trace_id,
            "status": event.status.value,
            "detail": event.detail,
            "updated_at": event.updated_at.astimezone(UTC).isoformat(),
        },
    )
    logger.info(
        f"job status transition job_id={event.job_id} trace_id={event.trace_id}"
    )


def main() -> None:
    try:
        asyncio.run(run_orchestrator())
    except KeyboardInterrupt:
        logger.info(f"orchestrator interrupted job_id=- trace_id={uuid.uuid4()}")


if __name__ == "__main__":
    main()
