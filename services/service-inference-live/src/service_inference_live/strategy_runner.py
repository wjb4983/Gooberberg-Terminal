from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from gb_core.event_schemas import DecisionEvent, MarketDataEvent, SignalEvent, utc_now


@dataclass(frozen=True)
class RationaleMetadata:
    decision_event_id: UUID
    trace_id: UUID
    strategy_version: str
    config_hash: str
    rationale_kind: str
    rationale_payload: dict[str, Any]
    feature_snapshot: dict[str, float]


@dataclass
class InMemoryRationaleStore:
    _records: list[RationaleMetadata] = field(default_factory=list)

    def persist(self, metadata: RationaleMetadata) -> None:
        self._records.append(metadata)

    def by_decision_event_id(self, decision_event_id: UUID) -> RationaleMetadata | None:
        return next((record for record in self._records if record.decision_event_id == decision_event_id), None)


class StrategyRunner:
    def __init__(self, *, producer: str, strategy_version: str, config_hash: str, rationale_store: InMemoryRationaleStore):
        self._producer = producer
        self._strategy_version = strategy_version
        self._config_hash = config_hash
        self._rationale_store = rationale_store

    def run(self, market_data: MarketDataEvent) -> tuple[SignalEvent, DecisionEvent]:
        signal = self._build_signal_event(market_data)
        decision = self._build_decision_event(signal)

        self._rationale_store.persist(
            RationaleMetadata(
                decision_event_id=decision.event_id,
                trace_id=decision.trace_id,
                strategy_version=decision.strategy_version,
                config_hash=decision.config_hash,
                rationale_kind=decision.rationale_kind,
                rationale_payload=decision.rationale_metadata,
                feature_snapshot=signal.features,
            )
        )
        return signal, decision

    def _build_signal_event(self, market_data: MarketDataEvent) -> SignalEvent:
        spread = market_data.ask - market_data.bid
        mid = (market_data.ask + market_data.bid) / 2
        momentum = (market_data.last - mid) / mid if mid else 0.0
        liquidity = min(market_data.volume / 1_000_000, 1.0)
        strength = max(min((momentum * 8) + (liquidity - 0.9), 1.0), -1.0)
        now = utc_now()
        return SignalEvent(
            event_id=uuid4(),
            trace_id=market_data.trace_id,
            schema_version=market_data.schema_version,
            event_type="SignalEvent",
            event_time=market_data.event_time,
            ingest_time=market_data.ingest_time,
            process_time=now,
            producer=self._producer,
            strategy_version=self._strategy_version,
            config_hash=self._config_hash,
            signal_name="micro-momentum",
            symbol=market_data.symbol,
            strength=round(strength, 5),
            features={"spread": spread, "mid": mid, "momentum": momentum, "liquidity": liquidity},
        )

    def _build_decision_event(self, signal: SignalEvent) -> DecisionEvent:
        threshold = 0.02
        reasons: list[str] = []
        decision = "hold"
        if signal.strength >= threshold:
            decision = "buy"
            reasons.append("strength_above_buy_threshold")
        elif signal.strength <= -threshold:
            decision = "sell"
            reasons.append("strength_below_sell_threshold")
        else:
            reasons.append("strength_inside_no_trade_band")

        confidence = min(abs(signal.strength), 1.0)
        feature_snapshot_ref = f"signal:{signal.event_id}:features"
        now = utc_now()
        return DecisionEvent(
            event_id=uuid4(),
            trace_id=signal.trace_id,
            schema_version=signal.schema_version,
            event_type="DecisionEvent",
            event_time=signal.event_time,
            ingest_time=signal.ingest_time,
            process_time=now,
            producer=self._producer,
            strategy_version=self._strategy_version,
            config_hash=self._config_hash,
            decision=decision,
            symbol=signal.symbol,
            rationale=",".join(reasons),
            go_no_go=decision != "hold",
            reasons=reasons,
            confidence=round(confidence, 5),
            feature_snapshot_ref=feature_snapshot_ref,
            rationale_kind="rule",
            rationale_metadata={
                "signal_strength": signal.strength,
                "threshold": threshold,
                "signal_name": signal.signal_name,
            },
        )
