"""Ingest adapters that normalize provider feed payloads into event envelopes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

AlertSeverity = Literal["info", "warning", "critical"]


class MarketDataEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["MarketDataEvent"] = "MarketDataEvent"
    event_time: datetime
    symbol: str
    venue: str
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    last: float = Field(gt=0)
    volume: float = Field(ge=0)
    sequence: int = Field(ge=0)


class AlertEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["AlertEvent"] = "AlertEvent"
    event_time: datetime
    severity: AlertSeverity
    category: str
    message: str
    symbol: str
    venue: str


class IngestResult(BaseModel):
    market_data: list[MarketDataEvent] = Field(default_factory=list)
    alerts: list[AlertEvent] = Field(default_factory=list)


@dataclass
class _StreamState:
    last_sequence: int | None = None
    last_event_time: datetime | None = None
    seen_keys: set[tuple[int, datetime]] = field(default_factory=set)


class FeedIngestAdapter:
    """Normalizes raw feed payloads and emits anomaly alerts."""

    def __init__(
        self,
        *,
        stale_after: timedelta = timedelta(seconds=5),
        heartbeat_interval: timedelta = timedelta(seconds=30),
        max_clock_skew: timedelta = timedelta(seconds=2),
    ) -> None:
        self.stale_after = stale_after
        self.heartbeat_interval = heartbeat_interval
        self.max_clock_skew = max_clock_skew
        self._state_by_stream: dict[tuple[str, str], _StreamState] = {}
        self._last_heartbeat_at: datetime | None = None

    def ingest(self, payload: dict[str, object], *, received_at: datetime | None = None) -> IngestResult:
        now = (received_at or datetime.now(UTC)).astimezone(UTC)
        result = IngestResult()

        symbol = str(payload.get("symbol", "")).strip().upper()
        venue = str(payload.get("venue", "UNKNOWN")).strip().upper()
        stream_key = (symbol, venue)
        state = self._state_by_stream.setdefault(stream_key, _StreamState())

        event_time = self._as_utc(payload.get("event_time"), default=now)
        sequence = int(payload.get("sequence", 0))

        if state.last_sequence is not None and sequence <= state.last_sequence:
            severity: AlertSeverity = "critical" if sequence < state.last_sequence else "warning"
            result.alerts.append(
                self._alert(
                    event_time=now,
                    severity=severity,
                    category="sequence",
                    symbol=symbol,
                    venue=venue,
                    message=f"non-monotonic sequence observed: current={sequence} last={state.last_sequence}",
                )
            )

        dedupe_key = (sequence, event_time)
        if dedupe_key in state.seen_keys:
            result.alerts.append(
                self._alert(
                    event_time=now,
                    severity="warning",
                    category="duplicate",
                    symbol=symbol,
                    venue=venue,
                    message=f"duplicate tick dropped for sequence={sequence} event_time={event_time.isoformat()}",
                )
            )
            return self._maybe_heartbeat(result=result, now=now)

        if now - event_time > self.stale_after:
            result.alerts.append(
                self._alert(
                    event_time=now,
                    severity="warning",
                    category="stale_data",
                    symbol=symbol,
                    venue=venue,
                    message=f"stale tick: age={(now - event_time).total_seconds():.3f}s threshold={self.stale_after.total_seconds():.3f}s",
                )
            )

        clock_skew = abs((now - event_time).total_seconds())
        if clock_skew > self.max_clock_skew.total_seconds():
            severity = "critical" if clock_skew > self.max_clock_skew.total_seconds() * 3 else "warning"
            result.alerts.append(
                self._alert(
                    event_time=now,
                    severity=severity,
                    category="clock_skew",
                    symbol=symbol,
                    venue=venue,
                    message=f"clock skew detected: {clock_skew:.3f}s > {self.max_clock_skew.total_seconds():.3f}s",
                )
            )

        result.market_data.append(
            MarketDataEvent(
                event_time=event_time,
                symbol=symbol,
                venue=venue,
                bid=float(payload.get("bid", 0.0)),
                ask=float(payload.get("ask", 0.0)),
                last=float(payload.get("last", 0.0)),
                volume=float(payload.get("volume", 0.0)),
                sequence=sequence,
            )
        )

        state.last_sequence = max(sequence, state.last_sequence or 0)
        state.last_event_time = event_time
        state.seen_keys.add(dedupe_key)
        if len(state.seen_keys) > 1024:
            state.seen_keys = set(list(state.seen_keys)[-512:])

        return self._maybe_heartbeat(result=result, now=now)

    def _maybe_heartbeat(self, *, result: IngestResult, now: datetime) -> IngestResult:
        if self._last_heartbeat_at is None or now - self._last_heartbeat_at >= self.heartbeat_interval:
            result.alerts.append(
                AlertEvent(
                    event_time=now,
                    severity="info",
                    category="heartbeat",
                    message="ingest heartbeat",
                    symbol="*",
                    venue="*",
                )
            )
            self._last_heartbeat_at = now
        return result

    @staticmethod
    def _as_utc(value: object, *, default: datetime) -> datetime:
        if isinstance(value, datetime):
            return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        return default

    @staticmethod
    def _alert(*, event_time: datetime, severity: AlertSeverity, category: str, symbol: str, venue: str, message: str) -> AlertEvent:
        return AlertEvent(
            event_time=event_time,
            severity=severity,
            category=category,
            symbol=symbol,
            venue=venue,
            message=message,
        )
