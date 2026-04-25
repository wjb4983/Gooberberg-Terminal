from __future__ import annotations

from datetime import UTC, date, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.domain.market_data.spec import dataset_id_from_spec
from app.jobs.models import JobLifecycleEvent, JobStatus
from app.persistence.models import (
    BacktestRunRow,
    DatasetPartitionRow,
    GraphEdgeRow,
    GraphNodeRow,
    JobEventRow,
    MarketDataCatalogRow,
    ModelConfigRow,
    ParameterSweepRunRow,
    RunArtifactRow,
    TestingRunRow,
    TrainingRunRow,
    utc_now,
)
from app.schemas import (
    GraphEdge,
    GraphNode,
    GraphTopologyResponse,
    MarketDataCacheCoverageResponse,
    MarketDataDatasetLookupResponse,
    MarketDataIngestionRequest,
    MarketDataIngestionResponse,
)


class ModelConfigSqlRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, item: dict[str, object]) -> dict[str, object]:
        timestamp = utc_now()
        row = ModelConfigRow(
            id=str(item.get("id") or uuid4()),
            model_family=str(item["model_family"]),
            config=dict(item.get("config", {})),
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_dict(row)

    def list_all(self) -> list[dict[str, object]]:
        rows = self._session.execute(select(ModelConfigRow).order_by(ModelConfigRow.created_at.desc())).scalars().all()
        return [self._to_dict(row) for row in rows]

    def get(self, item_id: UUID) -> dict[str, object] | None:
        row = self._session.get(ModelConfigRow, str(item_id))
        return self._to_dict(row) if row else None

    def update(self, item_id: UUID, item: dict[str, object]) -> dict[str, object] | None:
        row = self._session.get(ModelConfigRow, str(item_id))
        if row is None:
            return None
        row.config = dict(item.get("config", {}))
        row.updated_at = utc_now()
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_dict(row)

    @staticmethod
    def _to_dict(row: ModelConfigRow) -> dict[str, object]:
        return {
            "id": row.id,
            "model_family": row.model_family,
            "config": dict(row.config or {}),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }


class RunSqlRepository:
    def __init__(
        self,
        session: Session,
        model: type[TrainingRunRow] | type[ParameterSweepRunRow] | type[BacktestRunRow] | type[TestingRunRow],
    ) -> None:
        self._session = session
        self._model = model

    def add(self, item: dict[str, object]) -> dict[str, object]:
        row = self._model(**item)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_dict(row)

    def list_all(self) -> list[dict[str, object]]:
        rows = self._session.execute(select(self._model).order_by(self._model.created_at.desc())).scalars().all()
        return [self._to_dict(row) for row in rows]

    def get(self, item_id: UUID) -> dict[str, object] | None:
        row = self._session.get(self._model, str(item_id))
        return self._to_dict(row) if row else None

    def update_status(self, item_id: UUID, status: str) -> None:
        row = self._session.get(self._model, str(item_id))
        if row is None:
            return
        row.status = status
        self._session.add(row)
        self._session.commit()

    @staticmethod
    def _to_dict(row: TrainingRunRow | ParameterSweepRunRow | BacktestRunRow | TestingRunRow) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": row.id,
            "job_id": row.job_id,
            "status": row.status,
            "created_at": row.created_at,
        }
        if isinstance(row, TrainingRunRow):
            payload.update(
                {
                    "model_config_id": row.model_config_id,
                    "dataset_id": row.dataset_id,
                    "dataset_spec_hash": row.dataset_spec_hash,
                    "dataset_manifest_version": row.dataset_manifest_version,
                    "resolved_symbol_count": row.resolved_symbol_count,
                    "resolved_member_count": row.resolved_member_count,
                    "model_config_version_tag": row.model_config_version_tag,
                    "task_type": row.task_type,
                    "subtask_type": row.subtask_type,
                    "constraint_profile_version": row.constraint_profile_version,
                    "parameters": dict(row.parameters or {}),
                }
            )
        elif isinstance(row, ParameterSweepRunRow):
            payload.update(
                {
                    "model_config_id": row.model_config_id,
                    "parameter_set_id": row.parameter_set_id,
                    "task_type": row.task_type,
                    "subtask_type": row.subtask_type,
                    "objective": row.objective,
                    "search_space": dict(row.search_space or {}),
                    "provenance_snapshot": dict(row.provenance_snapshot or {}),
                }
            )
        elif isinstance(row, BacktestRunRow):
            payload.update(
                {
                    "strategy_key": row.strategy_key,
                    "model_config_id": row.model_config_id,
                    "window_start": row.window_start,
                    "window_end": row.window_end,
                    "parameters": dict(row.parameters or {}),
                }
            )
        else:
            payload.update(
                {
                    "mode": row.mode,
                    "target_refs": list(row.target_refs or []),
                    "parameters": dict(row.parameters or {}),
                    "result_summary": dict(row.result_summary) if row.result_summary is not None else None,
                }
            )
        return payload


class JobEventSqlRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def persist_event(self, event: JobLifecycleEvent) -> None:
        row = JobEventRow(
            job_id=str(event.job_id),
            run_id=str(event.run_id) if event.run_id else None,
            run_type=event.run_type,
            trace_id=event.trace_id,
            status=event.status.value,
            progress_pct=int(event.progress_pct),
            message=event.message,
            detail=event.detail,
            result_ref=event.result_ref,
            updated_at=event.updated_at.astimezone(UTC),
        )
        self._session.add(row)
        self._session.commit()

    def get_latest_event(self, job_id: UUID) -> JobLifecycleEvent | None:
        row = (
            self._session.execute(
                select(JobEventRow)
                .where(JobEventRow.job_id == str(job_id))
                .order_by(JobEventRow.updated_at.desc(), JobEventRow.id.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        return self._to_event(row)

    def list_events(self, job_id: UUID) -> list[JobLifecycleEvent]:
        rows = (
            self._session.execute(
                select(JobEventRow)
                .where(JobEventRow.job_id == str(job_id))
                .order_by(JobEventRow.updated_at.asc(), JobEventRow.id.asc())
            )
            .scalars()
            .all()
        )
        return [event for event in (self._to_event(row) for row in rows) if event]

    @staticmethod
    def _to_event(row: JobEventRow | None) -> JobLifecycleEvent | None:
        if row is None:
            return None
        return JobLifecycleEvent(
            job_id=UUID(row.job_id),
            run_id=UUID(row.run_id) if row.run_id else None,
            run_type=row.run_type,
            trace_id=row.trace_id,
            status=JobStatus(row.status),
            progress_pct=float(row.progress_pct),
            message=row.message,
            detail=row.detail,
            result_ref=row.result_ref,
            updated_at=row.updated_at,
        )


class RunArtifactSqlRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_summary(
        self,
        *,
        run_id: UUID,
        run_type: str,
        job_id: UUID,
        artifact_ref: str,
        checksum: str | None,
        size_bytes: int | None,
        metrics: dict[str, object],
        notes: str | None,
        retention_class: str,
    ) -> None:
        timestamp = utc_now()
        resolved_checksum = (checksum or "").strip() or sha256(artifact_ref.encode("utf-8")).hexdigest()
        existing_for_run = (
            self._session.execute(
                select(RunArtifactRow).where(
                    RunArtifactRow.run_id == str(run_id),
                    RunArtifactRow.run_type == run_type,
                    RunArtifactRow.checksum == resolved_checksum,
                )
            )
            .scalars()
            .first()
        )
        if existing_for_run is not None:
            existing_for_run.last_accessed_at = timestamp
            existing_for_run.metrics = metrics
            existing_for_run.notes = notes
            existing_for_run.size_bytes = size_bytes or existing_for_run.size_bytes
            existing_for_run.retention_class = retention_class
            self._session.add(existing_for_run)
            self._session.commit()
            return

        dedup_source = (
            self._session.execute(select(RunArtifactRow).where(RunArtifactRow.checksum == resolved_checksum).limit(1))
            .scalars()
            .first()
        )
        row = RunArtifactRow(
            run_id=str(run_id),
            run_type=run_type,
            job_id=str(job_id),
            artifact_ref=dedup_source.artifact_ref if dedup_source else artifact_ref,
            checksum=resolved_checksum,
            size_bytes=size_bytes or 0,
            metrics=metrics,
            notes=notes,
            last_accessed_at=timestamp,
            retention_class=retention_class,
            created_at=timestamp,
        )
        self._session.add(row)
        self._session.commit()

    def list_for_job(self, job_id: UUID) -> list[dict[str, object]]:
        rows = (
            self._session.execute(
                select(RunArtifactRow)
                .where(RunArtifactRow.job_id == str(job_id))
                .order_by(RunArtifactRow.created_at.desc(), RunArtifactRow.id.desc())
            )
            .scalars()
            .all()
        )
        return [self._to_summary(row) for row in rows]

    def get_for_job(self, *, job_id: UUID, artifact_id: int) -> dict[str, object] | None:
        row = (
            self._session.execute(
                select(RunArtifactRow).where(RunArtifactRow.job_id == str(job_id), RunArtifactRow.id == artifact_id)
            )
            .scalars()
            .first()
        )
        if row is None:
            return None
        row.last_accessed_at = utc_now()
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        payload = self._to_summary(row)
        payload["metrics"] = dict(row.metrics or {})
        payload["notes"] = row.notes
        return payload

    def prune_old_intermediates(self, *, now_utc, retention_days: int) -> int:
        cutoff = now_utc - timedelta(days=max(retention_days, 1))
        result = self._session.execute(
            delete(RunArtifactRow).where(
                RunArtifactRow.retention_class == "intermediate",
                RunArtifactRow.last_accessed_at < cutoff,
            )
        )
        self._session.commit()
        return int(result.rowcount or 0)

    @staticmethod
    def _best_metric(metrics: dict[str, object]) -> float | None:
        explicit_best = metrics.get("best_metric")
        if isinstance(explicit_best, (float, int)):
            return float(explicit_best)
        for key in ("score", "accuracy", "f1", "auc"):
            value = metrics.get(key)
            if isinstance(value, (float, int)):
                return float(value)
        return None

    def _to_summary(self, row: RunArtifactRow) -> dict[str, object]:
        return {
            "id": row.id,
            "run_id": row.run_id,
            "run_type": row.run_type,
            "job_id": row.job_id,
            "artifact_ref": row.artifact_ref,
            "checksum": row.checksum,
            "size_bytes": row.size_bytes,
            "best_metric": self._best_metric(dict(row.metrics or {})),
            "created_at": row.created_at,
            "last_accessed_at": row.last_accessed_at,
            "retention_class": row.retention_class,
        }


class GraphSqlRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def ensure_seeded(self, topology: GraphTopologyResponse) -> None:
        node_count = self._session.scalar(select(func.count()).select_from(GraphNodeRow)) or 0
        if node_count > 0:
            return
        for node in topology.nodes:
            self._session.add(
                GraphNodeRow(
                    id=node.id,
                    type=node.type.value,
                    label=node.label,
                    group=node.group,
                    metadata_json=dict(node.metadata),
                )
            )
        for edge in topology.edges:
            self._session.add(GraphEdgeRow(id=edge.id, source=edge.source, target=edge.target, label=edge.label))
        self._session.commit()

    def get_topology(self) -> GraphTopologyResponse:
        nodes = self._session.execute(select(GraphNodeRow)).scalars().all()
        edges = self._session.execute(select(GraphEdgeRow)).scalars().all()
        return GraphTopologyResponse(
            nodes=[
                GraphNode(
                    id=node.id,
                    type=node.type,
                    label=node.label,
                    group=node.group,
                    metadata=dict(node.metadata_json or {}),
                )
                for node in nodes
            ],
            edges=[GraphEdge(id=edge.id, source=edge.source, target=edge.target, label=edge.label) for edge in edges],
        )


class MarketDataSqlRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def request_ingestion(self, payload: MarketDataIngestionRequest) -> MarketDataIngestionResponse:
        dataset_id, serialized_spec = dataset_id_from_spec(payload)
        source = payload.source or payload.provider
        symbols = payload.universe_members or payload.symbols or ["UNKNOWN"]
        timeframe = (payload.resolutions[0] if payload.resolutions else payload.timeframe) or "1d"

        existing = self._session.get(MarketDataCatalogRow, dataset_id)
        if existing is not None:
            return MarketDataIngestionResponse(
                request_id=dataset_id,
                dataset_id=dataset_id,
                status="already_exists",
                source=existing.source,
                symbols=list((existing.metadata_json or {}).get("symbols", symbols)),
                timeframe=existing.timeframe,
            )

        self._session.add(
            MarketDataCatalogRow(
                dataset_id=dataset_id,
                source=source,
                symbol=symbols[0],
                timeframe=timeframe,
                metadata_json={
                    "dataset_spec": serialized_spec,
                    "provider": payload.provider,
                    "asset_class": payload.asset_class,
                    "symbols": symbols,
                    "resolutions": payload.resolutions,
                    "status": "accepted",
                    "start_date": payload.start_date.isoformat(),
                    "end_date": payload.end_date.isoformat(),
                    "feature_recipe_version": payload.feature_recipe_version,
                    "label_recipe_version": payload.label_recipe_version,
                },
            )
        )
        for symbol in symbols:
            self._session.add(
                DatasetPartitionRow(
                    dataset_id=dataset_id,
                    symbol=symbol,
                    timeframe=timeframe,
                    partition_start=payload.start_date,
                    partition_end=payload.end_date,
                )
            )
        self._session.commit()
        return MarketDataIngestionResponse(
            request_id=dataset_id,
            dataset_id=dataset_id,
            status="accepted",
            source=source,
            symbols=symbols,
            timeframe=timeframe,
        )

    def get_cache_coverage(self, symbol: str, timeframe: str) -> MarketDataCacheCoverageResponse:
        result = self._session.execute(
            select(
                func.min(DatasetPartitionRow.partition_start),
                func.max(DatasetPartitionRow.partition_end),
                func.count(DatasetPartitionRow.id),
            ).where(DatasetPartitionRow.symbol == symbol, DatasetPartitionRow.timeframe == timeframe)
        ).first()
        if result is None or result[0] is None or result[1] is None:
            return MarketDataCacheCoverageResponse(symbol=symbol, timeframe=timeframe, available_start=None, available_end=None, coverage_pct=0.0)
        available_start, available_end, partition_count = result
        coverage_pct = 100.0 if partition_count and partition_count > 0 else 0.0
        return MarketDataCacheCoverageResponse(
            symbol=symbol,
            timeframe=timeframe,
            available_start=available_start,
            available_end=available_end,
            coverage_pct=coverage_pct,
        )

    def lookup_dataset(self, dataset_id: str) -> MarketDataDatasetLookupResponse | None:
        row = self._session.get(MarketDataCatalogRow, dataset_id)
        if row is None:
            return None
        return MarketDataDatasetLookupResponse(
            dataset_id=row.dataset_id,
            source=row.source,
            symbol=row.symbol,
            timeframe=row.timeframe,
            metadata=dict(row.metadata_json or {}),
        )
