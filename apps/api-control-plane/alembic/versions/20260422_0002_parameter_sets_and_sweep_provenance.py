"""add parameter sets and sweep provenance metadata

Revision ID: 20260422_0002
Revises: 20260404_0001
Create Date: 2026-04-22 00:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "20260422_0002"
down_revision = "20260404_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parameter_sets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("model_config_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("version_tag", sa.String(length=64), nullable=False),
        sa.Column("parent_set_id", sa.String(length=36), nullable=True),
        sa.Column("provenance_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["model_config_id"], ["model_configs.id"]),
        sa.ForeignKeyConstraint(["parent_set_id"], ["parameter_sets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column("parameter_sweep_runs", sa.Column("parameter_set_id", sa.String(length=36), nullable=True))
    op.add_column("parameter_sweep_runs", sa.Column("provenance_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.create_foreign_key(
        "fk_parameter_sweep_runs_parameter_set_id",
        "parameter_sweep_runs",
        "parameter_sets",
        ["parameter_set_id"],
        ["id"],
    )
    op.alter_column("parameter_sweep_runs", "provenance_snapshot", server_default=None)


def downgrade() -> None:
    op.drop_constraint("fk_parameter_sweep_runs_parameter_set_id", "parameter_sweep_runs", type_="foreignkey")
    op.drop_column("parameter_sweep_runs", "provenance_snapshot")
    op.drop_column("parameter_sweep_runs", "parameter_set_id")
    op.drop_table("parameter_sets")
