from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
from typing import Any


@dataclass(frozen=True)
class EventRecord:
    offset: int
    event_type: str
    symbol: str | None
    event_time: datetime
    trace_id: str | None
    decision_id: str | None
    order_id: str | None
    payload: dict[str, Any]


@dataclass(frozen=True)
class SegmentIntegrity:
    segment_id: int
    event_count: int
    checksum: str


@dataclass(frozen=True)
class EventQuery:
    event_type: str | None = None
    symbol: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    trace_id: str | None = None
    decision_id: str | None = None
    order_id: str | None = None


@dataclass(frozen=True)
class EventLogPolicy:
    retention_period: timedelta = timedelta(days=7)
    archive_after: timedelta = timedelta(days=3)


class EventLogWriter:
    """In-memory event log with idempotent appends and monotonic offsets."""

    def __init__(self, *, policy: EventLogPolicy | None = None, segment_size: int = 1000) -> None:
        self._policy = policy or EventLogPolicy()
        self._segment_size = max(segment_size, 1)
        self._next_offset = 0
        self._records: list[EventRecord] = []
        self._idempotency_offsets: dict[str, int] = {}
        self._archived: list[EventRecord] = []

    def append(self, *, idempotency_key: str, payload: dict[str, Any]) -> EventRecord:
        existing_offset = self._idempotency_offsets.get(idempotency_key)
        if existing_offset is not None:
            return self._records[existing_offset]

        event_time = _coerce_utc_datetime(payload.get("event_time"))
        record = EventRecord(
            offset=self._next_offset,
            event_type=str(payload.get("event_type") or "UnknownEvent"),
            symbol=_to_optional_str(payload.get("symbol")),
            event_time=event_time,
            trace_id=_to_optional_str(payload.get("trace_id")),
            decision_id=_to_optional_str(payload.get("decision_id")),
            order_id=_to_optional_str(payload.get("order_id")),
            payload=payload,
        )
        self._records.append(record)
        self._idempotency_offsets[idempotency_key] = record.offset
        self._next_offset += 1
        return record

    def query(self, filters: EventQuery | None = None) -> list[EventRecord]:
        q = filters or EventQuery()
        result = self._records
        if q.event_type is not None:
            result = [r for r in result if r.event_type == q.event_type]
        if q.symbol is not None:
            result = [r for r in result if r.symbol == q.symbol]
        if q.start_time is not None:
            start = _coerce_utc_datetime(q.start_time)
            result = [r for r in result if r.event_time >= start]
        if q.end_time is not None:
            end = _coerce_utc_datetime(q.end_time)
            result = [r for r in result if r.event_time <= end]
        if q.trace_id is not None:
            result = [r for r in result if r.trace_id == q.trace_id]
        if q.decision_id is not None:
            result = [r for r in result if r.decision_id == q.decision_id]
        if q.order_id is not None:
            result = [r for r in result if r.order_id == q.order_id]
        return list(result)

    def apply_retention_and_archive(self, *, now: datetime | None = None) -> tuple[int, int]:
        now_utc = _coerce_utc_datetime(now) if now is not None else datetime.now(UTC)
        archive_cutoff = now_utc - self._policy.archive_after
        retention_cutoff = now_utc - self._policy.retention_period

        to_archive = [r for r in self._records if r.event_time <= archive_cutoff]
        for r in to_archive:
            if r not in self._archived:
                self._archived.append(r)

        before = len(self._records)
        self._records = [r for r in self._records if r.event_time >= retention_cutoff]
        purged = before - len(self._records)
        return (len(to_archive), purged)

    def integrity_segments(self) -> list[SegmentIntegrity]:
        segments: list[SegmentIntegrity] = []
        for segment_id, start in enumerate(range(0, len(self._records), self._segment_size)):
            part = self._records[start : start + self._segment_size]
            payload = [
                {
                    "offset": r.offset,
                    "event_type": r.event_type,
                    "symbol": r.symbol,
                    "event_time": r.event_time.isoformat(),
                    "trace_id": r.trace_id,
                    "decision_id": r.decision_id,
                    "order_id": r.order_id,
                }
                for r in part
            ]
            digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
            segments.append(SegmentIntegrity(segment_id=segment_id, event_count=len(part), checksum=digest))
        return segments

    @property
    def archived_records(self) -> list[EventRecord]:
        return list(self._archived)


def _coerce_utc_datetime(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _to_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    value_str = str(value)
    return value_str if value_str else None
