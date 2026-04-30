from gb_core.risk import RiskConfig, RiskExecutionAuthority


def test_continuous_monitors_emit_alerts_and_policy_actions() -> None:
    authority = RiskExecutionAuthority(
        RiskConfig(
            max_daily_drawdown_pct=5,
            max_rolling_drawdown_pct=8,
            max_loss_per_symbol=1000,
            max_loss_per_strategy=5000,
            max_symbol_concentration_pct=30,
            max_strategy_concentration_pct=50,
            high_vol_regime_threshold=25,
            vol_regime_throttle_scale=0.4,
        )
    )

    alerts = authority.evaluate_continuous_monitors(
        monitor_input={
            "daily_drawdown_pct": 6,
            "rolling_drawdown_pct": 10,
            "symbol_losses": {"AAPL": -1500},
            "strategy_loss": -6000,
            "symbol_concentration_pct": {"AAPL": 33},
            "strategy_concentration_pct": 55,
            "volatility_regime": 30,
        }
    )

    assert len(alerts) == 7
    assert {a.event_type for a in alerts} == {"AlertEvent"}
    assert {a.category for a in alerts} == {"risk"}

    actions = {item["policy_action"] for item in authority.policy_action_audit_trail}
    assert actions == {"warn", "throttle", "halt"}
    assert all("context" in item for item in authority.policy_action_audit_trail)
