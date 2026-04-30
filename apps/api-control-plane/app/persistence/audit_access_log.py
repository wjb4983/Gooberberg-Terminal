from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock


@dataclass(frozen=True)
class AuditAccessLogRecord:
    queried_at: datetime
    token_id: str
    scope: str
    endpoint: str
    filters: str


class ImmutableAuditAccessLog:
    """Append-only access ledger for sensitive audit query endpoints."""

    def __init__(self) -> None:
        self._records: tuple[AuditAccessLogRecord, ...] = ()
        self._lock = Lock()

    def append(self, *, token_id: str, scope: str, endpoint: str, filters: str) -> AuditAccessLogRecord:
        record = AuditAccessLogRecord(
            queried_at=datetime.now(UTC),
            token_id=token_id,
            scope=scope,
            endpoint=endpoint,
            filters=filters,
        )
        with self._lock:
            self._records = (*self._records, record)
        return record

    def snapshot(self) -> tuple[AuditAccessLogRecord, ...]:
        with self._lock:
            return self._records


audit_access_log = ImmutableAuditAccessLog()
