"""Strict adapter interface and capability declarations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from worker_training.main import AdapterOutput, TrainingRunRequest


@dataclass(frozen=True, slots=True)
class AdapterCapability:
    """Declares what an adapter can handle."""

    task: str
    subtask: str
    data_type: str


class StrictTrainingAdapter(Protocol):
    """Strict contract all training adapters must implement."""

    name: str
    model_family: str
    capabilities: tuple[AdapterCapability, ...]

    def run(self, request: TrainingRunRequest) -> AdapterOutput:
        """Run model training and return persisted artifact payload."""


class CapabilityValidationError(RuntimeError):
    """Raised when a request cannot be served by an adapter capability."""

    def __init__(self, model_family: str, task: str, subtask: str, data_type: str) -> None:
        super().__init__(
            "unsupported capability for model family "
            f"'{model_family}': task='{task}', subtask='{subtask}', data_type='{data_type}'"
        )
        self.model_family = model_family
        self.task = task
        self.subtask = subtask
        self.data_type = data_type
