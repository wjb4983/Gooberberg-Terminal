import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from worker_training.main import ADAPTERS, JobEnvelope, TrainingRunRequest, write_mock_artifacts


def test_training_artifact_written(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("worker_training.main.ARTIFACT_ROOT", tmp_path)
    envelope = JobEnvelope(
        job_id=uuid4(),
        trace_id="trace-1",
        job_type="training",
        payload={},
        queued_at=datetime.now(UTC),
    )
    request = TrainingRunRequest.model_validate({"model_name": "arima", "model_family": "statistical"})

    artifact = write_mock_artifacts(envelope, request)

    assert artifact.metadata_path.exists()
    assert (artifact.metadata_path.parent / "model.bin").exists()
    assert artifact.diagnostics_path.exists()
    assert artifact.ref.startswith("file://")
    metadata = json.loads(artifact.metadata_path.read_text(encoding="utf-8"))
    assert "split_manifest" in metadata
    assert set(metadata["split_manifest"]["counts"]) == {"train", "val", "test"}


@pytest.mark.parametrize("adapter_name", sorted(ADAPTERS))
def test_adapter_contract_artifacts(monkeypatch, tmp_path: Path, adapter_name: str) -> None:
    monkeypatch.setattr("worker_training.main.ARTIFACT_ROOT", tmp_path)
    envelope = JobEnvelope(
        job_id=uuid4(),
        trace_id="trace-adapter",
        job_type="training",
        payload={},
        queued_at=datetime.now(UTC),
    )
    family_by_adapter = {name: adapter.model_family for name, adapter in ADAPTERS.items()}
    request = TrainingRunRequest.model_validate(
        {"model_name": adapter_name, "model_family": family_by_adapter[adapter_name], "epochs": 3, "learning_rate": 0.01}
    )
    artifact = write_mock_artifacts(envelope, request)
    metadata = json.loads(artifact.metadata_path.read_text(encoding="utf-8"))
    diagnostics = json.loads(artifact.diagnostics_path.read_text(encoding="utf-8"))

    assert metadata["schema_version"] == "training-artifact/v1"
    assert metadata["target_schema"]["task"] == request.task
    assert metadata["prediction_output"]["schema_version"] == "prediction-output/v1"
    assert metadata["adapter"] == adapter_name
    assert isinstance(metadata["metrics_payload"], dict)
    assert "primary_metric" in metadata["metrics_payload"]
    assert isinstance(diagnostics, dict)


def test_deterministic_smoke_for_arima(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("worker_training.main.ARTIFACT_ROOT", tmp_path)
    envelope_a = JobEnvelope(job_id=uuid4(), trace_id="trace-a", job_type="training", payload={}, queued_at=datetime.now(UTC))
    envelope_b = JobEnvelope(job_id=uuid4(), trace_id="trace-b", job_type="training", payload={}, queued_at=datetime.now(UTC))
    request = TrainingRunRequest.model_validate(
        {"model_name": "arima", "model_family": "statistical", "epochs": 2, "learning_rate": 0.01, "seed": 99}
    )

    a = write_mock_artifacts(envelope_a, request)
    b = write_mock_artifacts(envelope_b, request)
    m_a = json.loads(a.metadata_path.read_text(encoding="utf-8"))
    m_b = json.loads(b.metadata_path.read_text(encoding="utf-8"))

    assert m_a["metrics_payload"] == m_b["metrics_payload"]
    assert m_a["model_checksum_sha256"] == m_b["model_checksum_sha256"]
