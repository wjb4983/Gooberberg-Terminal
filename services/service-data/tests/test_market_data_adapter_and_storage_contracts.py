from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

pytest.importorskip("polars")

from service_data.market_data.cache_repository import CacheRepository
from service_data.market_data.catalog_repository import CatalogRepository
from service_data.market_data.models import CanonicalBar, CoverageRecord, DatasetRef, MissingRange, TimeRange
from service_data.market_data.providers.massive_adapter import MassiveAdapter
from service_data.market_data.query_service import CoverageQuery, MarketDataQueryService


class _FakeCursor:
    def __init__(self, rows_by_call: list[list[tuple[object, ...]]] | None = None) -> None:
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []
        self._rows_by_call = rows_by_call or []
        self._idx = 0

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> None:
        self.executed.append((query, params))

    def fetchall(self) -> list[tuple[object, ...]]:
        if self._idx >= len(self._rows_by_call):
            return []
        rows = self._rows_by_call[self._idx]
        self._idx += 1
        return rows


class _FakeConn:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor
        self.commit_calls = 0

    def cursor(self) -> _FakeCursor:
        return self._cursor

    def commit(self) -> None:
        self.commit_calls += 1


def test_massive_adapter_normalizes_bar_contract() -> None:
    adapter = MassiveAdapter(api_key="secret")

    bars = adapter._normalize(
        {
            "results": [
                {"t": 1711843200000, "o": 10, "h": 12, "l": 9, "c": 11, "v": 1000, "vw": 10.8, "n": 42}
            ]
        },
        symbol="aapl",
        resolution="day",
    )

    assert len(bars) == 1
    assert bars[0].symbol == "AAPL"
    assert bars[0].resolution == "day"
    assert bars[0].trades == 42
    assert bars[0].source == "massive"


def test_catalog_upsert_commits_and_coverage_query_maps_rows() -> None:
    refreshed_at = datetime(2026, 4, 1, tzinfo=UTC)
    cursor = _FakeCursor(
        rows_by_call=[
            [("AAPL", "minute", datetime(2026, 3, 1, tzinfo=UTC), datetime(2026, 3, 31, tzinfo=UTC), refreshed_at)],
            [
                (
                    "AAPL",
                    "minute",
                    datetime(2026, 3, 15, tzinfo=UTC),
                    datetime(2026, 3, 16, tzinfo=UTC),
                    "upstream gap",
                    refreshed_at,
                )
            ],
            [(str(uuid4()), "AAPL", datetime(2026, 3, 20, tzinfo=UTC).date(), "minute", "file:///tmp/p", "sha256:x", refreshed_at)],
        ]
    )
    conn = _FakeConn(cursor)
    repo = CatalogRepository(conn=conn)

    repo.upsert_coverage(
        CoverageRecord(
            symbol="AAPL",
            resolution="minute",
            start=datetime(2026, 3, 1, tzinfo=UTC),
            end=datetime(2026, 3, 31, tzinfo=UTC),
            refreshed_at=refreshed_at,
        )
    )
    assert conn.commit_calls == 1

    coverage, missing, refs = repo.query_coverage(
        symbol="AAPL",
        resolution="minute",
        requested=TimeRange(start=datetime(2026, 3, 1, tzinfo=UTC), end=datetime(2026, 4, 1, tzinfo=UTC)),
    )
    assert coverage[0].symbol == "AAPL"
    assert missing[0].reason == "upstream gap"
    assert refs[0].uri.startswith("file://")


def test_cache_repository_dedupes_partition_refs_for_same_symbol_day_resolution(tmp_path) -> None:
    repo = CacheRepository(base_path=tmp_path)
    ts = datetime(2026, 4, 1, 9, 30, tzinfo=UTC)
    bars = [
        CanonicalBar(symbol="AAPL", ts=ts, open=1, high=2, low=1, close=2, volume=10, source="massive", resolution="minute"),
        CanonicalBar(symbol="aapl", ts=ts.replace(minute=31), open=2, high=3, low=1, close=2.5, volume=20, source="massive", resolution="minute"),
    ]

    refs = repo.write_bars(bars)

    assert len(refs) == 1
    assert "symbol=AAPL" in refs[0].uri
    assert (tmp_path / "manifest.json").exists()


def test_cache_repository_load_bars_uses_partition_predicates(tmp_path) -> None:
    repo = CacheRepository(base_path=tmp_path)
    bars = [
        CanonicalBar(
            symbol="AAPL",
            ts=datetime(2026, 4, 1, 13, 30, tzinfo=UTC),
            open=100,
            high=101,
            low=99,
            close=100.5,
            volume=1_000,
            source="massive",
            resolution="minute",
        ),
        CanonicalBar(
            symbol="MSFT",
            ts=datetime(2026, 4, 1, 13, 30, tzinfo=UTC),
            open=200,
            high=202,
            low=199,
            close=201,
            volume=2_000,
            source="massive",
            resolution="minute",
        ),
    ]
    repo.write_bars(bars)

    loaded = repo.load_bars(
        symbol="aapl",
        resolution="minute",
        start=datetime(2026, 4, 1, 0, 0, tzinfo=UTC),
        end=datetime(2026, 4, 2, 0, 0, tzinfo=UTC),
    )

    assert loaded.height == 1
    assert loaded["symbol"].to_list() == ["AAPL"]


def test_query_service_normalizes_symbol_and_returns_coverage_contract() -> None:
    class _CatalogStub:
        def query_coverage(self, *, symbol: str, resolution: str, requested: TimeRange):
            assert symbol == "MSFT"
            assert resolution == "hour"
            assert requested.start < requested.end
            return (
                [
                    CoverageRecord(
                        symbol=symbol,
                        resolution=resolution,
                        start=requested.start,
                        end=requested.end,
                        refreshed_at=datetime.now(UTC),
                    )
                ],
                [
                    MissingRange(
                        symbol=symbol,
                        resolution=resolution,
                        start=requested.start,
                        end=requested.end,
                        reason="none",
                        detected_at=datetime.now(UTC),
                    )
                ],
                [
                    DatasetRef(
                        ref_id=uuid4(),
                        symbol=symbol,
                        day=requested.start.date(),
                        resolution=resolution,
                        uri="file:///tmp/data",
                        schema_hash="sha256:test",
                        refreshed_at=datetime.now(UTC),
                    )
                ],
            )

    service = MarketDataQueryService(catalog=_CatalogStub())
    response = service.get_coverage(
        CoverageQuery(symbol="msft", resolution="hour", start=datetime(2026, 4, 1, tzinfo=UTC), end=datetime(2026, 4, 2, tzinfo=UTC))
    )
    assert response.symbol == "MSFT"
    assert response.coverage[0].resolution == "hour"
    assert len(response.refs) == 1
