"""Training worker that consumes queued training jobs and emits mock artifacts."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import date
import urllib.request
import uuid
from dataclasses import dataclass
from hashlib import sha256
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError

from worker_training.adapters.base import AdapterCapability
from worker_training.adapters.registry import AdapterRegistry
from worker_training.data.materializer import materialize_dataset_bundle
from worker_training.task_heads import TASK_HEAD_REGISTRY

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("worker-training")

JOB_QUEUE_KEY = "gb:jobs:queue"
STATE_KEY_PREFIX = "gb:jobs:state:"
WORKER_NAME = "worker-training"
JOB_TYPE = "training"
POLL_INTERVAL_SECONDS = 0.5
JOB_TIMEOUT_SECONDS = 30.0
MAX_ATTEMPTS = 3
ARTIFACT_ROOT = Path("/artifacts")
CONTROL_PLANE_EVENTS_URL = os.getenv("GB_CONTROL_PLANE_EVENTS_URL", "http://localhost:8000/api/v1")
HEARTBEAT_INTERVAL_SECONDS = float(os.getenv("GB_WORKER_HEARTBEAT_INTERVAL_SECONDS", "15"))

try:
    from redis.asyncio import Redis
except Exception:  # pragma: no cover
    Redis = None  # type: ignore[misc, assignment]


class JobStatus(str):
    QUEUED = "queued"
    WAITING_FOR_DATA = "waiting_for_data"
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


class TrainingRunRequest(BaseModel):
    dataset_id: str | None = None
    model_name: str = "placeholder-model"
    dataset_ref: str = "dataset://placeholder"
    epochs: int = 1
    learning_rate: float = 0.001
    seed: int = 7
    model_family: str = "statistical"
    task: str = "forecasting"
    subtask: str = "univariate"
    data_type: str = "timeseries_float"


class DatasetLookupResponse(BaseModel):
    dataset_id: str
    source: str
    symbol: str
    timeframe: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CacheCoverageResponse(BaseModel):
    symbol: str
    timeframe: str
    available_start: date | None = None
    available_end: date | None = None
    coverage_pct: float = 0.0


@dataclass(slots=True)
class ArtifactResult:
    ref: str
    metadata_path: Path
    sample_path: Path | None
    diagnostics_path: Path
    metrics_payload: dict[str, Any]


@dataclass(slots=True)
class AdapterOutput:
    adapter_name: str
    model_blob: bytes
    metrics_payload: dict[str, Any]
    diagnostics: dict[str, Any]


class AdapterExecutionError(RuntimeError):
    def __init__(self, code: str, message: str, diagnostics: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.diagnostics = diagnostics or {}


class TrainingAdapter:
    name = "base"
    model_family = "base"
    capabilities: tuple[AdapterCapability, ...] = ()

    def run(self, request: TrainingRunRequest) -> AdapterOutput:
        raise NotImplementedError


class ArimaAdapter(TrainingAdapter):
    name = "arima"
    model_family = "statistical"
    capabilities = (AdapterCapability(task="forecasting", subtask="univariate", data_type="timeseries_float"),)

    def run(self, request: TrainingRunRequest) -> AdapterOutput:
        coeff = round(0.8 + request.learning_rate, 5)
        return AdapterOutput(
            adapter_name=self.name,
            model_blob=f"ARIMA({request.epochs})::{request.seed}".encode("utf-8"),
            metrics_payload={"primary_metric": 0.9123, "aic": 123.4, "bic": 127.8},
            diagnostics={"coefficients": [coeff, -0.12, 0.05], "converged": True},
        )


class KalmanFilterAdapter(TrainingAdapter):
    name = "kalman_filter"
    model_family = "state_space"
    capabilities = (AdapterCapability(task="forecasting", subtask="univariate", data_type="timeseries_float"),)

    def run(self, request: TrainingRunRequest) -> AdapterOutput:
        q = round(request.learning_rate * 0.5, 6)
        return AdapterOutput(
            adapter_name=self.name,
            model_blob=f"KALMAN::{request.seed}".encode("utf-8"),
            metrics_payload={"primary_metric": 0.8877, "rmse": 0.114, "nll": 2.31},
            diagnostics={"transition_noise": q, "state_dim": 4, "stability_score": 0.97},
        )


class TorchNNTimeSeriesAdapter(TrainingAdapter):
    name = "torch_nn_timeseries"
    model_family = "neural"
    capabilities = (
        AdapterCapability(task="forecasting", subtask="univariate", data_type="timeseries_float"),
        AdapterCapability(task="forecasting", subtask="multivariate", data_type="timeseries_float"),
    )

    def run(self, request: TrainingRunRequest) -> AdapterOutput:
        if request.epochs <= 0:
            raise AdapterExecutionError(
                code="invalid_epochs",
                message="epochs must be greater than zero",
                diagnostics={"epochs": request.epochs},
            )
        return AdapterOutput(
            adapter_name=self.name,
            model_blob=f"TORCHNN::{request.epochs}::{request.seed}".encode("utf-8"),
            metrics_payload={"primary_metric": 0.9345, "loss": 0.0821, "val_loss": 0.0917},
            diagnostics={"layers": [64, 32], "dropout": 0.1, "best_epoch": min(request.epochs, 4)},
        )


ADAPTERS: dict[str, TrainingAdapter] = {
    "arima": ArimaAdapter(),
    "kalman_filter": KalmanFilterAdapter(),
    "torch_nn_timeseries": TorchNNTimeSeriesAdapter(),
}
ADAPTER_REGISTRY = AdapterRegistry(adapters_by_family={adapter.model_family: adapter for adapter in ADAPTERS.values()})


async def run_worker() -> None:
    redis_dsn = os.getenv("GB_REDIS_DSN")
    if not Redis or not redis_dsn:
        logger.warning("worker idle: redis dependency unavailable job_id=- trace_id=-")
        while True:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    client = Redis.from_url(redis_dsn, encoding="utf-8", decode_responses=True)
    await client.ping()
    heartbeat_task = asyncio.create_task(emit_worker_heartbeat())

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
        heartbeat_task.cancel()
        await client.aclose()


async def emit_worker_heartbeat() -> None:
    url = f"{CONTROL_PLANE_EVENTS_URL}/health/queue/heartbeat"
    while True:
        def _send() -> None:
            req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=3):
                pass

        try:
            await asyncio.to_thread(_send)
        except Exception:
            logger.debug("worker heartbeat failed")
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)


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
    from worker_training.pipeline import run_training_pipeline

    async def _emit(status: str, progress_pct: float, message: str, result_ref: str | None) -> None:
        await persist_event(client, envelope, status, progress_pct, message, result_ref)

    await run_training_pipeline(envelope, _emit)


def write_error_artifact(envelope: JobEnvelope, request: TrainingRunRequest, exc: AdapterExecutionError) -> str:
    run_dir = ARTIFACT_ROOT / "training" / str(envelope.job_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    error_payload = {
        "schema_version": "training-error/v1",
        "job_id": str(envelope.job_id),
        "trace_id": envelope.trace_id,
        "model_name": request.model_name,
        "error_code": exc.code,
        "error_message": str(exc),
        "diagnostics": exc.diagnostics,
        "failed_at": datetime.now(UTC).isoformat(),
    }
    error_path = run_dir / "error.json"
    error_path.write_text(json.dumps(error_payload, indent=2), encoding="utf-8")
    return f"file://{error_path}"


async def ensure_data_ready(envelope: JobEnvelope) -> None:
    request = TrainingRunRequest.model_validate(envelope.payload)
    if not request.dataset_id:
        return

    dataset_lookup = await control_plane_get_json(f"/market-data/datasets/{request.dataset_id}")
    if not dataset_lookup:
        return
    dataset = DatasetLookupResponse.model_validate(dataset_lookup)
    required_start = dataset.metadata.get("start_date")
    required_end = dataset.metadata.get("end_date")
    if not isinstance(required_start, str) or not isinstance(required_end, str):
        return
    try:
        start_date = date.fromisoformat(required_start)
        end_date = date.fromisoformat(required_end)
    except ValueError:
        return

    symbols_raw = dataset.metadata.get("symbols")
    resolutions_raw = dataset.metadata.get("resolutions")
    symbols = [item for item in symbols_raw if isinstance(item, str)] if isinstance(symbols_raw, list) else [dataset.symbol]
    resolutions = (
        [item for item in resolutions_raw if isinstance(item, str)] if isinstance(resolutions_raw, list) else [dataset.timeframe]
    )

    missing: list[tuple[str, str]] = []
    for symbol in symbols:
        for resolution in resolutions:
            coverage_raw = await control_plane_get_json(f"/market-data/cache-coverage?symbol={symbol}&timeframe={resolution}")
            if not coverage_raw:
                missing.append((symbol, resolution))
                continue
            coverage = CacheCoverageResponse.model_validate(coverage_raw)
            if (
                coverage.available_start is None
                or coverage.available_end is None
                or coverage.available_start > start_date
                or coverage.available_end < end_date
            ):
                missing.append((symbol, resolution))

    if not missing:
        return

    logger.info("pipeline stage update", extra={"job_id": str(envelope.job_id), "trace_id": envelope.trace_id, "stage": "data_wait", "status": JobStatus.WAITING_FOR_DATA, "progress_pct": 1.0})
    by_resolution: dict[str, set[str]] = {}
    for symbol, resolution in missing:
        by_resolution.setdefault(resolution, set()).add(symbol)
    for resolution, symbols_for_resolution in by_resolution.items():
        await control_plane_post_json(
            "/market-data/ingestions",
            {
                "provider": dataset.metadata.get("provider", "massive"),
                "asset_class": dataset.metadata.get("asset_class", "stocks"),
                "universe_members": sorted(symbols_for_resolution),
                "resolutions": [resolution],
                "feature_recipe_version": dataset.metadata.get("feature_recipe_version", "v1"),
                "label_recipe_version": dataset.metadata.get("label_recipe_version", "v1"),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

    logger.info("pipeline stage update", extra={"job_id": str(envelope.job_id), "trace_id": envelope.trace_id, "stage": "data_ready", "status": JobStatus.RUNNING, "progress_pct": 5.0})


def write_mock_artifacts(envelope: JobEnvelope, request: TrainingRunRequest) -> ArtifactResult:
    run_dir = ARTIFACT_ROOT / "training" / str(envelope.job_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    adapter = ADAPTER_REGISTRY.resolve(request)
    output = adapter.run(request)

    model_path = run_dir / "model.bin"
    model_path.write_bytes(output.model_blob)
    checksum = sha256(output.model_blob).hexdigest()
    diagnostics_path = run_dir / "diagnostics.json"
    diagnostics_path.write_text(json.dumps(output.diagnostics, indent=2), encoding="utf-8")
    task_head = TASK_HEAD_REGISTRY.resolve(request.task, request.subtask)
    bundle = materialize_dataset_bundle(request.model_dump(), seed=request.seed)
    metadata = {
        "job_id": str(envelope.job_id),
        "run_id": str(envelope.run_id) if envelope.run_id else None,
        "trace_id": envelope.trace_id,
        "worker": WORKER_NAME,
        "job_type": envelope.job_type,
        "generated_at": datetime.now(UTC).isoformat(),
        "schema_version": "training-artifact/v1",
        "adapter": output.adapter_name,
        "model_checksum_sha256": checksum,
        "diagnostics_ref": f"file://{diagnostics_path}",
        "metrics_payload": output.metrics_payload,
        "target_schema": task_head.build_target_schema(),
        "prediction_output": task_head.format_prediction(output.metrics_payload),
        "request": request.model_dump(),
        "split_manifest": bundle.split_manifest,
    }
    metadata_path = run_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    sample_path = try_write_parquet(run_dir / "metrics.parquet")
    return ArtifactResult(
        ref=f"file://{metadata_path}",
        metadata_path=metadata_path,
        sample_path=sample_path,
        diagnostics_path=diagnostics_path,
        metrics_payload=output.metrics_payload,
    )


def try_write_parquet(parquet_path: Path) -> Path | None:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except Exception:
        return None
    table = pa.table({"epoch": [1], "loss": [0.1234], "val_loss": [0.1337]})
    pq.write_table(table, parquet_path)
    return parquet_path


async def persist_event(client: Redis, envelope: JobEnvelope, status: str, progress_pct: float, message: str, result_ref: str | None) -> None:
    event_at = datetime.now(UTC)
    mapping = {
        "job_id": str(envelope.job_id),
        "run_id": str(envelope.run_id) if envelope.run_id else "",
        "status": status,
        "progress_pct": int(progress_pct),
        "message": message,
        "detail": f"{WORKER_NAME}: {message}",
        "updated_at": event_at.isoformat(),
    }
    if result_ref:
        mapping["result_ref"] = result_ref
    await client.hset(f"{STATE_KEY_PREFIX}{envelope.job_id}", mapping=mapping)
    await post_event(envelope, mapping)


async def post_event(envelope: JobEnvelope, mapping: dict[str, Any]) -> None:
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
    body = json.dumps(payload).encode("utf-8")
    url = f"{CONTROL_PLANE_EVENTS_URL}/jobs/{envelope.job_id}/events"

    def _send() -> None:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=3):
            pass

    try:
        await asyncio.to_thread(_send)
    except Exception:
        logger.debug("event post failed", extra={"job_id": str(envelope.job_id)})


async def control_plane_get_json(path: str) -> dict[str, Any] | None:
    url = f"{CONTROL_PLANE_EVENTS_URL}{path}"

    def _send() -> dict[str, Any] | None:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        return await asyncio.to_thread(_send)
    except Exception:
        return None


async def control_plane_post_json(path: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    url = f"{CONTROL_PLANE_EVENTS_URL}{path}"
    body = json.dumps(payload).encode("utf-8")

    def _send() -> dict[str, Any] | None:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=3) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        return await asyncio.to_thread(_send)
    except Exception:
        return None


def main() -> None:
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("worker interrupted trace_id=%s", uuid.uuid4())


if __name__ == "__main__":
    main()
