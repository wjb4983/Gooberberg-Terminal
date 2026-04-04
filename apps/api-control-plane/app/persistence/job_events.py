from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.jobs.models import JobLifecycleEvent
from app.persistence.repositories import JobEventSqlRepository


class JobEventRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def persist_event(self, event: JobLifecycleEvent) -> None:
        with self._session_factory() as session:
            JobEventSqlRepository(session).persist_event(event)

    def get_latest_event(self, job_id: UUID) -> JobLifecycleEvent | None:
        with self._session_factory() as session:
            return JobEventSqlRepository(session).get_latest_event(job_id)
