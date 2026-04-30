from random import Random

from service_risk_exec.main import (
    BasePlusJitterLatencyModel,
    ExecutionEngine,
    FixedBpsFeeModel,
    MarketEvent,
    ObservedOrFallbackSpreadModel,
    OrderRequest,
    OrderState,
    ParticipationCapFillModel,
    PowerLawSlippageModel,
)


def test_baseline_models_and_fill_attribution() -> None:
    engine = ExecutionEngine(
        fee_model=FixedBpsFeeModel(fixed_fee=1.0, maker_bps=1.0, taker_bps=2.0),
        slippage_model=PowerLawSlippageModel(a=1.0, b=3.0, gamma=2.0),
        spread_model=ObservedOrFallbackSpreadModel(fallback_by_symbol={"AAPL": 0.02}, default_spread=0.03),
        latency_model=BasePlusJitterLatencyModel(base_ms=5.0, jitter_ms=2.0, random=Random(1)),
        fill_model=ParticipationCapFillModel(participation_cap=0.25),
    )

    order = OrderRequest(symbol="AAPL", qty=100.0, aggressive=True, participation=0.2)
    event = MarketEvent(symbol="AAPL", displayed_qty=200.0, observed_spread=None)
    fill = engine.process_fill(order, event)

    assert fill.fill_qty == 50.0
    assert fill.state == OrderState.PARTIALLY_FILLED
    assert fill.fee_amt > 1.0
    assert fill.spread_cost == 1.0
    assert fill.impact_cost > 0
    assert fill.delay_cost > 0


def test_state_machine_terminal_fill() -> None:
    engine = ExecutionEngine(
        fee_model=FixedBpsFeeModel(),
        slippage_model=PowerLawSlippageModel(),
        spread_model=ObservedOrFallbackSpreadModel(fallback_by_symbol={}, default_spread=0.01),
        latency_model=BasePlusJitterLatencyModel(base_ms=0.0, jitter_ms=0.0),
        fill_model=ParticipationCapFillModel(participation_cap=10.0),
    )
    fill = engine.process_fill(
        OrderRequest(symbol="MSFT", qty=10.0, aggressive=False, participation=1.0),
        MarketEvent(symbol="MSFT", displayed_qty=100.0, observed_spread=0.02),
    )
    assert fill.state == OrderState.FILLED
