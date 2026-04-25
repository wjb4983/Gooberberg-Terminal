from __future__ import annotations

from datetime import UTC, datetime

from service_data.market_data.providers.massive_adapter import MassiveAdapter, _parse_retry_after_seconds
from service_data.market_data.providers.policy import ProviderPolicy


def test_provider_policy_defaults_and_history_override(monkeypatch) -> None:
    monkeypatch.setenv("GB_MD_POLICY_HIST_WINDOW_STOCKS_YEARS", "5")
    monkeypatch.setenv("GB_MD_POLICY_HIST_WINDOW_OPTIONS_YEARS", "2")
    monkeypatch.setenv("GB_MD_POLICY_API_HISTORY_OVERRIDE_STOCKS_YEARS", "8")
    monkeypatch.setenv("GB_MD_POLICY_FINEST_RESOLUTION_OPTIONS", "hour")

    policy = ProviderPolicy.from_env()

    assert policy.effective_history_window_years("stocks") == 8
    assert policy.effective_history_window_years("options") == 2
    assert policy.finest_resolution_by_asset["options"] == "hour"

    end = datetime(2026, 4, 25, tzinfo=UTC)
    start = policy.recommended_start(asset_class="stocks", end=end)
    assert start.year <= 2018


def test_massive_adapter_chunk_ranges_follow_policy() -> None:
    policy = ProviderPolicy.default()
    adapter = MassiveAdapter(api_key="secret", policy=policy)

    ranges = adapter._chunk_ranges(
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 3, 15, tzinfo=UTC),
        resolution="minute",
    )

    assert len(ranges) == 3
    assert ranges[0][0] == datetime(2026, 1, 1, tzinfo=UTC)
    assert ranges[-1][1] == datetime(2026, 3, 15, tzinfo=UTC)


def test_retry_after_parser() -> None:
    assert _parse_retry_after_seconds("7") == 7
    assert _parse_retry_after_seconds("999") == 300.0
    assert _parse_retry_after_seconds("bad") is None
