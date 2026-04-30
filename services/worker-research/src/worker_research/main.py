"""Research worker that consumes queued backtest jobs and emits deterministic backtest artifacts."""

from __future__ import annotations

import asyncio
import hashlib
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
from gb_core.lineage import LineageReference, LineageSpec, resolve_lineage_spec

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
PIPELINE_VERSION = "research-pipeline.v2"
PROD_PIPELINE_ENABLED = os.getenv("GB_WORKER_RESEARCH_PROD_PIPELINE_ENABLED", "0").lower() in {"1", "true", "yes", "on"}
CONTROL_PLANE_EVENTS_URL = os.getenv("GB_CONTROL_PLANE_EVENTS_URL", "http://localhost:8000/api/v1")
HEARTBEAT_INTERVAL_SECONDS = float(os.getenv("GB_WORKER_HEARTBEAT_INTERVAL_SECONDS", "15"))

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
    lineage: LineageSpec | None = None
    lineage_ref: LineageReference | None = None
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
    checksum: str


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
    if not PROD_PIPELINE_ENABLED:
        await persist_event(client, envelope, JobStatus.RUNNING, 25.0, "legacy_pipeline", None)
        request = BacktestRequest.model_validate(envelope.payload)
        artifact = write_legacy_artifacts(envelope, request)
        await persist_event(client, envelope, JobStatus.SUCCESS, 100.0, "legacy_completed", artifact.ref)
        return

    await emit_terminal_event(client, envelope, JobStatus.RUNNING, 5.0, "validate_request", None)
    request = validate_request(envelope)
    await emit_terminal_event(client, envelope, JobStatus.RUNNING, 20.0, "load_inputs", None)
    loaded = load_inputs(request)
    await emit_terminal_event(client, envelope, JobStatus.RUNNING, 45.0, "execute_strategy", None)
    executed = execute_strategy(envelope, request, loaded)
    await emit_terminal_event(client, envelope, JobStatus.RUNNING, 65.0, "compute_metrics", None)
    computed = compute_metrics(executed)
    await emit_terminal_event(client, envelope, JobStatus.RUNNING, 85.0, "persist_artifacts", None)
    artifact = persist_artifacts(envelope, request, loaded, computed)
    await emit_terminal_event(client, envelope, JobStatus.SUCCESS, 100.0, "completed", artifact.ref)


def write_legacy_artifacts(envelope: JobEnvelope, request: BacktestRequest) -> ArtifactResult:
    run_dir = ARTIFACT_ROOT / "backtests" / str(envelope.job_id) / "legacy"
    run_dir.mkdir(parents=True, exist_ok=True)
    schema_version = "backtest.v1"
    seed = sum(ord(c) for c in str(envelope.job_id)) % 11
    symbols = request.universe or ["SPY"]
    trades = []
    positions = []
    attribution = []
    gross_pnl = 0.0
    for idx, symbol in enumerate(symbols):
        qty = 10 + ((seed + idx) % 5) * 5
        entry = 100.0 + idx * 3.0
        exit_px = entry + ((seed + idx) % 7 - 3) * 0.8
        pnl = round((exit_px - entry) * qty, 2)
        gross_pnl += pnl
        trades.append({"trade_id": f"t-{idx+1}", "symbol": symbol, "side": "buy", "quantity": qty, "entry_price": entry, "exit_price": round(exit_px,2), "pnl": pnl})
        positions.append({"symbol": symbol, "quantity": 0, "avg_price": 0.0, "market_price": round(exit_px,2), "market_value": 0.0, "unrealized_pnl": 0.0})
        attribution.append({"symbol": symbol, "pnl_contribution": pnl, "weight": round(1/len(symbols),4)})
    starting_equity = 100000.0
    ending_equity = round(starting_equity + gross_pnl, 2)
    pnl = {"starting_equity": starting_equity, "ending_equity": ending_equity, "gross_pnl": round(gross_pnl,2), "return_pct": round((gross_pnl/starting_equity)*100,4)}
    risk_metrics = {"max_drawdown_pct": round(abs(min(gross_pnl,0))/starting_equity*100,4), "volatility_annualized": round(8.5 + seed*0.3,4), "sharpe_ratio": round((gross_pnl/1000.0),4)}
    output = {"schema_version": schema_version, "job_id": str(envelope.job_id), "run_id": str(envelope.run_id) if envelope.run_id else None, "trace_id": envelope.trace_id, "worker": WORKER_NAME, "generated_at": datetime.now(UTC).isoformat(), "request": request.model_dump(), "trades": trades, "positions": positions, "pnl": pnl, "risk_metrics": risk_metrics, "attribution": attribution}
    metadata_path = run_dir / "backtest_output.json"
    payload = json.dumps(output, indent=2)
    metadata_path.write_text(payload, encoding="utf-8")
    sample_path = try_write_parquet(run_dir / "equity_curve.parquet")
    checksum = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return ArtifactResult(ref=f"file://{metadata_path}", metadata_path=metadata_path, sample_path=sample_path, checksum=checksum)


