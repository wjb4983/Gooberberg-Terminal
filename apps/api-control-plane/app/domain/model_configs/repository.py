from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.orm import Session

from app.persistence.repositories import ModelConfigSqlRepository


class ModelConfigRepository:
    def __init__(self, session: Session) -> None:
        self._repository = ModelConfigSqlRepository(session)

    def save(self, item: Mapping[str, object]) -> dict[str, object]:
        return self._repository.save(dict(item))

    def list_all(self) -> list[dict[str, object]]:
        return self._repository.list_all()

    def get(self, item_id: UUID) -> dict[str, object] | None:
        return self._repository.get(item_id)

    def update(self, item_id: UUID, item: Mapping[str, object]) -> dict[str, object] | None:
        return self._repository.update(item_id, dict(item))
