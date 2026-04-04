from collections.abc import Mapping
from copy import deepcopy
from datetime import UTC, datetime
from threading import Lock
from uuid import UUID, uuid4


class ModelConfigRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, dict[str, object]] = {}
        self._lock = Lock()

    def save(self, item: Mapping[str, object]) -> dict[str, object]:
        with self._lock:
            timestamp = datetime.now(UTC)
            row = deepcopy(dict(item))
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", timestamp)
            row["updated_at"] = timestamp
            self._items[UUID(str(row["id"]))] = row
            return deepcopy(row)

    def list_all(self) -> list[dict[str, object]]:
        with self._lock:
            return [deepcopy(item) for item in self._items.values()]

    def get(self, item_id: UUID) -> dict[str, object] | None:
        with self._lock:
            item = self._items.get(item_id)
            return deepcopy(item) if item is not None else None

    def update(self, item_id: UUID, item: Mapping[str, object]) -> dict[str, object] | None:
        with self._lock:
            existing = self._items.get(item_id)
            if existing is None:
                return None
            updated = deepcopy(existing)
            updated.update(deepcopy(dict(item)))
            updated["id"] = str(item_id)
            updated["updated_at"] = datetime.now(UTC)
            self._items[item_id] = updated
            return deepcopy(updated)
