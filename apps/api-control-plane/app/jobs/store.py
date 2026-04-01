from collections.abc import Mapping
from threading import Lock
from uuid import UUID

from app.jobs.models import JobLifecycleEvent


class InMemoryJobStateStore:
    """Process-local fallback store for latest known job status."""

    def __init__(self) -> None:
        self._events: dict[UUID, JobLifecycleEvent] = {}
        self._lock = Lock()

    def upsert(self, event: JobLifecycleEvent) -> JobLifecycleEvent:
        with self._lock:
            self._events[event.job_id] = event
        return event

    def get(self, job_id: UUID) -> JobLifecycleEvent | None:
        with self._lock:
            return self._events.get(job_id)

    def snapshot(self) -> Mapping[UUID, JobLifecycleEvent]:
        with self._lock:
            return dict(self._events)


job_state_store = InMemoryJobStateStore()
