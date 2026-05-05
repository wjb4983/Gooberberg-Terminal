from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.domain.training_runs.repository import Repository
    from app.domain.training_runs.service import Service

__all__ = ["Repository", "Service", "TrainingRunService"]


def __getattr__(name: str) -> Any:
    # Import lazily so schema modules can reference validation helpers
    # without pulling the repository package back through app.schemas.
    if name == "Repository":
        from app.domain.training_runs.repository import Repository

        return Repository
    if name == "Service":
        from app.domain.training_runs.service import Service

        return Service
    if name == "TrainingRunService":
        from app.domain.training_runs.service import Service as TrainingRunService

        return TrainingRunService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
