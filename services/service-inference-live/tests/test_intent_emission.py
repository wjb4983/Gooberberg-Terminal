from uuid import uuid4

from service_inference_live.main import _build_mock_intent


def test_mock_intent_contains_trace_and_confidence() -> None:
    intent = _build_mock_intent(strategy_instance_id=uuid4(), seq=3)

    assert intent.trace_id is not None
    assert 0 <= intent.confidence <= 1
    assert "execution delegated" in (intent.notes or "")
