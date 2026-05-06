"""Provider capability policy for ingest resolution constraints."""

from __future__ import annotations

from dataclasses import dataclass

AssetClass = str
ProviderName = str


@dataclass(frozen=True)
class ProviderCapabilities:
    provider: ProviderName
    asset_class: AssetClass
    min_ingest_resolution: str
    provider_native_subminute_supported: bool
    notes: str


_CAPABILITIES: dict[tuple[ProviderName, AssetClass], ProviderCapabilities] = {
    (
        "massive",
        "stocks",
    ): ProviderCapabilities(
        provider="massive",
        asset_class="stocks",
        min_ingest_resolution="minute",
        provider_native_subminute_supported=False,
        notes="MassiveAdapter supports minute/hour/day aggregate fetches only.",
    ),
    (
        "massive",
        "options",
    ): ProviderCapabilities(
        provider="massive",
        asset_class="options",
        min_ingest_resolution="minute",
        provider_native_subminute_supported=False,
        notes="MassiveAdapter supports minute/hour/day aggregate fetches only.",
    ),
}


def get_provider_capabilities(provider: str, asset_class: str) -> ProviderCapabilities | None:
    return _CAPABILITIES.get((provider.lower(), asset_class.lower()))


def list_provider_capabilities() -> list[ProviderCapabilities]:
    return sorted(_CAPABILITIES.values(), key=lambda item: (item.provider, item.asset_class))
