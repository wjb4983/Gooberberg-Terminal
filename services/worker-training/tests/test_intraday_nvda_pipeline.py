from worker_training.modeling.intraday_nvda import StrategyParams, SweepConfig, compute_intraday_features, run_variant_sweep


def _rows() -> list[dict[str, object]]:
    return [
        {"symbol": "NVDA", "session": "2026-04-01", "minute": 1, "open": 100.0, "close": 99.2},
        {"symbol": "NVDA", "session": "2026-04-01", "minute": 2, "open": 100.0, "close": 97.0},
        {"symbol": "NVDA", "session": "2026-04-01", "minute": 3, "open": 100.0, "close": 100.5},
        {"symbol": "NVDA", "session": "2026-04-02", "minute": 1, "open": 101.0, "close": 100.8},
        {"symbol": "NVDA", "session": "2026-04-02", "minute": 2, "open": 101.0, "close": 99.5},
        {"symbol": "NVDA", "session": "2026-04-02", "minute": 3, "open": 101.0, "close": 99.7},
        {"symbol": "AAPL", "session": "2026-04-02", "minute": 1, "open": 10.0, "close": 11.0},
    ]


def test_compute_intraday_features_outputs_required_signals() -> None:
    features = compute_intraday_features(
        _rows(),
        params=StrategyParams(dip_threshold=0.01, confirmation_window=2, rebound_timeout=3),
    )
    assert len(features) == 2
    for feature in features:
        assert "opening_return" in feature
        assert "dip_depth" in feature
        assert "recovery_likelihood" in feature
        assert "recovery_minute" in feature


def test_variant_sweep_returns_rules_and_ml_ranked() -> None:
    results = run_variant_sweep(
        _rows(),
        SweepConfig(dip_thresholds=(0.01, 0.02), confirmation_windows=(2,), rebound_timeouts=(2, 3)),
    )
    assert len(results) == 8
    assert results[0].score >= results[-1].score
    model_types = {result.model_type for result in results}
    assert model_types == {"rules", "ml"}
