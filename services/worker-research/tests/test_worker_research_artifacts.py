from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from worker_research.main import BacktestRequest, JobEnvelope, write_mock_artifacts


def test_backtest_artifact_written(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("worker_research.main.ARTIFACT_ROOT", tmp_path)
    envelope = JobEnvelope(
        job_id=uuid4(),
        trace_id="trace-1",
        job_type="backtest",
        payload={},
        queued_at=datetime.now(UTC),
    )
    request = BacktestRequest.model_validate({})

    artifact = write_mock_artifacts(envelope, request)

    assert artifact.metadata_path.exists()
    assert artifact.ref.startswith("file://")
