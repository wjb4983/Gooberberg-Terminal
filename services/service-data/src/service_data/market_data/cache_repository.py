"""Parquet-backed cache repository for canonical market bars."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from uuid import UUID, uuid4

import polars as pl

from service_data.market_data.models import CanonicalBar, DatasetRef


class CacheRepository:
    """Persist canonical bars in partitioned parquet with a dataset manifest."""

    MANIFEST_FILE = "manifest.json"
    INDEX_FIELDS = ["symbol", "resolution", "ts", "year", "month"]

    def __init__(self, *, base_path: Path) -> None:
        self.base_path = base_path.resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def write_bars(self, bars: Iterable[CanonicalBar]) -> list[DatasetRef]:
        items = list(bars)
        if not items:
            return []

        manifest = self._read_manifest()
        grouped: dict[tuple[str, str, str, str, str, str, str], list[CanonicalBar]] = {}
        for bar in items:
            key = self._partition_key(bar)
            grouped.setdefault(key, []).append(bar)

        refreshed_at = max(bar.ts for bar in items)
        refs: dict[tuple[str, str, str], DatasetRef] = {}
        manifest_partitions = list(manifest.get("partitions", []))
        for bars_for_partition in grouped.values():
            first = bars_for_partition[0]
            partition_dir = self._partition_dir(first)
            partition_dir.mkdir(parents=True, exist_ok=True)
            part_file = partition_dir / f"part-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-{uuid4().hex[:8]}.parquet"
            frame = pl.DataFrame([self._bar_row(bar) for bar in bars_for_partition])
            frame.write_parquet(part_file, compression="zstd")

            min_ts = min(bar.ts for bar in bars_for_partition)
            max_ts = max(bar.ts for bar in bars_for_partition)
            manifest_partitions.append(
                {
                    "path": str(part_file.relative_to(self.base_path)),
                    "provider": first.source,
                    "asset_class": first.asset_class,
                    "symbol": first.symbol,
                    "resolution": first.resolution,
                    "year": min_ts.astimezone(UTC).year,
                    "month": f"{min_ts.astimezone(UTC).month:02d}",
                    "day": min_ts.astimezone(UTC).date().isoformat(),
                    "start_ts": min_ts.astimezone(UTC).isoformat(),
                    "end_ts": max_ts.astimezone(UTC).isoformat(),
                    "row_count": len(bars_for_partition),
                }
            )

        manifest["partitions"] = manifest_partitions
        manifest["index_fields"] = self.INDEX_FIELDS
        manifest["updated_at"] = refreshed_at.astimezone(UTC).isoformat()
        self._write_manifest(manifest)

        for bar in items:
            day = bar.ts.astimezone(UTC).date()
            key = (bar.symbol, day.isoformat(), bar.resolution)
            if key in refs:
                continue
            ref_id = uuid4()
            uri = self._partition_uri(bar)
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

    def _partition_uri(self, bar: CanonicalBar) -> str:
        partition = self._partition_dir(bar)
        return f"file://{partition.as_posix()}"

    def _partition_key(self, bar: CanonicalBar) -> tuple[str, str, str, str, str, str, str]:
        ts = bar.ts.astimezone(UTC)
        entity = bar.symbol if bar.asset_class == "stocks" else (bar.underlying or bar.symbol)
        return (
            bar.source,
            bar.asset_class,
            entity,
            bar.resolution,
            f"{ts.year:04d}",
            f"{ts.month:02d}",
            f"{ts.day:02d}",
        )

    def _bar_row(self, bar: CanonicalBar) -> dict[str, object]:
        ts = bar.ts.astimezone(UTC)
        payload: dict[str, object] = {
            "symbol": bar.symbol,
            "ts": ts,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
            "vwap": bar.vwap,
            "trades": bar.trades,
            "source": bar.source,
            "resolution": bar.resolution,
            "asset_class": bar.asset_class,
            "year": f"{ts.year:04d}",
            "month": f"{ts.month:02d}",
            "day": f"{ts.day:02d}",
        }
        if bar.asset_class == "options":
            payload["underlying"] = bar.underlying
            payload["expiry"] = bar.expiry.isoformat() if bar.expiry else None
            payload["strike"] = bar.strike
            payload["right"] = bar.right
        return payload

    def _partition_dir(self, bar: CanonicalBar) -> Path:
        ts = bar.ts.astimezone(UTC)
        if bar.asset_class == "options":
            return (
                self.base_path
                / f"provider={bar.source}"
                / f"asset_class={bar.asset_class}"
                / f"underlying={bar.underlying}"
                / f"expiry={bar.expiry.isoformat()}"
                / f"strike={bar.strike}"
                / f"right={bar.right}"
                / f"resolution={bar.resolution}"
                / f"year={ts.year:04d}"
                / f"month={ts.month:02d}"
                / f"day={ts.day:02d}"
            )
        return self._partition_dir_from_values(
            provider=bar.source,
            asset_class=bar.asset_class,
            symbol=bar.symbol,
            resolution=bar.resolution,
            year=f"{ts.year:04d}",
            month=f"{ts.month:02d}",
            day=f"{ts.day:02d}",
        )

    def _partition_dir_from_values(
        self,
        *,
        provider: str,
        asset_class: str,
        symbol: str,
        resolution: str,
        year: str,
        month: str,
        day: str,
    ) -> Path:
        return (
            self.base_path
            / f"provider={provider}"
            / f"asset_class={asset_class}"
            / f"symbol={symbol}"
            / f"resolution={resolution}"
            / f"year={year}"
            / f"month={month}"
            / f"day={day}"
        )

    def _manifest_path(self) -> Path:
        return self.base_path / self.MANIFEST_FILE

    def _read_manifest(self) -> dict[str, object]:
        manifest_path = self._manifest_path()
        if not manifest_path.exists():
            return {"dataset": "market_data_bars", "partitions": [], "index_fields": self.INDEX_FIELDS}
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def _write_manifest(self, manifest: dict[str, object]) -> None:
        manifest_path = self._manifest_path()
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    def load_bars(
        self,
        *,
        symbol: str,
        resolution: str,
        start: datetime,
        end: datetime,
        provider: str = "massive",
    ) -> pl.DataFrame:
        start_utc = start.astimezone(UTC)
        end_utc = end.astimezone(UTC)
        years = self._years_in_range(start_utc, end_utc)
        months = self._months_in_range(start_utc, end_utc)
        partition_filter = pl.col("year").is_in(years) & pl.col("month").is_in(months)
        scan = pl.scan_parquet(str(self.base_path / "**" / "*.parquet"), hive_partitioning=True)
        return (
            scan.filter(
                (pl.col("provider") == provider)
                & (pl.col("symbol") == symbol.upper())
                & (pl.col("resolution") == resolution)
                & partition_filter
                & (pl.col("ts") >= start_utc)
                & (pl.col("ts") < end_utc)
            )
            .collect()
        )

    def _years_in_range(self, start: datetime, end: datetime) -> list[str]:
        return [f"{year:04d}" for year in range(start.year, end.year + 1)]

    def _months_in_range(self, start: datetime, end: datetime) -> list[str]:
        months: list[str] = []
        year = start.year
        month = start.month
        while (year, month) <= (end.year, end.month):
            months.append(f"{month:02d}")
            if month == 12:
                year += 1
                month = 1
            else:
                month += 1
        return months

    def resolve_ref(self, ref_id: UUID, refs: Iterable[DatasetRef]) -> DatasetRef | None:
        for ref in refs:
            if ref.ref_id == ref_id:
                return ref
        return None
