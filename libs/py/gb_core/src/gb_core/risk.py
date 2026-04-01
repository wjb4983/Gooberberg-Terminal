from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from gb_core.schemas import ExecutionDecision, RiskOverride, StrategyIntent


class RiskConfig(BaseModel):
    max_quantity: float = Field(default=1000.0, gt=0)
    max_notional: float = Field(default=250_000.0, gt=0)


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

        approved = True
        reason_code = "APPROVED"
        detail = "intent approved"

        if intent.quantity is None or intent.symbol is None:
            approved = False
            reason_code = "MISSING_ORDER_FIELDS"
            detail = "intent missing required symbol/quantity"
        elif intent.quantity > max_qty:
            approved = False
            reason_code = "MAX_QUANTITY_EXCEEDED"
            detail = f"quantity {intent.quantity} exceeds max {max_qty}"
        else:
            notional = intent.quantity * (intent.limit_price or 0)
            if intent.limit_price is not None and notional > max_notional:
                approved = False
                reason_code = "MAX_NOTIONAL_EXCEEDED"
                detail = f"notional {notional} exceeds max {max_notional}"

        decision = ExecutionDecision(
            intent_id=intent.intent_id,
            approved=approved,
            reason_code=reason_code,
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
