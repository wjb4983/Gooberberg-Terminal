"""Pipeline orchestration for worker training."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from worker_training.main import (
    AdapterExecutionError,
    ArtifactResult,
    JobEnvelope,
    JobStatus,
    TrainingRunRequest,
    ensure_data_ready,
    write_error_artifact,
    write_mock_artifacts,
)

logger = logging.getLogger("worker-training.pipeline")

StageEmitter = Callable[[str, float, str, str | None, dict[str, Any] | None], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class PipelineStage:
    name: str
    progress_pct: float
    message: str


STAGES = {
    "load_intent": PipelineStage("load_intent", 10.0, "training worker accepted job"),
    "qualify_dataset": PipelineStage("qualify_dataset", 20.0, "qualifying dataset"),
    "materialize_splits": PipelineStage("materialize_splits", 45.0, "materializing data splits"),
    "fit_predict": PipelineStage("fit_predict", 70.0, "running adapter fit/predict"),
    "evaluate": PipelineStage("evaluate", 90.0, "evaluating run outputs"),
    "persist_artifacts": PipelineStage("persist_artifacts", 95.0, "persisting training artifacts"),
    "emit_lifecycle": PipelineStage("emit_lifecycle", 100.0, "training run completed"),
}


def _strict_pipeline_enabled_for_family(model_family: str) -> bool:
    strict_mode_enabled = os.getenv("GB_TRAINING_PIPELINE_STRICT_MODE", "0").strip().lower() in {"1", "true", "yes", "on"}
    if not strict_mode_enabled:
        return False

    families_raw = os.getenv("GB_TRAINING_PIPELINE_STRICT_MODEL_FAMILIES", "")
    enabled_families = {item.strip() for item in families_raw.split(",") if item.strip()}
    if not enabled_families:
        return True
    return model_family in enabled_families


async def run_training_pipeline(
    envelope: JobEnvelope,
    emit: StageEmitter,
) -> None:
    request: TrainingRunRequest | None = None
    artifact: ArtifactResult | None = None
    strict_mode = False

    stage_started_at = time.monotonic()

    async def _emit(
        stage_key: str,
        *,
        status: str = JobStatus.RUNNING,
        result_ref: str | None = None,
        metric_bundle: dict[str, Any] | None = None,
    ) -> None:
        nonlocal stage_started_at
        stage = STAGES[stage_key]
        now = time.monotonic()
        duration_ms = (now - stage_started_at) * 1000
        fingerprint = hashlib.sha256(json.dumps({"job_id": str(envelope.job_id), "stage": stage.name, "status": status}, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        logger.info(
            "pipeline stage update",
            extra={
                "job_id": str(envelope.job_id),
                "trace_id": envelope.trace_id,
                "stage": stage.name,
                "status": status,
                "progress_pct": stage.progress_pct,
                "duration_ms": round(duration_ms, 3),
                "success": status != JobStatus.FAILED,
                "fingerprint": fingerprint,
                "fallback_reason": None if strict_mode else "compatibility_mode",
            },
        )
        await emit(status, stage.progress_pct, stage.message, result_ref, metric_bundle)
        stage_started_at = time.monotonic()

    await _emit("load_intent")
    request = TrainingRunRequest.model_validate(envelope.payload)
    strict_mode = _strict_pipeline_enabled_for_family(request.model_family)

    await _emit("qualify_dataset")
    await ensure_data_ready(envelope=envelope)

    await _emit("materialize_splits")

    await _emit("fit_predict")
    try:
        if strict_mode:
            logger.info(
                "pipeline strict-mode routing",
                extra={
                    "job_id": str(envelope.job_id),
                    "trace_id": envelope.trace_id,
                    "model_family": request.model_family,
                    "pipeline_mode": "strict",
                },
            )
        else:
            logger.info(
                "pipeline compatibility-mode routing",
                extra={
                    "job_id": str(envelope.job_id),
                    "trace_id": envelope.trace_id,
                    "model_family": request.model_family,
                    "pipeline_mode": "compatibility",
                },
            )
        artifact = write_mock_artifacts(envelope, request)
    except AdapterExecutionError as exc:
        error_ref = write_error_artifact(envelope, request, exc)
        await emit(JobStatus.FAILED, 100.0, f"{exc.code}: {exc}", error_ref, None)
        return

    await _emit("evaluate")
    await _emit("persist_artifacts")
    await _emit("emit_lifecycle", status=JobStatus.SUCCESS, result_ref=artifact.ref, metric_bundle=artifact.metric_bundle)
