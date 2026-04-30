import json

import asyncio
from gb_core.schemas import StrategyIntent

from service_risk_exec.main import ServiceState, _consume_intent_payload


class FakeRedis:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    async def publish(self, channel: str, payload: str) -> None:
        self.published.append((channel, payload))


def test_consumer_processes_intent_and_publishes_decision() -> None:
    client = FakeRedis()
    state = ServiceState()
    payload = StrategyIntent(symbol="AAPL", quantity=10, confidence=0.8).model_dump_json()

    asyncio.run(_consume_intent_payload(client, payload, state))

    assert state.processed_intents == 1
    assert len(client.published) == 1
    _, decision_payload = client.published[0]
    parsed = json.loads(decision_payload)
    assert parsed["execution_status"] == "created"
    assert parsed["order_lifecycle"][-1] == "filled"
    assert parsed["risk_check_event"]["event_type"] == "RiskCheckEvent"
    assert parsed["risk_check_event"]["passed"] is True


def test_consumer_blocks_intent_and_emits_failure_reason_codes() -> None:
    client = FakeRedis()
    state = ServiceState()
    payload = StrategyIntent(symbol="AAPL", quantity=100_000, confidence=0.8).model_dump_json()

    asyncio.run(_consume_intent_payload(client, payload, state))

    _, decision_payload = client.published[0]
    parsed = json.loads(decision_payload)
    assert parsed["decision"]["approved"] is False
    assert "MAX_QUANTITY_EXCEEDED" in parsed["decision"]["failure_reason_codes"]
    assert "MAX_QUANTITY_EXCEEDED" in parsed["risk_check_event"]["failure_reason_codes"]
