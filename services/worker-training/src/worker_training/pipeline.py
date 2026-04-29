"""Pipeline orchestration for worker training."""

from __future__ import annotations

import logging
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

StageEmitter = Callable[[str, float, str, str | None], Awaitable[None]]


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


async def run_training_pipeline(
    envelope: JobEnvelope,
    emit: StageEmitter,
) -> None:
    request: TrainingRunRequest | None = None
    artifact: ArtifactResult | None = None

    async def _emit(stage_key: str, *, status: str = JobStatus.RUNNING, result_ref: str | None = None) -> None:
        stage = STAGES[stage_key]
        logger.info(
            "pipeline stage update",
            extra={
                "job_id": str(envelope.job_id),
                "trace_id": envelope.trace_id,
                "stage": stage.name,
                "status": status,
                "progress_pct": stage.progress_pct,
            },
        )
        await emit(status, stage.progress_pct, stage.message, result_ref)

    await _emit("load_intent")
    request = TrainingRunRequest.model_validate(envelope.payload)

    await _emit("qualify_dataset")
    await ensure_data_ready(envelope=envelope)

    await _emit("materialize_splits")

    await _emit("fit_predict")
    try:
        artifact = write_mock_artifacts(envelope, request)
    except AdapterExecutionError as exc:
        error_ref = write_error_artifact(envelope, request, exc)
        await emit(JobStatus.FAILED, 100.0, f"{exc.code}: {exc}", error_ref)
        return

    await _emit("evaluate")
    await _emit("persist_artifacts")
    await _emit("emit_lifecycle", status=JobStatus.SUCCESS, result_ref=artifact.ref)
