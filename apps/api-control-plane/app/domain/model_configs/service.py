from collections.abc import Mapping
from typing import Any
from uuid import UUID
from enum import Enum

from app.domain.model_registry import ModelRegistry
from app.domain.model_configs.repository import ModelConfigRepository


class ModelConfigService:
    def __init__(self, repository: ModelConfigRepository, model_registry: ModelRegistry) -> None:
        self._repository = repository
        self._model_registry = model_registry

    def create(self, model_family: str, config: Mapping[str, Any]) -> dict[str, object]:
        normalized_family = self._normalize_model_family(model_family)
        spec = self._model_registry.require(normalized_family)
        validated_config = spec.validate_config(config)
        return self._repository.save(
            {
                "model_family": normalized_family,
                "config": dict(validated_config),
            }
        )

    def list_all(self) -> list[dict[str, object]]:
        return self._repository.list_all()

    def get(self, model_config_id: UUID) -> dict[str, object] | None:
        return self._repository.get(model_config_id)

    def update(self, model_config_id: UUID, config: Mapping[str, Any]) -> dict[str, object] | None:
        existing = self._repository.get(model_config_id)
        if existing is None:
            return None

        model_family = self._normalize_model_family(existing["model_family"])
        spec = self._model_registry.require(model_family)
        validated_config = spec.validate_config(config)
        return self._repository.update(model_config_id, {"config": dict(validated_config)})

    @staticmethod
    def _normalize_model_family(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, Enum):
            raw_value = value.value
            if isinstance(raw_value, str):
                return raw_value
        return str(value)
