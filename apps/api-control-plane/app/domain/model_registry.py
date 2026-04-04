from collections.abc import Mapping
from typing import Any, Protocol


class ModelSpec(Protocol):
    """Domain model-family contract for config validation."""

    model_family: str

    def validate_config(self, config: Mapping[str, Any]) -> Mapping[str, Any]:
        """Validate and normalize model configuration payload."""


class ModelRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, ModelSpec] = {}

    def register(self, spec: ModelSpec) -> None:
        self._specs[spec.model_family] = spec

    def get(self, model_family: str) -> ModelSpec | None:
        return self._specs.get(model_family)

    def require(self, model_family: str) -> ModelSpec:
        spec = self.get(model_family)
        if spec is None:
            raise KeyError(f"model family is not registered: {model_family}")
        return spec

    def list_families(self) -> tuple[str, ...]:
        return tuple(sorted(self._specs))
