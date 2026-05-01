from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import create_app
from app.persistence.models import ModelConfigRow, TrainingRunRow


def test_list_training_runs_normalizes_legacy_status_and_task_fields() -> None:
    with TestClient(create_app()) as client:
        with client.app.state.database.session_factory() as session:
            session.add(
                ModelConfigRow(
                    id="11111111-1111-1111-1111-111111111111",
                    model_family="arima",
                    config={"p": 1, "d": 1, "q": 1},
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )
            session.add(
                TrainingRunRow(
                    id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    job_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                    model_config_id="11111111-1111-1111-1111-111111111111",
                    dataset_id="legacy_dataset",
                    status="accepted",
                    parameters={},
                    created_at=datetime.now(UTC),
                    task_type="unsupported_old_value",
                    subtask_type="unsupported_old_value",
                    dataset_spec_hash="",
                    dataset_manifest_version="v1",
                    resolved_symbol_count=0,
                    resolved_member_count=0,
                    model_config_version_tag="unknown",
                    constraint_profile_version="v1",
                )
            )
            session.commit()

        response = client.get("/api/v1/training-runs")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["status"] == "queued"
        assert payload[0]["task_type"] == "time_series_momentum"
        assert payload[0]["subtask_type"] == "ranking"


def test_list_training_runs_skips_rows_that_remain_invalid_after_normalization() -> None:
    with TestClient(create_app()) as client:
        with client.app.state.database.session_factory() as session:
            session.add(
                ModelConfigRow(
                    id="22222222-2222-2222-2222-222222222222",
                    model_family="arima",
                    config={"p": 1, "d": 1, "q": 1},
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )
            session.add(
                TrainingRunRow(
                    id="cccccccc-cccc-cccc-cccc-cccccccccccc",
                    job_id="dddddddd-dddd-dddd-dddd-dddddddddddd",
                    model_config_id="22222222-2222-2222-2222-222222222222",
                    dataset_id="valid_dataset",
                    status="queued",
                    parameters={},
                    created_at=datetime.now(UTC),
                    task_type="time_series_momentum",
                    subtask_type="ranking",
                    dataset_spec_hash="",
                    dataset_manifest_version="v1",
                    resolved_symbol_count=0,
                    resolved_member_count=0,
                    model_config_version_tag="unknown",
                    constraint_profile_version="v1",
                )
            )
            session.add(
                TrainingRunRow(
                    id="eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
                    job_id="ffffffff-ffff-ffff-ffff-ffffffffffff",
                    model_config_id="not-a-uuid",
                    dataset_id="invalid_dataset",
                    status="queued",
                    parameters={},
                    created_at=datetime.now(UTC),
                    task_type="time_series_momentum",
                    subtask_type="ranking",
                    dataset_spec_hash="",
                    dataset_manifest_version="v1",
                    resolved_symbol_count=0,
                    resolved_member_count=0,
                    model_config_version_tag="unknown",
                    constraint_profile_version="v1",
                )
            )
            session.commit()

        response = client.get("/api/v1/training-runs")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["id"] == "cccccccc-cccc-cccc-cccc-cccccccccccc"


def test_list_training_runs_handles_non_object_parameters_payload() -> None:
    with TestClient(create_app()) as client:
        with client.app.state.database.session_factory() as session:
            session.add(
                ModelConfigRow(
                    id="33333333-3333-3333-3333-333333333333",
                    model_family="arima",
                    config={"p": 1, "d": 1, "q": 1},
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )
            session.commit()
            session.execute(
                text(
                    """
                    INSERT INTO training_runs (
                        id, job_id, model_config_id, dataset_id, status, parameters, created_at,
                        task_type, subtask_type, dataset_spec_hash, dataset_manifest_version,
                        resolved_symbol_count, resolved_member_count, model_config_version_tag, constraint_profile_version
                    )
                    VALUES (
                        :id, :job_id, :model_config_id, :dataset_id, :status, :parameters, :created_at,
                        :task_type, :subtask_type, :dataset_spec_hash, :dataset_manifest_version,
                        :resolved_symbol_count, :resolved_member_count, :model_config_version_tag, :constraint_profile_version
                    )
                    """
                ),
                {
                    "id": "abababab-abab-abab-abab-abababababab",
                    "job_id": "cdcdcdcd-cdcd-cdcd-cdcd-cdcdcdcdcdcd",
                    "model_config_id": "33333333-3333-3333-3333-333333333333",
                    "dataset_id": "legacy_dataset",
                    "status": "queued",
                    "parameters": "[]",
                    "created_at": datetime.now(UTC),
                    "task_type": "time_series_momentum",
                    "subtask_type": "ranking",
                    "dataset_spec_hash": "",
                    "dataset_manifest_version": "v1",
                    "resolved_symbol_count": 0,
                    "resolved_member_count": 0,
                    "model_config_version_tag": "unknown",
                    "constraint_profile_version": "v1",
                },
            )
            session.commit()

        response = client.get("/api/v1/training-runs")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["id"] == "abababab-abab-abab-abab-abababababab"
        assert payload[0]["parameters"] == {}
