"""Runtime adapter registry keyed by model family."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from worker_training.adapters.base import CapabilityValidationError, StrictTrainingAdapter

if TYPE_CHECKING:
    from worker_training.main import TrainingRunRequest


@dataclass(frozen=True, slots=True)
class AdapterRegistry:
    adapters_by_family: dict[str, StrictTrainingAdapter]

    def resolve(self, request: TrainingRunRequest) -> StrictTrainingAdapter:
        from worker_training.main import AdapterExecutionError

        adapter = self.adapters_by_family.get(request.model_family)
        if adapter is None:
            raise AdapterExecutionError(
                code="adapter_not_found",
                message=f"no adapter registered for model family '{request.model_family}'",
                diagnostics={"model_family": request.model_family, "available_model_families": sorted(self.adapters_by_family)},
            )

        for capability in adapter.capabilities:
            if (
                capability.task == request.task
                and capability.subtask == request.subtask
                and capability.data_type == request.data_type
            ):
                return adapter

        err = CapabilityValidationError(request.model_family, request.task, request.subtask, request.data_type)
        raise AdapterExecutionError(
            code="unsupported_capability",
            message=str(err),
            diagnostics={
                "model_family": request.model_family,
                "requested": {"task": request.task, "subtask": request.subtask, "data_type": request.data_type},
                "supported": [
                    {"task": c.task, "subtask": c.subtask, "data_type": c.data_type} for c in adapter.capabilities
                ],
            },
        )
