"""Postgres-backed catalog of cache coverage, gaps, and dataset references."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from service_data.market_data.models import CoverageRecord, DatasetRef, MissingRange, Resolution, TimeRange


class CursorLike(Protocol):
    def execute(self, query: str, params: tuple[object, ...] | None = None) -> object: ...

    def fetchall(self) -> list[tuple[object, ...]]: ...


class ConnectionLike(Protocol):
    def cursor(self) -> CursorLike: ...

    def commit(self) -> None: ...


class CatalogRepository:
    """Persist and query metadata for cached market data."""

    def __init__(self, *, conn: ConnectionLike) -> None:
        self.conn = conn

    def upsert_dataset_ref(self, ref: DatasetRef) -> None:
        with self.conn.cursor() as cur:  # type: ignore[attr-defined]
            cur.execute(
                """
                INSERT INTO market_data.dataset_refs
                    (ref_id, symbol, day, resolution, uri, schema_hash, refreshed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ref_id)
                DO UPDATE SET
                    uri = EXCLUDED.uri,
                    schema_hash = EXCLUDED.schema_hash,
                    refreshed_at = EXCLUDED.refreshed_at
                """,
                (
                    ref.ref_id,
                    ref.symbol,
                    ref.day,
                    ref.resolution,
                    ref.uri,
                    ref.schema_hash,
                    ref.refreshed_at,
                ),
            )
        self.conn.commit()

    def upsert_coverage(self, coverage: CoverageRecord) -> None:
        with self.conn.cursor() as cur:  # type: ignore[attr-defined]
            cur.execute(
                """
                INSERT INTO market_data.coverage
                    (symbol, resolution, range_start, range_end, refreshed_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (symbol, resolution)
                DO UPDATE SET
                    range_start = LEAST(market_data.coverage.range_start, EXCLUDED.range_start),
                    range_end = GREATEST(market_data.coverage.range_end, EXCLUDED.range_end),
                    refreshed_at = EXCLUDED.refreshed_at
                """,
                (
                    coverage.symbol,
                    coverage.resolution,
                    coverage.start,
                    coverage.end,
                    coverage.refreshed_at,
                ),
            )
        self.conn.commit()

    def record_missing(self, missing: MissingRange) -> None:
        with self.conn.cursor() as cur:  # type: ignore[attr-defined]
            cur.execute(
                """
                INSERT INTO market_data.missing_ranges
                    (symbol, resolution, range_start, range_end, reason, detected_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    missing.symbol,
                    missing.resolution,
                    missing.start,
                    missing.end,
                    missing.reason,
                    missing.detected_at,
                ),
            )
        self.conn.commit()

    def query_coverage(
        self,
        *,
        symbol: str,
        resolution: Resolution,
        requested: TimeRange,
    ) -> tuple[list[CoverageRecord], list[MissingRange], list[DatasetRef]]:
        with self.conn.cursor() as cur:  # type: ignore[attr-defined]
            cur.execute(
                """
                SELECT symbol, resolution, range_start, range_end, refreshed_at
                FROM market_data.coverage
                WHERE symbol = %s
                  AND resolution = %s
                  AND range_end > %s
                  AND range_start < %s
                """,
                (symbol, resolution, requested.start, requested.end),
            )
            coverage_rows = cur.fetchall()

            cur.execute(
                """
                SELECT symbol, resolution, range_start, range_end, reason, detected_at
                FROM market_data.missing_ranges
                WHERE symbol = %s
                  AND resolution = %s
                  AND range_end > %s
                  AND range_start < %s
                ORDER BY detected_at DESC
                """,
                (symbol, resolution, requested.start, requested.end),
            )
            missing_rows = cur.fetchall()

            cur.execute(
                """
                SELECT ref_id, symbol, day, resolution, uri, schema_hash, refreshed_at
                FROM market_data.dataset_refs
                WHERE symbol = %s
                  AND resolution = %s
                  AND day BETWEEN %s::date AND %s::date
                ORDER BY day ASC
                """,
                (symbol, resolution, requested.start.date(), requested.end.date()),
            )
            ref_rows = cur.fetchall()

        coverage = [
            CoverageRecord(
                symbol=str(row[0]),
                resolution=str(row[1]),
                start=_as_utc(row[2]),
                end=_as_utc(row[3]),
                refreshed_at=_as_utc(row[4]),
            )
            for row in coverage_rows
        ]
        missing = [
            MissingRange(
                symbol=str(row[0]),
                resolution=str(row[1]),
                start=_as_utc(row[2]),
                end=_as_utc(row[3]),
                reason=str(row[4]),
                detected_at=_as_utc(row[5]),
            )
            for row in missing_rows
        ]
        refs = [
            DatasetRef(
                ref_id=UUID(str(row[0])),
                symbol=str(row[1]),
                day=row[2],
                resolution=str(row[3]),
                uri=str(row[4]),
                schema_hash=str(row[5]),
                refreshed_at=_as_utc(row[6]),
            )
            for row in ref_rows
        ]
        return coverage, missing, refs


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
