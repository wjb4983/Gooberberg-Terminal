from uuid import UUID

from app.domain.testing_runs.repository import Repository


class Service:
    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    def create(self, payload: dict[str, object]) -> dict[str, object]:
        return self._repository.add(payload)

    def list_all(self) -> list[dict[str, object]]:
        return self._repository.list_all()

    def get(self, item_id: UUID) -> dict[str, object] | None:
        return self._repository.get(item_id)
