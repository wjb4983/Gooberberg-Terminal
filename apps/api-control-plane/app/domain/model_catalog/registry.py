from collections.abc import Iterable

from app.domain.model_catalog.models import ModelCatalogEntry


class ModelCatalogRegistry:
    def __init__(self, entries: Iterable[ModelCatalogEntry]) -> None:
        self._entries = {entry.metadata.model_family: entry for entry in entries}

    def get(self, model_family: str) -> ModelCatalogEntry | None:
        return self._entries.get(model_family)

    def require(self, model_family: str) -> ModelCatalogEntry:
        entry = self.get(model_family)
        if entry is None:
            raise KeyError(f"model family is not in catalog: {model_family}")
        return entry

    def list_entries(self) -> tuple[ModelCatalogEntry, ...]:
        return tuple(self._entries[key] for key in sorted(self._entries))

    def list_families(self) -> tuple[str, ...]:
        return tuple(sorted(self._entries))
