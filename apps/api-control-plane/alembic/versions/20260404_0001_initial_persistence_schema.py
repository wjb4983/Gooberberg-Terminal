"""initial persistence schema

Revision ID: 20260404_0001
Revises: 
Create Date: 2026-04-04 00:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "20260404_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_configs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("model_family", sa.String(length=128), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "training_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("model_config_id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["model_config_id"], ["model_configs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "parameter_sweep_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("model_config_id", sa.String(length=36), nullable=False),
        sa.Column("objective", sa.String(length=255), nullable=False),
        sa.Column("search_space", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["model_config_id"], ["model_configs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("strategy_key", sa.String(length=128), nullable=False),
        sa.Column("model_config_id", sa.String(length=36), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["model_config_id"], ["model_configs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "job_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=True),
        sa.Column("run_type", sa.String(length=32), nullable=True),
        sa.Column("trace_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("progress_pct", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("result_ref", sa.String(length=1024), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_events_job_id", "job_events", ["job_id"], unique=False)
    op.create_index("ix_job_events_run_id", "job_events", ["run_id"], unique=False)

    op.create_index("ix_training_runs_job_id", "training_runs", ["job_id"], unique=False)
    op.create_index("ix_parameter_sweep_runs_job_id", "parameter_sweep_runs", ["job_id"], unique=False)
    op.create_index("ix_backtest_runs_job_id", "backtest_runs", ["job_id"], unique=False)



    op.create_table(
        "run_artifacts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("run_type", sa.String(length=32), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("artifact_ref", sa.String(length=1024), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_run_artifacts_run_id", "run_artifacts", ["run_id"], unique=False)
    op.create_index("ix_run_artifacts_job_id", "run_artifacts", ["job_id"], unique=False)


    op.create_table(
        "graph_nodes",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("group", sa.String(length=255), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "graph_edges",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("target", sa.String(length=128), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["source"], ["graph_nodes.id"]),
        sa.ForeignKeyConstraint(["target"], ["graph_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "market_data_catalog",
        sa.Column("dataset_id", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("timeframe", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("dataset_id"),
    )

    op.create_table(
        "dataset_partitions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dataset_id", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("timeframe", sa.String(length=64), nullable=False),
        sa.Column("partition_start", sa.Date(), nullable=False),
        sa.Column("partition_end", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["market_data_catalog.dataset_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dataset_partitions_symbol", "dataset_partitions", ["symbol"], unique=False)
    op.create_index("ix_dataset_partitions_timeframe", "dataset_partitions", ["timeframe"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_dataset_partitions_timeframe", table_name="dataset_partitions")
    op.drop_index("ix_run_artifacts_job_id", table_name="run_artifacts")
    op.drop_index("ix_run_artifacts_run_id", table_name="run_artifacts")
    op.drop_table("run_artifacts")
    op.drop_index("ix_dataset_partitions_symbol", table_name="dataset_partitions")
    op.drop_table("dataset_partitions")
    op.drop_table("market_data_catalog")
    op.drop_table("graph_edges")
    op.drop_table("graph_nodes")
    op.drop_index("ix_training_runs_job_id", table_name="training_runs")
    op.drop_index("ix_parameter_sweep_runs_job_id", table_name="parameter_sweep_runs")
    op.drop_index("ix_backtest_runs_job_id", table_name="backtest_runs")
    op.drop_index("ix_job_events_run_id", table_name="job_events")
    op.drop_index("ix_job_events_job_id", table_name="job_events")
    op.drop_table("job_events")
    op.drop_table("backtest_runs")
    op.drop_table("parameter_sweep_runs")
    op.drop_table("training_runs")
    op.drop_table("model_configs")
