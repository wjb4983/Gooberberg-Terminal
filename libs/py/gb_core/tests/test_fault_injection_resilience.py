from gb_core.risk import RiskConfig, RiskExecutionAuthority


def test_circuit_breaker_halt_on_risk_breaches_and_warn_on_concentration() -> None:
    authority = RiskExecutionAuthority(
        RiskConfig(
            max_daily_drawdown_pct=5,
            max_rolling_drawdown_pct=8,
            max_loss_per_symbol=1_000,
            max_loss_per_strategy=5_000,
            max_symbol_concentration_pct=30,
        )
    )

    alerts = authority.evaluate_continuous_monitors(
        monitor_input={
            "daily_drawdown_pct": 7,
            "rolling_drawdown_pct": 9,
            "symbol_losses": {"AAPL": -2_000},
            "strategy_loss": -10_000,
            "symbol_concentration_pct": {"AAPL": 35},
        }
    )

    actions = [item["policy_action"] for item in authority.policy_action_audit_trail]
    assert len(alerts) == 5
    assert actions.count("halt") == 4
    assert actions.count("throttle") == 1
