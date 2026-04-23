"""add artifact manifest metadata and retention indexes

Revision ID: 20260423_0003
Revises: 20260422_0002
Create Date: 2026-04-23 00:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "20260423_0003"
down_revision = "20260422_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("run_artifacts", sa.Column("checksum", sa.String(length=128), nullable=True))
    op.add_column("run_artifacts", sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(
        "run_artifacts",
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.add_column(
        "run_artifacts",
        sa.Column("retention_class", sa.String(length=32), nullable=False, server_default="standard"),
    )

    op.execute("UPDATE run_artifacts SET checksum = artifact_ref WHERE checksum IS NULL")
    op.alter_column("run_artifacts", "checksum", nullable=False)
    op.alter_column("run_artifacts", "size_bytes", server_default=None)
    op.alter_column("run_artifacts", "last_accessed_at", server_default=None)
    op.alter_column("run_artifacts", "retention_class", server_default=None)

    op.create_index("ix_run_artifacts_checksum", "run_artifacts", ["checksum"], unique=False)
    op.create_index("ix_run_artifacts_retention_class", "run_artifacts", ["retention_class"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_run_artifacts_retention_class", table_name="run_artifacts")
    op.drop_index("ix_run_artifacts_checksum", table_name="run_artifacts")
    op.drop_column("run_artifacts", "retention_class")
    op.drop_column("run_artifacts", "last_accessed_at")
    op.drop_column("run_artifacts", "size_bytes")
    op.drop_column("run_artifacts", "checksum")
