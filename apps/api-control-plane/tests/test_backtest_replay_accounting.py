from app.domain.backtest_runs.replay import replay_backtest


def test_replay_consumes_fills_and_emits_position_and_pnl_events() -> None:
    replay = replay_backtest(
        [
            {"type": "order", "order_id": "o-1", "symbol": "AAPL", "side": "buy", "quantity": 10, "price": 100},
            {"type": "fill", "order_id": "o-1", "symbol": "AAPL", "quantity": 4, "price": 101, "fee": 0.5, "fill_id": "f-1"},
            {"type": "fill", "order_id": "o-1", "symbol": "AAPL", "quantity": 6, "price": 99, "fee": 0.5, "fill_id": "f-2"},
        ]
    )

    assert replay["positions"] == [{"symbol": "AAPL", "quantity": 10.0}]
    assert len(replay["position_events"]) == 2
    assert all(e["event_type"] == "PositionEvent" for e in replay["position_events"])
    assert len(replay["pnl_events"]) == 2
    assert all(e["event_type"] == "PnLEvent" for e in replay["pnl_events"])
    assert replay["pnl_state"]["fees"] == 1.0
    assert replay["pnl_state"]["slippage"] == 10.0
    assert replay["reconciliation"]["inventory_conservation_ok"] is True
    assert replay["reconciliation"]["cash_consistency_ok"] is True


def test_replay_reconciliation_in_pnl_events() -> None:
    replay = replay_backtest(
        [
            {"type": "order", "order_id": "o-2", "symbol": "MSFT", "side": "sell", "quantity": 5, "price": 200},
            {"type": "fill", "order_id": "o-2", "symbol": "MSFT", "quantity": 5, "price": 198, "fee": 1.0, "fill_id": "f-3"},
        ]
    )

    pnl_event = replay["pnl_events"][0]
    assert pnl_event["inventory_conservation_ok"] is True
    assert pnl_event["cash_consistency_ok"] is True
    assert replay["pnl_state"]["cash"] == 989.0
