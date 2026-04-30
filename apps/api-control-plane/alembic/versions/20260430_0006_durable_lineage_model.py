"""add durable lineage columns, artifact integrity constraints, and compatibility view

Revision ID: 20260430_0006
Revises: 20260430_0005
Create Date: 2026-04-30 00:30:00

"""

from alembic import op
import sqlalchemy as sa


revision = "20260430_0006"
down_revision = "20260430_0005"
branch_labels = None
depends_on = None


RUN_TABLES = ("training_runs", "parameter_sweep_runs", "backtest_runs", "testing_runs")


def _add_lineage_columns(table_name: str) -> None:
    op.add_column(table_name, sa.Column("lineage_version", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(table_name, sa.Column("dataset_fingerprint", sa.String(length=128), nullable=True))
    op.add_column(table_name, sa.Column("code_hash", sa.String(length=64), nullable=True))
    op.add_column(table_name, sa.Column("config_digest", sa.String(length=128), nullable=True))
    op.add_column(table_name, sa.Column("seed", sa.Integer(), nullable=True))
    op.add_column(table_name, sa.Column("lineage_status", sa.String(length=32), nullable=True))
    op.add_column(table_name, sa.Column("lineage_error_code", sa.String(length=64), nullable=True))

    op.create_check_constraint(
        f"ck_{table_name}_lineage_hashes",
        table_name,
        "(dataset_fingerprint IS NULL OR length(dataset_fingerprint) = 64) "
        "AND (code_hash IS NULL OR length(code_hash) = 40 OR length(code_hash) = 64) "
        "AND (config_digest IS NULL OR length(config_digest) = 64)",
    )
    op.create_check_constraint(
        f"ck_{table_name}_lineage_status_terminal_success",
        table_name,
        "status <> 'succeeded' OR "
        "(dataset_fingerprint IS NOT NULL AND code_hash IS NOT NULL AND config_digest IS NOT NULL "
        "AND seed IS NOT NULL AND lineage_status IS NOT NULL)",
    )

    op.create_index(f"ix_{table_name}_dataset_fingerprint", table_name, ["dataset_fingerprint"], unique=False)
    op.create_index(f"ix_{table_name}_code_hash", table_name, ["code_hash"], unique=False)
    op.create_index(f"ix_{table_name}_config_digest", table_name, ["config_digest"], unique=False)
    op.alter_column(table_name, "lineage_version", server_default=None)


def upgrade() -> None:
    for table_name in RUN_TABLES:
        _add_lineage_columns(table_name)

    op.add_column("run_artifacts", sa.Column("artifact_role", sa.String(length=64), nullable=True))
    op.add_column("run_artifacts", sa.Column("artifact_uri", sa.String(length=1024), nullable=True))
    op.add_column("run_artifacts", sa.Column("sha256", sa.String(length=64), nullable=True))
    op.add_column("run_artifacts", sa.Column("content_type", sa.String(length=255), nullable=True))

    op.execute("UPDATE run_artifacts SET artifact_role = 'unspecified' WHERE artifact_role IS NULL")
    op.execute("UPDATE run_artifacts SET artifact_uri = artifact_ref WHERE artifact_uri IS NULL")
    op.execute("UPDATE run_artifacts SET sha256 = substr(checksum, 1, 64) WHERE sha256 IS NULL")
    op.execute("UPDATE run_artifacts SET content_type = 'application/octet-stream' WHERE content_type IS NULL")

    op.alter_column("run_artifacts", "artifact_role", nullable=False)
    op.alter_column("run_artifacts", "artifact_uri", nullable=False)
    op.alter_column("run_artifacts", "sha256", nullable=False)
    op.alter_column("run_artifacts", "content_type", nullable=False)

    op.create_unique_constraint("uq_run_artifacts_run_id_artifact_role", "run_artifacts", ["run_id", "artifact_role"])
    op.create_check_constraint(
        "ck_run_artifacts_sha256_length",
        "run_artifacts",
        "length(sha256) = 64",
    )

    op.execute(
        "CREATE VIEW run_artifacts_legacy_v AS "
        "SELECT id, run_id, run_type, job_id, artifact_ref, checksum, signature, size_bytes, metrics, notes, "
        "last_accessed_at, retention_class, promotion_status, created_at FROM run_artifacts"
    )


def downgrade() -> None:
    op.execute("DROP VIEW run_artifacts_legacy_v")
    op.drop_constraint("ck_run_artifacts_sha256_length", "run_artifacts", type_="check")
    op.drop_constraint("uq_run_artifacts_run_id_artifact_role", "run_artifacts", type_="unique")
    op.drop_column("run_artifacts", "content_type")
    op.drop_column("run_artifacts", "sha256")
    op.drop_column("run_artifacts", "artifact_uri")
    op.drop_column("run_artifacts", "artifact_role")

    for table_name in reversed(RUN_TABLES):
        op.drop_index(f"ix_{table_name}_config_digest", table_name=table_name)
        op.drop_index(f"ix_{table_name}_code_hash", table_name=table_name)
        op.drop_index(f"ix_{table_name}_dataset_fingerprint", table_name=table_name)
        op.drop_constraint(f"ck_{table_name}_lineage_status_terminal_success", table_name, type_="check")
        op.drop_constraint(f"ck_{table_name}_lineage_hashes", table_name, type_="check")
        op.drop_column(table_name, "lineage_error_code")
        op.drop_column(table_name, "lineage_status")
        op.drop_column(table_name, "seed")
        op.drop_column(table_name, "config_digest")
        op.drop_column(table_name, "code_hash")
        op.drop_column(table_name, "dataset_fingerprint")
        op.drop_column(table_name, "lineage_version")
