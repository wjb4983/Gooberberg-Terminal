from collections.abc import Callable
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
        metrics: dict[str, object],
        notes: str | None,
    ) -> None:
        with self._session_factory() as session:
            RunArtifactSqlRepository(session).add_summary(
                run_id=run_id,
                run_type=run_type,
                job_id=job_id,
                artifact_ref=artifact_ref,
                metrics=metrics,
                notes=notes,
            )
