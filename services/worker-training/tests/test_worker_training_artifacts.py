from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from worker_training.main import JobEnvelope, TrainingRunRequest, write_mock_artifacts


def test_training_artifact_written(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("worker_training.main.ARTIFACT_ROOT", tmp_path)
    envelope = JobEnvelope(
        job_id=uuid4(),
        trace_id="trace-1",
        job_type="training",
        payload={},
        queued_at=datetime.now(UTC),
    )
    request = TrainingRunRequest.model_validate({})

    artifact = write_mock_artifacts(envelope, request)

    assert artifact.metadata_path.exists()
    assert (artifact.metadata_path.parent / "model.bin").exists()
    assert artifact.ref.startswith("file://")
