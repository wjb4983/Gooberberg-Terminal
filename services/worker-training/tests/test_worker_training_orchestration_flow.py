from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from uuid import uuid4

import asyncio

import pytest

from worker_training.main import JobEnvelope, JobStatus, handle_with_timeout, process_job


def _payload_with_lineage(seed: int = 7) -> dict:
    payload = {"model_name": "arima", "model_family": "statistical", "seed": seed, "dataset_ref": "dataset://placeholder"}
    config_digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    dataset_fingerprint = hashlib.sha256(
        json.dumps(
            {"dataset_ref": payload["dataset_ref"], "dataset_id": payload.get("dataset_id"), "seed": payload["seed"]},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    payload["lineage"] = {
        "lineage_version": 1,
        "dataset_fingerprint": {"hash": dataset_fingerprint},
        "code_hash": {"git_commit_sha": "0" * 40, "dirty": False},
        "config_digest": {"digest": config_digest},
        "seed": seed,
        "artifact_manifest": [
            {"uri": "pending://artifact", "size_bytes": 0, "hash": "0" * 64, "media_type": "application/json", "role": "placeholder"}
        ],
    }
    return payload
from worker_training.pipeline import _strict_pipeline_enabled_for_family


class _RedisStub:
    def __init__(self, *, attempts: int = 1) -> None:
        self.attempts = attempts
        self.events: list[dict[str, str | int]] = []

    async def hincrby(self, *_: object) -> int:
        return self.attempts


def test_process_job_emits_running_then_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    emitted: list[str] = []
    emitted_metric_bundles: list[dict | None] = []

    async def _persist_event(_client, _envelope, status, _progress, _message, _result_ref, metric_bundle=None):
        emitted.append(status)
        emitted_metric_bundles.append(metric_bundle)

    monkeypatch.setattr("worker_training.main.persist_event", _persist_event)
    monkeypatch.setattr("worker_training.main.ARTIFACT_ROOT", tmp_path)

    envelope = JobEnvelope(
        job_id=uuid4(),
        trace_id="trace",
        job_type="training",
        payload=_payload_with_lineage(),
        queued_at=datetime.now(UTC),
    )
    client = _RedisStub()

    asyncio.run(process_job(client, envelope))  # type: ignore[arg-type]

    assert emitted == [
        JobStatus.RUNNING,
        JobStatus.RUNNING,
        JobStatus.RUNNING,
        JobStatus.RUNNING,
        JobStatus.RUNNING,
        JobStatus.RUNNING,
        JobStatus.SUCCESS,
    ]
    assert emitted_metric_bundles[-1] is not None


def test_process_job_uses_family_fallback_for_unknown_adapter(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    emitted: list[str] = []
    emitted_metric_bundles: list[dict | None] = []

    async def _persist_event(_client, _envelope, status, _progress, _message, _result_ref, metric_bundle=None):
        emitted.append(status)
        emitted_metric_bundles.append(metric_bundle)

    monkeypatch.setattr("worker_training.main.persist_event", _persist_event)
    monkeypatch.setattr("worker_training.main.ARTIFACT_ROOT", tmp_path)
    envelope = JobEnvelope(
        job_id=uuid4(),
        trace_id="trace",
        job_type="training",
        payload={**_payload_with_lineage(), "model_name": "missing_adapter"},
        queued_at=datetime.now(UTC),
    )
    client = _RedisStub()

    asyncio.run(process_job(client, envelope))  # type: ignore[arg-type]

    assert emitted[-1] == JobStatus.SUCCESS
    assert emitted.count(JobStatus.RUNNING) >= 4


def test_handle_with_timeout_marks_failed_when_attempts_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[str] = []
    emitted_metric_bundles: list[dict | None] = []

    async def _persist_event(_client, _envelope, status, _progress, _message, _result_ref, metric_bundle=None):
        emitted.append(status)
        emitted_metric_bundles.append(metric_bundle)

    monkeypatch.setattr("worker_training.main.persist_event", _persist_event)

    envelope = JobEnvelope(job_id=uuid4(), trace_id="trace", job_type="training", payload={}, queued_at=datetime.now(UTC))
    client = _RedisStub(attempts=999)

    asyncio.run(handle_with_timeout(client, envelope))  # type: ignore[arg-type]

    assert emitted == [JobStatus.FAILED]


def test_strict_mode_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GB_TRAINING_PIPELINE_STRICT_MODE", raising=False)
    monkeypatch.delenv("GB_TRAINING_PIPELINE_STRICT_MODEL_FAMILIES", raising=False)

    assert _strict_pipeline_enabled_for_family("arima") is False


def test_strict_mode_can_be_targeted_to_model_families(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GB_TRAINING_PIPELINE_STRICT_MODE", "true")
    monkeypatch.setenv("GB_TRAINING_PIPELINE_STRICT_MODEL_FAMILIES", "arima,torch_nn_timeseries")

    assert _strict_pipeline_enabled_for_family("arima") is True
    assert _strict_pipeline_enabled_for_family("hmm_regime_switching") is False
