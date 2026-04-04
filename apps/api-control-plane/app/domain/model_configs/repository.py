from collections.abc import Mapping
from copy import deepcopy
from threading import Lock
from uuid import UUID, uuid4


class ModelConfigRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, dict[str, object]] = {}
        self._lock = Lock()

    def save(self, item: Mapping[str, object]) -> dict[str, object]:
        with self._lock:
            row = deepcopy(dict(item))
            row.setdefault("id", str(uuid4()))
            self._items[UUID(str(row["id"]))] = row
            return deepcopy(row)

    def list_all(self) -> list[dict[str, object]]:
        with self._lock:
            return [deepcopy(item) for item in self._items.values()]
