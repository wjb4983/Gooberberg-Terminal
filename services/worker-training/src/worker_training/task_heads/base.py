"""Task-head abstractions for target construction and prediction formatting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class TaskHead(Protocol):
    """Objective-specific behavior used by generic model adapters."""

    task: str
    subtask: str

    def build_target_schema(self) -> dict[str, Any]:
        """Describe expected training target schema for this objective."""

    def format_prediction(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Normalize model output into a standard prediction shape."""


@dataclass(frozen=True, slots=True)
class StandardTaskHead:
    task: str
    subtask: str
    target_kind: str
    prediction_kind: str
    horizon_key: str = "horizon"

    def build_target_schema(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "subtask": self.subtask,
            "target_kind": self.target_kind,
            "required_fields": ["entity_id", "timestamp", "target"],
            "target_dtype": "float",
            "horizon_key": self.horizon_key,
        }

    def format_prediction(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": "prediction-output/v1",
            "task": self.task,
            "subtask": self.subtask,
            "prediction_kind": self.prediction_kind,
            "primary_metric": payload.get("primary_metric"),
            "values": payload,
        }
