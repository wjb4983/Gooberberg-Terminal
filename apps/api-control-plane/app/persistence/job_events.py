from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.jobs.models import JobLifecycleEvent
from app.persistence.repositories import JobEventSqlRepository, RunArtifactSqlRepository


class JobEventRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def persist_event(self, event: JobLifecycleEvent) -> None:
        with self._session_factory() as session:
            JobEventSqlRepository(session).persist_event(event)

    def get_latest_event(self, job_id: UUID) -> JobLifecycleEvent | None:
        with self._session_factory() as session:
            return JobEventSqlRepository(session).get_latest_event(job_id)

    def list_events(self, job_id: UUID) -> list[JobLifecycleEvent]:
        with self._session_factory() as session:
            return JobEventSqlRepository(session).list_events(job_id)

    def persist_artifact_summary(
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
        with self._session_factory() as session:
            RunArtifactSqlRepository(session).add_summary(
                run_id=run_id,
                run_type=run_type,
                job_id=job_id,
                artifact_ref=artifact_ref,
                checksum=checksum,
                size_bytes=size_bytes,
                metrics=metrics,
                notes=notes,
                retention_class=retention_class,
            )

    def list_artifact_summaries(self, job_id: UUID) -> list[dict[str, object]]:
        with self._session_factory() as session:
            return RunArtifactSqlRepository(session).list_for_job(job_id)

    def get_artifact_detail(self, *, job_id: UUID, artifact_id: int) -> dict[str, object] | None:
        with self._session_factory() as session:
            return RunArtifactSqlRepository(session).get_for_job(job_id=job_id, artifact_id=artifact_id)

    def run_retention_jobs(self, *, intermediate_retention_days: int) -> int:
        with self._session_factory() as session:
            return RunArtifactSqlRepository(session).prune_old_intermediates(
                now_utc=datetime.now(UTC),
                retention_days=intermediate_retention_days,
            )
