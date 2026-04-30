from __future__ import annotations

from sqlalchemy import create_engine, inspect

from app.persistence.models import Base


def test_lineage_and_governance_tables_exist() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    assert "scenario_registry" in table_names
    assert "artifact_blobs" in table_names
    assert "lineage_entities" in table_names
    assert "lineage_edges" in table_names
    assert "audit_reports" in table_names


def test_run_artifacts_has_signature_and_promotion_status_columns() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    run_artifact_columns = {column["name"] for column in inspector.get_columns("run_artifacts")}

    assert "signature" in run_artifact_columns
    assert "promotion_status" in run_artifact_columns
