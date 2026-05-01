from service_risk_exec.guards import GuardAction, RuntimeRiskGuard


def test_runtime_guard_blocks_new_orders_on_concentration_breach() -> None:
    guard = RuntimeRiskGuard.from_config(
        {
            "strat": {
                "max_intraday_drawdown": 0.1,
                "max_position_concentration": 0.2,
                "max_daily_turnover": 100,
                "max_slippage_deviation_bps": 50,
            }
        }
    )
    decision = guard.evaluate(
        strategy_key="strat",
        intraday_drawdown=0.05,
        position_concentration=0.25,
        turnover_delta=10,
        slippage_deviation_bps=1,
    )
    assert decision.action == GuardAction.BLOCK_NEW_ORDERS
    assert "MAX_POSITION_CONCENTRATION" in decision.breached_rules


def test_runtime_guard_derisks_on_drawdown_breach() -> None:
    guard = RuntimeRiskGuard.from_config(
        {
            "strat": {
                "max_intraday_drawdown": 0.03,
                "max_position_concentration": 0.6,
                "max_daily_turnover": 100,
                "max_slippage_deviation_bps": 50,
            }
        }
    )
    decision = guard.evaluate(
        strategy_key="strat",
        intraday_drawdown=0.04,
        position_concentration=0.2,
        turnover_delta=10,
        slippage_deviation_bps=1,
    )
    assert decision.action == GuardAction.DE_RISK
    assert "MAX_INTRADAY_DRAWDOWN" in decision.breached_rules
