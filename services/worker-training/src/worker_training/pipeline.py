"""Pipeline orchestration for worker training."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
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
    "preflight": PipelineStage("preflight", 15.0, "validating deterministic lineage preflight"),
    "qualify_dataset": PipelineStage("qualify_dataset", 20.0, "qualifying dataset"),
    "materialize_splits": PipelineStage("materialize_splits", 45.0, "materializing data splits"),
    "fit_predict": PipelineStage("fit_predict", 70.0, "running adapter fit/predict"),
    "evaluate": PipelineStage("evaluate", 90.0, "evaluating run outputs"),
    "persist_artifacts": PipelineStage("persist_artifacts", 95.0, "persisting training artifacts"),
    "emit_lifecycle": PipelineStage("emit_lifecycle", 100.0, "training run completed"),
}
REQUIRED_ARTIFACT_ROLES = ("model", "metadata", "diagnostics", "metrics_parquet")


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_json(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return _sha256_bytes(canonical)


def _resolve_runtime_code_hash() -> str:
    return os.getenv("GB_RUNTIME_CODE_SHA", "0" * 40).strip().lower()


def _build_expected_manifest() -> list[dict[str, Any]]:
    return [
        {"role": role, "uri": "pending://artifact", "algorithm": "sha256", "hash": "0" * 64, "size_bytes": 0}
        for role in REQUIRED_ARTIFACT_ROLES
    ]


def _preflight_lineage(envelope: JobEnvelope, request: TrainingRunRequest) -> tuple[bool, str, dict[str, Any] | None]:
    lineage = request.lineage
    if lineage is None:
        return False, "deterministic_gate_error: missing lineage", {"error_code": "missing_lineage"}
    if "seed" not in envelope.payload:
        return False, "deterministic_gate_error: explicit seed missing", {"error_code": "missing_seed"}

    runtime_dataset_fingerprint = _sha256_json({"dataset_ref": request.dataset_ref, "dataset_id": request.dataset_id, "seed": request.seed})
    runtime_code_hash = _resolve_runtime_code_hash()
    runtime_config_digest = _sha256_json(request.model_dump(mode="json"))
    if lineage.dataset_fingerprint.hash != runtime_dataset_fingerprint:
        return False, "deterministic_gate_error: dataset fingerprint mismatch", {"error_code": "dataset_fingerprint_mismatch"}
    if lineage.code_hash.git_commit_sha != runtime_code_hash:
        return False, "deterministic_gate_error: code hash mismatch", {"error_code": "code_hash_mismatch"}
    if lineage.config_digest.digest != runtime_config_digest:
        return False, "deterministic_gate_error: config digest mismatch", {"error_code": "config_digest_mismatch"}
    if lineage.seed != request.seed:
        return False, "deterministic_gate_error: seed mismatch", {"error_code": "seed_mismatch"}
    return True, "", None


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
    await _emit("preflight")
    success, gate_message, gate_metrics = _preflight_lineage(envelope, request)
    if not success:
        await emit(JobStatus.FAILED, 100.0, gate_message, None, gate_metrics)
        return

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
    artifact_paths: dict[str, Path | None] = {
        "metadata": artifact.metadata_path,
        "model": artifact.metadata_path.parent / "model.bin",
        "diagnostics": artifact.diagnostics_path,
        "metrics_parquet": artifact.sample_path,
    }
    manifest = _build_expected_manifest()
    missing_roles = [role for role, path in artifact_paths.items() if path is None or not path.exists()]
    if missing_roles:
        await emit(
            JobStatus.FAILED,
            100.0,
            "deterministic_gate_error: required artifact set incomplete",
            artifact.ref,
            {"error_code": "artifact_set_incomplete", "missing_roles": missing_roles},
        )
        return
    finalized_manifest: list[dict[str, Any]] = []
    for entry in manifest:
        role = entry["role"]
        path = artifact_paths[role]
        assert path is not None
        content = path.read_bytes()
        finalized_manifest.append(
            {**entry, "uri": f"file://{path}", "size_bytes": len(content), "hash": _sha256_bytes(content)}
        )
    completion_metrics = dict(artifact.metric_bundle or {})
    completion_metrics["artifact_manifest"] = finalized_manifest
    await _emit("emit_lifecycle", status=JobStatus.SUCCESS, result_ref=artifact.ref, metric_bundle=completion_metrics)
