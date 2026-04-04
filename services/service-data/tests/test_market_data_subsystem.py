from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

pytest.importorskip("polars")

from service_data.market_data.cache_repository import CacheRepository
from service_data.market_data.models import CanonicalBar
from service_data.market_data.providers.base import ProviderError
from service_data.market_data.providers.massive_adapter import MassiveAdapter


def test_massive_adapter_reads_api_key_from_env(monkeypatch) -> None:
    monkeypatch.setenv("MASSIVE_API_KEY", "secret")

    adapter = MassiveAdapter(api_key_path=Path("/tmp/definitely-missing-api-key"))

    assert adapter.api_key == "secret"


def test_massive_adapter_raises_if_missing_api_key(monkeypatch) -> None:
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)

    try:
        MassiveAdapter(api_key_path=Path("/tmp/definitely-missing-api-key"))
    except ProviderError as exc:
        assert exc.code == "auth"
    else:
        raise AssertionError("Expected ProviderError for missing API key")


def test_cache_repository_writes_partitioned_parquet(tmp_path: Path) -> None:
    repo = CacheRepository(base_path=tmp_path)
    bars = [
        CanonicalBar(
            symbol="aapl",
            ts=datetime(2026, 3, 31, 13, 30, tzinfo=UTC),
            open=100,
            high=101,
            low=99,
            close=100.5,
            volume=1000,
            vwap=100.2,
            trades=25,
            source="massive",
            resolution="minute",
        )
    ]

    refs = repo.write_bars(bars)

    assert len(refs) == 1
    assert "symbol=AAPL" in refs[0].uri
    assert (tmp_path / "symbol=AAPL" / "date=2026-03-31" / "resolution=minute").exists()
