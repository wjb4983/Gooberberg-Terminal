from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Protocol

TaskRunner = Callable[[Mapping[str, Any]], Awaitable[Mapping[str, Any] | None]]


class TaskSpec(Protocol):
    """Task contract for API task execution."""

    task_type: str

    async def run(self, payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
        """Execute task and return optional structured output."""


class TaskRegistry:
    def __init__(self) -> None:
        self._runners: dict[str, TaskRunner] = {}

    def register_runner(self, task_type: str, runner: TaskRunner) -> None:
        self._runners[task_type] = runner

    def register_spec(self, spec: TaskSpec) -> None:
        self.register_runner(spec.task_type, spec.run)

    def get_runner(self, task_type: str) -> TaskRunner | None:
        return self._runners.get(task_type)

    def require_runner(self, task_type: str) -> TaskRunner:
        runner = self.get_runner(task_type)
        if runner is None:
            raise KeyError(f"task type is not registered: {task_type}")
        return runner

    def list_task_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._runners))
