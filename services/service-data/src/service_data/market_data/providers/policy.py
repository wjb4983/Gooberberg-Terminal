"""Provider policy configuration for market-data ingestion behavior."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from service_data.market_data.models import AssetClass, Resolution


@dataclass(frozen=True)
class RetryPolicy:
    """Retry/backoff policy tuned for provider HTTP failures."""

    max_retries: int = 4
    base_backoff_seconds: float = 0.5
    max_backoff_seconds: float = 30.0
    rate_limit_backoff_seconds: float = 5.0


@dataclass(frozen=True)
class ProviderPolicy:
    """Policy values controlling provider ingestion behavior."""

    historical_window_years: dict[AssetClass, int]
    api_history_override_years: dict[AssetClass, int | None]
    chunk_days_by_resolution: dict[Resolution, int]
    finest_resolution_by_asset: dict[AssetClass, Resolution]
    retry: RetryPolicy

    @staticmethod
    def default() -> "ProviderPolicy":
        return ProviderPolicy(
            historical_window_years={"stocks": 5, "options": 2},
            api_history_override_years={"stocks": None, "options": None},
            chunk_days_by_resolution={"minute": 30, "hour": 120, "day": 3650},
            finest_resolution_by_asset={"stocks": "minute", "options": "minute"},
            retry=RetryPolicy(),
        )

    @staticmethod
    def from_env() -> "ProviderPolicy":
        baseline = ProviderPolicy.default()
        return ProviderPolicy(
            historical_window_years={
                "stocks": _read_int("GB_MD_POLICY_HIST_WINDOW_STOCKS_YEARS", baseline.historical_window_years["stocks"]),
                "options": _read_int("GB_MD_POLICY_HIST_WINDOW_OPTIONS_YEARS", baseline.historical_window_years["options"]),
            },
            api_history_override_years={
                "stocks": _read_optional_int("GB_MD_POLICY_API_HISTORY_OVERRIDE_STOCKS_YEARS"),
                "options": _read_optional_int("GB_MD_POLICY_API_HISTORY_OVERRIDE_OPTIONS_YEARS"),
            },
            chunk_days_by_resolution={
                "minute": _read_int("GB_MD_POLICY_CHUNK_MINUTE_DAYS", baseline.chunk_days_by_resolution["minute"]),
                "hour": _read_int("GB_MD_POLICY_CHUNK_HOUR_DAYS", baseline.chunk_days_by_resolution["hour"]),
                "day": _read_int("GB_MD_POLICY_CHUNK_DAY_DAYS", baseline.chunk_days_by_resolution["day"]),
            },
            finest_resolution_by_asset={
                "stocks": _read_resolution("GB_MD_POLICY_FINEST_RESOLUTION_STOCKS", baseline.finest_resolution_by_asset["stocks"]),
                "options": _read_resolution("GB_MD_POLICY_FINEST_RESOLUTION_OPTIONS", baseline.finest_resolution_by_asset["options"]),
            },
            retry=RetryPolicy(
                max_retries=_read_int("GB_MD_POLICY_RETRY_MAX_RETRIES", baseline.retry.max_retries),
                base_backoff_seconds=_read_float("GB_MD_POLICY_RETRY_BASE_BACKOFF_SECONDS", baseline.retry.base_backoff_seconds),
                max_backoff_seconds=_read_float("GB_MD_POLICY_RETRY_MAX_BACKOFF_SECONDS", baseline.retry.max_backoff_seconds),
                rate_limit_backoff_seconds=_read_float(
                    "GB_MD_POLICY_RETRY_RATE_LIMIT_BACKOFF_SECONDS",
                    baseline.retry.rate_limit_backoff_seconds,
                ),
            ),
        )

    def effective_history_window_years(self, asset_class: AssetClass) -> int:
        baseline = self.historical_window_years[asset_class]
        override = self.api_history_override_years[asset_class]
        if override is None:
            return baseline
        return max(baseline, override)

    def recommended_start(self, *, asset_class: AssetClass, end: datetime) -> datetime:
        years = self.effective_history_window_years(asset_class)
        return end.astimezone(UTC) - timedelta(days=365 * years)


def _read_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def _read_optional_int(key: str) -> int | None:
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return None
    try:
        return max(1, int(raw))
    except ValueError:
        return None


def _read_float(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return max(0.0, float(raw))
    except ValueError:
        return default


def _read_resolution(key: str, default: Resolution) -> Resolution:
    raw = os.getenv(key)
    if raw is None:
        return default
    candidate = raw.strip().lower()
    if candidate in {"minute", "hour", "day"}:
        return candidate  # type: ignore[return-value]
    return default
