from uuid import UUID

from app.persistence.models import ParameterSweepRunRow
from app.persistence.repositories import RunSqlRepository


class Repository:
    def __init__(self, sql_repository: RunSqlRepository) -> None:
        self._repository = sql_repository

    def add(self, item: dict[str, object]) -> dict[str, object]:
        return self._repository.add(item)

    def list_all(self) -> list[dict[str, object]]:
        return self._repository.list_all()

    def get(self, item_id: UUID) -> dict[str, object] | None:
        return self._repository.get(item_id)

    @classmethod
    def from_session(cls, session: object) -> "Repository":
        return cls(RunSqlRepository(session, ParameterSweepRunRow))
