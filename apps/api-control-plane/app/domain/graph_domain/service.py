from app.domain.graph_domain.repository import Repository


class Service:
    """Service layer for orchestrating domain operations."""

    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    def create(self, payload: dict[str, object]) -> dict[str, object]:
        return self._repository.add(payload)

    def list_all(self) -> list[dict[str, object]]:
        return self._repository.list_all()
