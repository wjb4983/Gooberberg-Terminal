from service_data.market_data.providers.capabilities import get_provider_capabilities, list_provider_capabilities


def test_massive_capabilities_minimum_resolution_is_minute() -> None:
    caps = get_provider_capabilities("massive", "stocks")
    assert caps is not None
    assert caps.min_ingest_resolution == "minute"
    assert caps.provider_native_subminute_supported is False


def test_list_provider_capabilities_includes_massive_stocks() -> None:
    caps = list_provider_capabilities()
    assert any(item.provider == "massive" and item.asset_class == "stocks" for item in caps)
