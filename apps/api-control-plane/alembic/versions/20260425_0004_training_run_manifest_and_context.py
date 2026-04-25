"""add training run manifest/context metadata columns

Revision ID: 20260425_0004
Revises: 20260423_0003
Create Date: 2026-04-25 00:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "20260425_0004"
down_revision = "20260423_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("training_runs", sa.Column("task_type", sa.String(length=64), nullable=False, server_default="time_series_momentum"))
    op.add_column("training_runs", sa.Column("subtask_type", sa.String(length=64), nullable=False, server_default="ranking"))
    op.add_column("training_runs", sa.Column("dataset_spec_hash", sa.String(length=128), nullable=False, server_default=""))
    op.add_column(
        "training_runs",
        sa.Column("dataset_manifest_version", sa.String(length=64), nullable=False, server_default="v1"),
    )
    op.add_column("training_runs", sa.Column("resolved_symbol_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("training_runs", sa.Column("resolved_member_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(
        "training_runs",
        sa.Column("model_config_version_tag", sa.String(length=64), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "training_runs",
        sa.Column("constraint_profile_version", sa.String(length=64), nullable=False, server_default="v1"),
    )

    op.alter_column("training_runs", "task_type", server_default=None)
    op.alter_column("training_runs", "subtask_type", server_default=None)
    op.alter_column("training_runs", "dataset_spec_hash", server_default=None)
    op.alter_column("training_runs", "dataset_manifest_version", server_default=None)
    op.alter_column("training_runs", "resolved_symbol_count", server_default=None)
    op.alter_column("training_runs", "resolved_member_count", server_default=None)
    op.alter_column("training_runs", "model_config_version_tag", server_default=None)
    op.alter_column("training_runs", "constraint_profile_version", server_default=None)


def downgrade() -> None:
    op.drop_column("training_runs", "constraint_profile_version")
    op.drop_column("training_runs", "model_config_version_tag")
    op.drop_column("training_runs", "resolved_member_count")
    op.drop_column("training_runs", "resolved_symbol_count")
    op.drop_column("training_runs", "dataset_manifest_version")
    op.drop_column("training_runs", "dataset_spec_hash")
    op.drop_column("training_runs", "subtask_type")
    op.drop_column("training_runs", "task_type")