def validate_request(envelope: JobEnvelope) -> BacktestRequest:
    request = BacktestRequest.model_validate(envelope.payload)
    request.lineage = resolve_lineage_spec(lineage=request.lineage, lineage_ref=request.lineage_ref, config_payload=envelope.payload)
    return request


def load_inputs(request: BacktestRequest) -> dict[str, Any]:
    symbols = sorted(set(request.universe or ["SPY"]))
    stable_ts = f"{request.start_date}T00:00:00+00:00"
    return {"symbols": symbols, "stable_timestamp": stable_ts}


def execute_strategy(envelope: JobEnvelope, request: BacktestRequest, loaded_inputs: dict[str, Any]) -> dict[str, Any]:
    seed_src = f"{envelope.job_id}:{envelope.run_id or 'none'}:{request.strategy_id}:{','.join(loaded_inputs['symbols'])}:{request.start_date}:{request.end_date}:{request.benchmark}"
    seed = int(hashlib.sha256(seed_src.encode("utf-8")).hexdigest()[:8], 16)
    trades: list[dict[str, Any]] = []
    positions: list[dict[str, Any]] = []
    attribution: list[dict[str, Any]] = []
    gross_pnl = 0.0
    symbols = loaded_inputs["symbols"]
    for idx, symbol in enumerate(symbols):
        qty = 10 + ((seed + idx) % 5) * 5
        entry = 100.0 + idx * 3.0
        exit_px = entry + ((seed + idx) % 7 - 3) * 0.8
        pnl = round((exit_px - entry) * qty, 2)
        gross_pnl += pnl
        trades.append({"trade_id": f"t-{idx+1}", "symbol": symbol, "side": "buy", "quantity": qty, "entry_price": entry, "exit_price": round(exit_px, 2), "pnl": pnl})
        positions.append({"symbol": symbol, "quantity": 0, "avg_price": 0.0, "market_price": round(exit_px, 2), "market_value": 0.0, "unrealized_pnl": 0.0})
        attribution.append({"symbol": symbol, "pnl_contribution": pnl, "weight": round(1 / len(symbols), 4)})
    return {"seed": seed, "gross_pnl": round(gross_pnl, 2), "trades": trades, "positions": positions, "attribution": attribution}


def compute_metrics(executed: dict[str, Any]) -> dict[str, Any]:
    starting_equity = 100000.0
    ending_equity = round(starting_equity + executed["gross_pnl"], 2)
    gross_pnl = executed["gross_pnl"]
    return {
        "pnl": {"starting_equity": starting_equity, "ending_equity": ending_equity, "gross_pnl": gross_pnl, "return_pct": round((gross_pnl / starting_equity) * 100, 4)},
        "risk_metrics": {"max_drawdown_pct": round(abs(min(gross_pnl, 0)) / starting_equity * 100, 4), "volatility_annualized": round(8.5 + (executed["seed"] % 11) * 0.3, 4), "sharpe_ratio": round(gross_pnl / 1000.0, 4)},
    }


def persist_artifacts(envelope: JobEnvelope, request: BacktestRequest, loaded_inputs: dict[str, Any], computed: dict[str, Any]) -> ArtifactResult:
    run_key = str(envelope.run_id) if envelope.run_id else "default"
    run_dir = ARTIFACT_ROOT / "backtests" / str(envelope.job_id) / run_key / PIPELINE_VERSION
    run_dir.mkdir(parents=True, exist_ok=True)
    request_payload = request.model_dump()
    request_payload["universe"] = loaded_inputs["symbols"]
    input_fingerprint = hashlib.sha256(
        json.dumps(request_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    output = {
        "schema_version": "backtest.v2",
        "job_id": str(envelope.job_id),
        "run_id": str(envelope.run_id) if envelope.run_id else None,
        "trace_id": envelope.trace_id,
        "worker": WORKER_NAME,
        "generated_at": loaded_inputs["stable_timestamp"],
        "pipeline_version": PIPELINE_VERSION,
        "determinism_mode": "strict",
        "input_fingerprint": input_fingerprint,
        "request": request_payload,
        "metrics": computed,
        "checksum": "",
    }
    canonical_payload = json.dumps(output, indent=2, sort_keys=True)
    checksum = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
    output["checksum"] = checksum
    metadata_path = run_dir / "backtest_output.v2.json"
    metadata_path.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    sample_path = try_write_parquet(run_dir / "equity_curve.parquet", loaded_inputs["stable_timestamp"])
    return ArtifactResult(ref=f"file://{metadata_path}", metadata_path=metadata_path, sample_path=sample_path, checksum=checksum)


def try_write_parquet(parquet_path: Path, stable_timestamp: str | None = None) -> Path | None:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except Exception:
        return None
    ts = stable_timestamp or datetime.now(UTC).isoformat()
    table = pa.table({"ts": [ts], "equity_curve": [100000.0], "drawdown": [0.0]})
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


async def emit_terminal_event(client: Redis, envelope: JobEnvelope, status: str, progress_pct: float, stage_name: str, result_ref: str | None) -> None:
    await persist_event(client, envelope, status, progress_pct, stage_name, result_ref)


def main() -> None:
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("worker interrupted trace_id=%s", uuid.uuid4())


if __name__ == "__main__":
    main()
