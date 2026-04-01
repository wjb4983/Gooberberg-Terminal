"""Research worker that consumes queued backtest jobs and emits mock artifacts."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("worker-research")

JOB_QUEUE_KEY = "gb:jobs:queue"
STATE_KEY_PREFIX = "gb:jobs:state:"
WORKER_NAME = "worker-research"
JOB_TYPE = "backtest"
POLL_INTERVAL_SECONDS = 0.5
JOB_TIMEOUT_SECONDS = 20.0
MAX_ATTEMPTS = 3
ARTIFACT_ROOT = Path("/artifacts")

try:
    from redis.asyncio import Redis
except Exception:  # pragma: no cover - optional dependency import guard
    Redis = None  # type: ignore[misc, assignment]


class JobStatus(str):
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


class BacktestRequest(BaseModel):
    strategy_id: str = "placeholder-strategy"
    universe: list[str] = Field(default_factory=lambda: ["SPY"])
    start_date: str = "2024-01-01"
    end_date: str = "2024-12-31"
    benchmark: str = "SPY"


@dataclass(slots=True)
class ArtifactResult:
    ref: str
    metadata_path: Path
    sample_path: Path | None


async def run_worker() -> None:
    redis_dsn = os.getenv("GB_REDIS_DSN")
    if not Redis or not redis_dsn:
        logger.warning("worker idle: redis dependency unavailable job_id=- trace_id=-")
        while True:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    client = Redis.from_url(redis_dsn, encoding="utf-8", decode_responses=True)
    await client.ping()
    logger.info("worker connected to redis job_id=- trace_id=-")

    try:
        while True:
            popped = await client.blpop(JOB_QUEUE_KEY, timeout=1)
            if not popped:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue

            _, raw_payload = popped
            try:
                envelope = JobEnvelope.model_validate_json(raw_payload)
            except ValidationError:
                logger.exception("dropping malformed queue payload")
                continue

            if envelope.job_type != JOB_TYPE:
                await client.rpush(JOB_QUEUE_KEY, raw_payload)
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue

            await handle_with_timeout(client, envelope)
    finally:
        await client.aclose()


async def handle_with_timeout(client: Redis, envelope: JobEnvelope) -> None:
    attempts = await client.hincrby(f"{STATE_KEY_PREFIX}{envelope.job_id}", "attempt_count", 1)
    if attempts > MAX_ATTEMPTS:
        await persist_event(
            client,
            envelope,
            JobStatus.FAILED,
            f"{WORKER_NAME} max attempts exceeded ({MAX_ATTEMPTS})",
            result_ref=None,
        )
        return

    try:
        await asyncio.wait_for(process_job(client, envelope), timeout=JOB_TIMEOUT_SECONDS)
    except TimeoutError:
        await persist_event(
            client,
            envelope,
            JobStatus.FAILED,
            f"{WORKER_NAME} timed out after {JOB_TIMEOUT_SECONDS:.0f}s",
            result_ref=None,
        )
    except Exception:
        logger.exception("job execution failed", extra={"job_id": str(envelope.job_id)})
        await persist_event(
            client,
            envelope,
            JobStatus.FAILED,
            f"{WORKER_NAME} failed to process job",
            result_ref=None,
        )


async def process_job(client: Redis, envelope: JobEnvelope) -> None:
    existing_status = await client.hget(f"{STATE_KEY_PREFIX}{envelope.job_id}", "status")
    if existing_status == JobStatus.SUCCESS:
        logger.info("skip already successful job", extra={"job_id": str(envelope.job_id)})
        return

    await persist_event(client, envelope, JobStatus.RUNNING, "worker-research started backtest mock", result_ref=None)
    backtest_request = BacktestRequest.model_validate(envelope.payload)
    artifact = write_mock_artifacts(envelope, backtest_request)
    await asyncio.sleep(0.25)
    await persist_event(
        client,
        envelope,
        JobStatus.SUCCESS,
        "worker-research completed backtest mock",
        result_ref=artifact.ref,
    )


def write_mock_artifacts(envelope: JobEnvelope, request: BacktestRequest) -> ArtifactResult:
    run_dir = ARTIFACT_ROOT / "backtests" / str(envelope.job_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "job_id": str(envelope.job_id),
        "trace_id": envelope.trace_id,
        "worker": WORKER_NAME,
        "job_type": envelope.job_type,
        "generated_at": datetime.now(UTC).isoformat(),
        "request": request.model_dump(),
        "summary": {
            "status": "mock-success",
            "notes": "No real quant logic was executed.",
        },
    }

    metadata_path = run_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    sample_path = try_write_parquet(run_dir / "sample.parquet")
    return ArtifactResult(ref=f"file://{metadata_path}", metadata_path=metadata_path, sample_path=sample_path)


def try_write_parquet(parquet_path: Path) -> Path | None:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except Exception:
        return None

    table = pa.table({
        "ts": [datetime.now(UTC).isoformat()],
        "equity_curve": [100000.0],
        "drawdown": [0.0],
    })
    pq.write_table(table, parquet_path)
    return parquet_path


async def persist_event(
    client: Redis,
    envelope: JobEnvelope,
    status: str,
    detail: str,
    result_ref: str | None,
) -> None:
    event_at = datetime.now(UTC).isoformat()
    mapping = {
        "job_id": str(envelope.job_id),
        "trace_id": envelope.trace_id,
        "status": status,
        "detail": detail,
        "updated_at": event_at,
    }
    if result_ref:
        mapping["result_ref"] = result_ref
    await client.hset(f"{STATE_KEY_PREFIX}{envelope.job_id}", mapping=mapping)


def main() -> None:
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("worker interrupted trace_id=%s", uuid.uuid4())


if __name__ == "__main__":
    main()
