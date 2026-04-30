from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPLAY_PATH = Path(__file__).resolve().parents[1] / "app" / "domain" / "backtest_runs" / "replay.py"
_SPEC = importlib.util.spec_from_file_location("backtest_replay_module", _REPLAY_PATH)
assert _SPEC and _SPEC.loader
_REPLAY = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _REPLAY
_SPEC.loader.exec_module(_REPLAY)

replay_backtest = _REPLAY.replay_backtest
validate_replay = _REPLAY.validate_replay


def _event_log() -> list[dict[str, object]]:
    return [
        {"type": "decision", "decision_id": "d-1", "approved": True},
        {"type": "order", "order_id": "o-1", "symbol": "AAPL", "side": "buy", "quantity": 10, "price": 100.0},
        {"type": "fill", "order_id": "o-1", "symbol": "AAPL", "quantity": 3, "price": 100.0, "fee": 0.1, "fill_id": "f-1"},
        {"type": "fill", "order_id": "o-1", "symbol": "AAPL", "quantity": 7, "price": 100.0, "fee": 0.2, "fill_id": "f-2"},
    ]


def test_replay_equivalence_live_vs_reconstructed_outcomes() -> None:
    live_outcome = replay_backtest(_event_log())
    reconstructed_outcome = replay_backtest(list(_event_log()))

    validation = validate_replay(
        reconstructed_outcome,
        live_outcome,
        run_strategy_version="v1",
        run_config_hash="cfg1",
        requested_strategy_version="v1",
        requested_config_hash="cfg1",
    )

    assert validation.validation["status"] == "ok"
    assert validation.validation["mismatch_count"] == 0


def test_idempotency_under_duplicate_fill_injection_detects_divergence() -> None:
    baseline = replay_backtest(_event_log())
    duplicate_injected = replay_backtest(_event_log() + [_event_log()[-1]])

    validation = validate_replay(
        duplicate_injected,
        baseline,
        run_strategy_version="v1",
        run_config_hash="cfg1",
        requested_strategy_version="v1",
        requested_config_hash="cfg1",
    )

    assert validation.validation["status"] == "diverged"
    assert validation.validation["mismatch_count"] >= 1


def test_out_of_order_delayed_and_dropped_market_data_fills() -> None:
    replay = replay_backtest(
        [
            {"type": "fill", "order_id": "unknown-order", "symbol": "AAPL", "quantity": 3, "price": 101.0, "fee": 0.1, "fill_id": "ignored"},
            {"type": "order", "order_id": "o-1", "symbol": "AAPL", "side": "buy", "quantity": 10, "price": 100.0},
            {"type": "fill", "order_id": "o-1", "symbol": "AAPL", "quantity": 4, "price": 100.5, "fee": 0.2, "fill_id": "f-1"},
            {"type": "market_data", "symbol": "AAPL", "price": 99.0, "timestamp": "late-tick"},
            {"type": "fill", "order_id": "o-1", "symbol": "AAPL", "quantity": 6, "price": 99.5, "fee": 0.3, "fill_id": "f-2"},
            {"type": "market_data", "symbol": "AAPL", "price": 102.0, "timestamp": "delayed-tick"},
        ]
    )

    assert replay["positions"] == [{"symbol": "AAPL", "quantity": 10.0}]
    assert len(replay["pnl_events"]) == 2
    assert replay["reconciliation"]["inventory_conservation_ok"] is True
    assert replay["reconciliation"]["cash_consistency_ok"] is True
