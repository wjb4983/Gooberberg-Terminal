"""Research worker that consumes queued backtest jobs and emits mock artifacts."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.request
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
CONTROL_PLANE_EVENTS_URL = os.getenv("GB_CONTROL_PLANE_EVENTS_URL", "http://localhost:8000/api/v1")

try:
    from redis.asyncio import Redis
except Exception:  # pragma: no cover
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
    run_id: UUID | None = None
    run_type: str | None = None
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
        await persist_event(client, envelope, JobStatus.FAILED, 100.0, "max attempts exceeded", None)
        return
    try:
        await asyncio.wait_for(process_job(client, envelope), timeout=JOB_TIMEOUT_SECONDS)
    except TimeoutError:
        await persist_event(client, envelope, JobStatus.FAILED, 100.0, f"timed out after {JOB_TIMEOUT_SECONDS:.0f}s", None)
    except Exception:
        logger.exception("job execution failed", extra={"job_id": str(envelope.job_id)})
        await persist_event(client, envelope, JobStatus.FAILED, 100.0, "failed to process job", None)


async def process_job(client: Redis, envelope: JobEnvelope) -> None:
    await persist_event(client, envelope, JobStatus.RUNNING, 15.0, "research worker accepted backtest", None)
    request = BacktestRequest.model_validate(envelope.payload)
    await asyncio.sleep(0.1)
    await persist_event(client, envelope, JobStatus.RUNNING, 55.0, "simulating research pass", None)
    artifact = write_mock_artifacts(envelope, request)
    await asyncio.sleep(0.1)
    await persist_event(client, envelope, JobStatus.SUCCESS, 100.0, "backtest run completed", artifact.ref)


def write_mock_artifacts(envelope: JobEnvelope, request: BacktestRequest) -> ArtifactResult:
    run_dir = ARTIFACT_ROOT / "backtests" / str(envelope.job_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "job_id": str(envelope.job_id),
        "run_id": str(envelope.run_id) if envelope.run_id else None,
        "trace_id": envelope.trace_id,
        "worker": WORKER_NAME,
        "job_type": envelope.job_type,
        "generated_at": datetime.now(UTC).isoformat(),
        "request": request.model_dump(),
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
    table = pa.table({"ts": [datetime.now(UTC).isoformat()], "equity_curve": [100000.0], "drawdown": [0.0]})
    pq.write_table(table, parquet_path)
    return parquet_path


async def persist_event(client: Redis, envelope: JobEnvelope, status: str, progress_pct: float, message: str, result_ref: str | None) -> None:
    mapping = {
        "job_id": str(envelope.job_id),
        "run_id": str(envelope.run_id) if envelope.run_id else "",
        "status": status,
        "progress_pct": int(progress_pct),
        "message": message,
        "detail": f"{WORKER_NAME}: {message}",
        "updated_at": datetime.now(UTC).isoformat(),
    }
    if result_ref:
        mapping["result_ref"] = result_ref
    await client.hset(f"{STATE_KEY_PREFIX}{envelope.job_id}", mapping=mapping)
    await post_event(envelope, mapping)


async def post_event(envelope: JobEnvelope, mapping: dict[str, Any]) -> None:
    url = f"{CONTROL_PLANE_EVENTS_URL}/jobs/{envelope.job_id}/events"
    payload = {
        "status": mapping["status"],
        "detail": mapping["detail"],
        "run_id": str(envelope.run_id) if envelope.run_id else None,
        "run_type": envelope.run_type,
        "progress_pct": float(mapping["progress_pct"]),
        "message": mapping["message"],
        "result_ref": mapping.get("result_ref"),
        "metrics": {"checkpoint": mapping["message"]},
        "notes": f"emitted by {WORKER_NAME}",
    }

    def _send() -> None:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3):
            pass

    try:
        await asyncio.to_thread(_send)
    except Exception:
        logger.debug("event post failed", extra={"job_id": str(envelope.job_id)})


def main() -> None:
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("worker interrupted trace_id=%s", uuid.uuid4())


if __name__ == "__main__":
    main()
