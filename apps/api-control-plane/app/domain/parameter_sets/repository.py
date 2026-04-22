from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.persistence.models import ParameterSetRow


class Repository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, item: dict[str, object]) -> dict[str, object]:
        row = ParameterSetRow(**item)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_dict(row)

    def list_all(self) -> list[dict[str, object]]:
        rows = self._session.execute(select(ParameterSetRow).order_by(ParameterSetRow.created_at.desc())).scalars().all()
        return [self._to_dict(row) for row in rows]

    def get(self, item_id: UUID) -> dict[str, object] | None:
        row = self._session.get(ParameterSetRow, str(item_id))
        return self._to_dict(row) if row else None

    def list_lineage(self, item_id: UUID) -> list[dict[str, object]]:
        lineage: list[dict[str, object]] = []
        cursor = str(item_id)
        while cursor:
            row = self._session.get(ParameterSetRow, cursor)
            if row is None:
                break
            lineage.append(self._to_dict(row))
            cursor = row.parent_set_id or ""
        lineage.reverse()
        return lineage

    @staticmethod
    def _to_dict(row: ParameterSetRow) -> dict[str, object]:
        return {
            "id": row.id,
            "model_config_id": row.model_config_id,
            "name": row.name,
            "parameters": dict(row.parameters or {}),
            "version_tag": row.version_tag,
            "parent_set_id": row.parent_set_id,
            "provenance_metadata": dict(row.provenance_metadata or {}),
            "created_at": row.created_at,
        }
