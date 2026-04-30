from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from gb_core.schemas import ExecutionDecision, RiskOverride, StrategyIntent


class RiskConfig(BaseModel):
    max_quantity: float = Field(default=1000.0, gt=0)
    max_notional: float = Field(default=250_000.0, gt=0)
    max_symbol_position: float = Field(default=5_000.0, gt=0)
    max_sector_position: float = Field(default=25_000.0, gt=0)
    max_gross_exposure: float = Field(default=2_500_000.0, gt=0)
    max_net_exposure: float = Field(default=500_000.0, gt=0)
    max_trades_per_minute: int = Field(default=120, gt=0)
    allowed_instruments: set[str] = Field(default_factory=lambda: {"equity"})
    allowed_session_windows_utc: list[tuple[int, int]] = Field(default_factory=lambda: [(13, 20)])


@dataclass
class IntentEventRecord:
    intent: StrategyIntent
    received_at: datetime


class RiskExecutionAuthority:
    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig()
        self._overrides: list[RiskOverride] = []
        self._intent_events: list[IntentEventRecord] = []
        self._decision_events: list[ExecutionDecision] = []
        self.override_audit_trail: list[dict[str, Any]] = []
        self.decision_audit_trail: list[dict[str, Any]] = []

    def consume_intent(self, intent: StrategyIntent) -> ExecutionDecision:
        self._intent_events.append(IntentEventRecord(intent=intent, received_at=datetime.now(UTC)))

        override = self._find_override(intent)
        max_qty = override.max_quantity if override and override.max_quantity is not None else self.config.max_quantity
        max_notional = (
            override.max_notional if override and override.max_notional is not None else self.config.max_notional
        )

        rule_results: list[dict[str, Any]] = []
        failure_reason_codes: list[str] = []

        def _record(name: str, passed: bool, reason_code: str, detail: str) -> None:
            rule_results.append({"rule": name, "passed": passed, "reason_code": reason_code, "detail": detail})
            if not passed:
                failure_reason_codes.append(reason_code)

        if intent.quantity is None or intent.symbol is None:
            _record("required_fields", False, "MISSING_ORDER_FIELDS", "intent missing required symbol/quantity")
        else:
            _record("required_fields", True, "OK", "required fields present")
            _record("max_order_size", intent.quantity <= max_qty, "MAX_QUANTITY_EXCEEDED", f"quantity {intent.quantity} <= max {max_qty}")
            notional = intent.quantity * (intent.limit_price or 0)
            _record(
                "max_notional",
                intent.limit_price is None or notional <= max_notional,
                "MAX_NOTIONAL_EXCEEDED",
                f"notional {notional} <= max {max_notional}",
            )
            instrument = str(intent.params.get("instrument", "equity"))
            _record("allowed_instruments", instrument in self.config.allowed_instruments, "INSTRUMENT_NOT_ALLOWED", instrument)
            hour = intent.created_at.hour
            in_session = any(start <= hour < end for start, end in self.config.allowed_session_windows_utc)
            _record("session_window", in_session, "OUTSIDE_SESSION_WINDOW", f"hour={hour}")
            next_symbol_position = abs(float(intent.params.get("symbol_position_after", 0.0)))
            _record("max_symbol_position", next_symbol_position <= self.config.max_symbol_position, "MAX_SYMBOL_POSITION_EXCEEDED", str(next_symbol_position))
            next_sector_position = abs(float(intent.params.get("sector_position_after", 0.0)))
            _record("max_sector_position", next_sector_position <= self.config.max_sector_position, "MAX_SECTOR_POSITION_EXCEEDED", str(next_sector_position))
            gross_exposure = abs(float(intent.params.get("gross_exposure_after", 0.0)))
            _record("gross_exposure", gross_exposure <= self.config.max_gross_exposure, "MAX_GROSS_EXPOSURE_EXCEEDED", str(gross_exposure))
            net_exposure = abs(float(intent.params.get("net_exposure_after", 0.0)))
            _record("net_exposure", net_exposure <= self.config.max_net_exposure, "MAX_NET_EXPOSURE_EXCEEDED", str(net_exposure))
            trades_last_minute = int(intent.params.get("trades_last_minute", 0))
            _record("trade_frequency", trades_last_minute <= self.config.max_trades_per_minute, "TRADE_FREQUENCY_LIMIT_EXCEEDED", str(trades_last_minute))

        approved = not failure_reason_codes
        reason_code = failure_reason_codes[0] if failure_reason_codes else "APPROVED"
        detail = "intent approved" if approved else "; ".join(failure_reason_codes)

        decision = ExecutionDecision(
            intent_id=intent.intent_id,
            approved=approved,
            reason_code=reason_code,
            failure_reason_codes=failure_reason_codes,
            detail=detail,
            applied_override_id=override.override_id if override else None,
        )
        self._decision_events.append(decision)
        self.decision_audit_trail.append(
            {
                "decision_id": str(decision.decision_id),
                "intent_id": str(decision.intent_id),
                "approved": decision.approved,
                "reason_code": decision.reason_code,
                "failure_reason_codes": decision.failure_reason_codes,
                "rule_results": rule_results,
                "recorded_at": decision.evaluated_at.isoformat(),
            }
        )
        return decision

    def add_override(self, override: RiskOverride) -> RiskOverride:
        self._overrides.insert(0, override)
        self.override_audit_trail.append(
            {
                "override_id": str(override.override_id),
                "strategy_key": override.strategy_key,
                "symbol": override.symbol,
                "recorded_at": override.created_at.isoformat(),
                "action": "upsert",
            }
        )
        return override

    def list_overrides(self) -> list[RiskOverride]:
        return list(self._overrides)

    def recent_decisions(self, limit: int = 50) -> list[ExecutionDecision]:
        return list(reversed(self._decision_events[-limit:]))

    def event_trail(self) -> list[dict[str, str]]:
        trail: list[dict[str, str]] = []
        for record in self._intent_events:
            trail.append(
                {
                    "type": "intent_received",
                    "intent_id": str(record.intent.intent_id),
                    "at": record.received_at.isoformat(),
                }
            )
        for decision in self._decision_events:
            trail.append(
                {
                    "type": "decision_emitted",
                    "intent_id": str(decision.intent_id),
                    "decision_id": str(decision.decision_id),
                    "at": decision.evaluated_at.isoformat(),
                }
            )
        return trail

    def _find_override(self, intent: StrategyIntent) -> RiskOverride | None:
        for override in self._overrides:
            if override.strategy_key and override.strategy_key == intent.strategy_key:
                return override
            if override.symbol and override.symbol == intent.symbol:
                return override
        return None
