from collections.abc import Mapping
from typing import Any

from app.domain.model_registry import ModelRegistry
from app.domain.model_configs.repository import ModelConfigRepository


class ModelConfigService:
    def __init__(self, repository: ModelConfigRepository, model_registry: ModelRegistry) -> None:
        self._repository = repository
        self._model_registry = model_registry

    def create(self, model_family: str, config: Mapping[str, Any]) -> dict[str, object]:
        spec = self._model_registry.require(model_family)
        validated_config = spec.validate_config(config)
        return self._repository.save(
            {
                "model_family": model_family,
                "config": dict(validated_config),
            }
        )

    def list_all(self) -> list[dict[str, object]]:
        return self._repository.list_all()
