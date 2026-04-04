from app.domain.job_runner.repository import JobRunnerRepository
from app.domain.task_registry import TaskRegistry
from app.jobs.models import JobEnvelope


class JobRunnerService:
    def __init__(self, repository: JobRunnerRepository, task_registry: TaskRegistry) -> None:
        self._repository = repository
        self._task_registry = task_registry

    def submit(self, envelope: JobEnvelope) -> None:
        self._task_registry.require_runner(envelope.job_type)
        self._repository.record_submission(
            {
                "job_id": str(envelope.job_id),
                "trace_id": envelope.trace_id,
                "job_type": envelope.job_type,
            }
        )
