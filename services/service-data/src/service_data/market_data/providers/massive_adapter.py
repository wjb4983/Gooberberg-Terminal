"""Massive provider adapter with retry/backoff and normalized error mapping."""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib import error, parse, request

from service_data.market_data.models import CanonicalBar, Resolution
from service_data.market_data.providers.base import MarketDataProvider, ProviderError
from service_data.market_data.providers.policy import ProviderPolicy

_DEFAULT_API_KEY_PATH = Path("/etc/Massive/api-key")


class MassiveAdapter(MarketDataProvider):
    """Adapter for Massive aggregates API."""

    provider_name = "massive"

    def __init__(
        self,
        *,
        base_url: str = "https://api.massive.com/v2/aggs/ticker",
        api_key: str | None = None,
        api_key_path: Path = _DEFAULT_API_KEY_PATH,
        env_var: str = "MASSIVE_API_KEY",
        timeout_seconds: float = 15.0,
        max_retries: int | None = None,
        backoff_seconds: float | None = None,
        policy: ProviderPolicy | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or self._read_api_key(api_key_path=api_key_path, env_var=env_var)
        self.timeout_seconds = timeout_seconds
        self.policy = policy or ProviderPolicy.from_env()
        self.max_retries = self.policy.retry.max_retries if max_retries is None else max_retries
        self.backoff_seconds = self.policy.retry.base_backoff_seconds if backoff_seconds is None else backoff_seconds

    @staticmethod
    def _read_api_key(*, api_key_path: Path, env_var: str) -> str:
        if api_key_path.exists():
            key = api_key_path.read_text(encoding="utf-8").strip()
            if key:
                return key

        key = os.getenv(env_var, "").strip()
        if key:
            return key
        raise ProviderError("auth", "Missing Massive API key")

    def fetch_bars(
        self,
        *,
        symbol: str,
        start: datetime,
        end: datetime,
        resolution: Resolution,
    ) -> list[CanonicalBar]:
        if resolution not in {"minute", "hour", "day"}:
            raise ProviderError("invalid_request", f"Unsupported resolution: {resolution}")

        chunks = self._chunk_ranges(start=start, end=end, resolution=resolution)
        all_bars: list[CanonicalBar] = []
        for chunk_start, chunk_end in chunks:
            all_bars.extend(
                self._fetch_chunk(
                    symbol=symbol,
                    start=chunk_start,
                    end=chunk_end,
                    resolution=resolution,
                )
            )
        return all_bars

    def _fetch_chunk(
        self,
        *,
        symbol: str,
        start: datetime,
        end: datetime,
        resolution: Resolution,
    ) -> list[CanonicalBar]:
        span = self._resolution_span(resolution)
        from_ms = int(start.astimezone(UTC).timestamp() * 1000)
        to_ms = int(end.astimezone(UTC).timestamp() * 1000)

        endpoint = f"{self.base_url}/{symbol.upper()}/range/1/{span}/{from_ms}/{to_ms}"
        query = parse.urlencode({"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": self.api_key})
        req = request.Request(f"{endpoint}?{query}", headers={"Accept": "application/json"})

        last_error: ProviderError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                    return self._normalize(payload, symbol=symbol, resolution=resolution)
            except error.HTTPError as exc:
                mapped = self._map_http_error(exc)
                last_error = mapped
                if mapped.retriable and attempt < self.max_retries:
                    self._sleep_before_retry(attempt=attempt, status_code=exc.code, retry_after=exc.headers.get("Retry-After"))
                    continue
                raise mapped from exc
            except error.URLError as exc:
                last_error = ProviderError("unavailable", str(exc.reason), retriable=True)
                if attempt < self.max_retries:
                    self._sleep_before_retry(attempt=attempt)
                    continue
                raise last_error from exc
            except json.JSONDecodeError as exc:
                raise ProviderError("bad_payload", "Massive returned invalid JSON") from exc

        if last_error is not None:
            raise last_error
        raise ProviderError("unknown", "Unknown Massive adapter failure")

    def _chunk_ranges(self, *, start: datetime, end: datetime, resolution: Resolution) -> list[tuple[datetime, datetime]]:
        if end <= start:
            return []

        chunk_days = self.policy.chunk_days_by_resolution[resolution]
        step = timedelta(days=chunk_days)
        ranges: list[tuple[datetime, datetime]] = []
        cursor = start.astimezone(UTC)
        stop = end.astimezone(UTC)
        while cursor < stop:
            chunk_end = min(cursor + step, stop)
            ranges.append((cursor, chunk_end))
            cursor = chunk_end
        return ranges

    def _sleep_before_retry(self, *, attempt: int, status_code: int | None = None, retry_after: str | None = None) -> None:
        if status_code == 429:
            if retry_after:
                wait = _parse_retry_after_seconds(retry_after)
                if wait is not None:
                    time.sleep(wait)
                    return
            time.sleep(self.policy.retry.rate_limit_backoff_seconds)
            return

        exp_wait = self.backoff_seconds * (2**attempt)
        bounded = min(exp_wait, self.policy.retry.max_backoff_seconds)
        time.sleep(bounded)

    def _normalize(
        self,
        payload: dict[str, object],
        *,
        symbol: str,
        resolution: Resolution,
    ) -> list[CanonicalBar]:
        rows = payload.get("results", [])
        if not isinstance(rows, list):
            raise ProviderError("bad_payload", "Massive payload missing results list")

        bars: list[CanonicalBar] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            ts = datetime.fromtimestamp(float(row.get("t", 0)) / 1000, tz=UTC)
            bars.append(
                CanonicalBar(
                    symbol=symbol,
                    ts=ts,
                    open=float(row.get("o", 0.0)),
                    high=float(row.get("h", 0.0)),
                    low=float(row.get("l", 0.0)),
                    close=float(row.get("c", 0.0)),
                    volume=float(row.get("v", 0.0)),
                    vwap=float(row["vw"]) if row.get("vw") is not None else None,
                    trades=int(row["n"]) if row.get("n") is not None else None,
                    source=self.provider_name,
                    resolution=resolution,
                )
            )
        return bars

    @staticmethod
    def _map_http_error(exc: error.HTTPError) -> ProviderError:
        status = exc.code
        if status in (401, 403):
            return ProviderError("auth", "Massive authentication failed")
        if status == 404:
            return ProviderError("not_found", "Symbol or endpoint not found")
        if status == 429:
            return ProviderError("rate_limit", "Massive rate limit exceeded", retriable=True)
        if 500 <= status < 600:
            return ProviderError("unavailable", f"Massive upstream error: {status}", retriable=True)
        return ProviderError("invalid_request", f"Massive request failed: {status}")

    @staticmethod
    def _resolution_span(resolution: Resolution) -> str:
        if resolution == "minute":
            return "minute"
        if resolution == "hour":
            return "hour"
        if resolution == "day":
            return "day"
        raise ProviderError("invalid_request", f"Unsupported resolution: {resolution}")


def _parse_retry_after_seconds(header_value: str) -> float | None:
    value = header_value.strip()
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        return None
    if seconds < 0:
        return None
    return min(seconds, 300.0)
