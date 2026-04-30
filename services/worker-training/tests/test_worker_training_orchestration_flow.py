from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import asyncio

import pytest

from worker_training.main import JobEnvelope, JobStatus, handle_with_timeout, process_job
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
        payload={"model_name": "arima"},
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
        payload={"model_name": "missing_adapter"},
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
