from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


class ModelConfigRow(Base):
    __tablename__ = "model_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    model_family: Mapped[str] = mapped_column(String(128), nullable=False)
    config: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class TrainingRunRow(Base):
    __tablename__ = "training_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    model_config_id: Mapped[str] = mapped_column(String(36), ForeignKey("model_configs.id"), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(255), nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subtask_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    parameters: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class ParameterSweepRunRow(Base):
    __tablename__ = "parameter_sweep_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    model_config_id: Mapped[str] = mapped_column(String(36), ForeignKey("model_configs.id"), nullable=False)
    parameter_set_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("parameter_sets.id"), nullable=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subtask_type: Mapped[str] = mapped_column(String(64), nullable=False)
    objective: Mapped[str] = mapped_column(String(255), nullable=False)
    search_space: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    provenance_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class ParameterSetRow(Base):
    __tablename__ = "parameter_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    model_config_id: Mapped[str] = mapped_column(String(36), ForeignKey("model_configs.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parameters: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    version_tag: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_set_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("parameter_sets.id"), nullable=True)
    provenance_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class BacktestRunRow(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    strategy_key: Mapped[str] = mapped_column(String(128), nullable=False)
    model_config_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("model_configs.id"), nullable=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    parameters: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class TestingRunRow(Base):
    __tablename__ = "testing_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    target_refs: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    parameters: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    result_summary: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class JobEventRow(Base):
    __tablename__ = "job_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    run_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    trace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    result_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RunArtifactRow(Base):
    __tablename__ = "run_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    run_type: Mapped[str] = mapped_column(String(32), nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    artifact_ref: Mapped[str] = mapped_column(String(1024), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metrics: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    retention_class: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class GraphNodeRow(Base):
    __tablename__ = "graph_nodes"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    group: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column("metadata", JSON, nullable=False, default=dict)


class GraphEdgeRow(Base):
    __tablename__ = "graph_edges"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source: Mapped[str] = mapped_column(String(128), ForeignKey("graph_nodes.id"), nullable=False)
    target: Mapped[str] = mapped_column(String(128), ForeignKey("graph_nodes.id"), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)


class MarketDataCatalogRow(Base):
    __tablename__ = "market_data_catalog"

    dataset_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column("metadata", JSON, nullable=False, default=dict)


class DatasetPartitionRow(Base):
    __tablename__ = "dataset_partitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(String(128), ForeignKey("market_data_catalog.dataset_id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    partition_start: Mapped[date] = mapped_column(Date, nullable=False)
    partition_end: Mapped[date] = mapped_column(Date, nullable=False)
