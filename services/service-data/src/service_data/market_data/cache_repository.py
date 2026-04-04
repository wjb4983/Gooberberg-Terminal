"""Parquet-backed cache repository for canonical market bars."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path
from typing import Iterable
from uuid import UUID, uuid4

import polars as pl

from service_data.market_data.models import CanonicalBar, DatasetRef


class CacheRepository:
    """Persist canonical bars in parquet partitions by symbol/day/resolution."""

    def __init__(self, *, base_path: Path) -> None:
        self.base_path = base_path.resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def write_bars(self, bars: Iterable[CanonicalBar]) -> list[DatasetRef]:
        items = list(bars)
        if not items:
            return []

        payload = [
            {
                "symbol": bar.symbol,
                "ts": bar.ts.astimezone(UTC),
                "date": bar.ts.astimezone(UTC).date().isoformat(),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
                "vwap": bar.vwap,
                "trades": bar.trades,
                "source": bar.source,
                "resolution": bar.resolution,
            }
            for bar in items
        ]
        frame = pl.DataFrame(payload)

        frame.write_parquet(
            self.base_path / "bars.parquet",
            use_pyarrow=True,
            pyarrow_options={
                "compression": "zstd",
                "partition_cols": ["symbol", "date", "resolution"],
            },
        )

        refreshed_at = max(bar.ts for bar in items)
        refs: dict[tuple[str, str, str], DatasetRef] = {}
        for bar in items:
            day = bar.ts.astimezone(UTC).date()
            key = (bar.symbol, day.isoformat(), bar.resolution)
            if key in refs:
                continue
            ref_id = uuid4()
            uri = self._partition_uri(symbol=bar.symbol, day=day.isoformat(), resolution=bar.resolution)
            refs[key] = DatasetRef(
                ref_id=ref_id,
                symbol=bar.symbol,
                day=day,
                resolution=bar.resolution,
                uri=uri,
                schema_hash="sha256:canonical_bar_v1",
                refreshed_at=refreshed_at,
            )
        return list(refs.values())

    def _partition_uri(self, *, symbol: str, day: str, resolution: str) -> str:
        partition = (
            self.base_path
            / f"symbol={symbol}"
            / f"date={day}"
            / f"resolution={resolution}"
        )
        return partition.as_uri()

    def resolve_ref(self, ref_id: UUID, refs: Iterable[DatasetRef]) -> DatasetRef | None:
        for ref in refs:
            if ref.ref_id == ref_id:
                return ref
        return None
