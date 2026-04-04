class Repository:
    """Repository boundary for the domain package."""

    def __init__(self) -> None:
        self._items: list[dict[str, object]] = []

    def add(self, item: dict[str, object]) -> dict[str, object]:
        self._items.append(dict(item))
        return dict(item)

    def list_all(self) -> list[dict[str, object]]:
        return [dict(item) for item in self._items]
