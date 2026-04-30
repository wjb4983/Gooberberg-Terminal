from __future__ import annotations

from sqlalchemy import create_engine, inspect

from app.persistence.models import Base


RUN_TABLES = ("training_runs", "parameter_sweep_runs", "backtest_runs", "testing_runs")


def test_run_tables_include_durable_lineage_columns() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)

    required_columns = {
        "lineage_version",
        "dataset_fingerprint",
        "code_hash",
        "config_digest",
        "seed",
        "lineage_status",
        "lineage_error_code",
    }

    for table_name in RUN_TABLES:
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        assert required_columns.issubset(columns)


def test_run_artifacts_include_lineage_artifact_fields() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)

    columns = {column["name"] for column in inspector.get_columns("run_artifacts")}
    assert {"artifact_role", "artifact_uri", "sha256", "content_type"}.issubset(columns)
