from datetime import UTC, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "gb_core" / "event_schemas.py"
SPEC = spec_from_file_location("event_schemas", MODULE_PATH)
assert SPEC and SPEC.loader
EVENT_SCHEMAS = module_from_spec(SPEC)
SPEC.loader.exec_module(EVENT_SCHEMAS)


def _base_payload() -> dict[str, object]:
    now = datetime(2026, 4, 30, tzinfo=UTC)
    return {
        "event_id": str(uuid4()),
        "trace_id": str(uuid4()),
        "schema_version": "1.0.0",
        "event_time": now.isoformat(),
        "ingest_time": now.isoformat(),
        "process_time": now.isoformat(),
        "producer": "strategy-engine",
        "strategy_version": "strat-v2",
        "config_hash": "cfg-123",
    }


def test_all_event_schema_definitions_exist() -> None:
    json_defs = EVENT_SCHEMAS.json_schema_definitions()
    avro_defs = EVENT_SCHEMAS.avro_schema_definitions()
    proto_defs = EVENT_SCHEMAS.protobuf_schema_definitions()

    assert set(json_defs) == set(EVENT_SCHEMAS.EVENT_MODELS)
    assert set(avro_defs) == set(EVENT_SCHEMAS.EVENT_MODELS)
    assert set(proto_defs) == set(EVENT_SCHEMAS.EVENT_MODELS)


def test_backward_forward_compatibility_with_optional_addition() -> None:
    base = _base_payload()
    payload = {
        **base,
        "event_type": "OrderIntentEvent",
        "intent_id": str(uuid4()),
        "symbol": "AAPL",
        "side": "buy",
        "quantity": 10,
        "limit_price": 123.45,
    }

    accepted = EVENT_SCHEMAS.validate_ingestion_payload("OrderIntentEvent", payload)
    assert accepted.symbol == "AAPL"

    forward_payload = {**payload, "new_optional_field": "future-compatible"}
    forward_accepted = EVENT_SCHEMAS.validate_ingestion_payload("OrderIntentEvent", forward_payload)
    assert forward_accepted.quantity == 10


def test_ingestion_boundary_rejects_invalid_payloads() -> None:
    base = _base_payload()
    invalid = {
        **base,
        "event_type": "FillEvent",
        "order_id": str(uuid4()),
        "fill_id": str(uuid4()),
        "symbol": "AAPL",
        "side": "buy",
        "quantity": -1,
        "price": 0,
    }

    with pytest.raises(ValidationError):
        EVENT_SCHEMAS.validate_ingestion_payload("FillEvent", invalid)


def test_common_fields_marked_required_in_json_schema() -> None:
    required = {
        "event_id",
        "trace_id",
        "schema_version",
        "event_type",
        "event_time",
        "ingest_time",
        "process_time",
        "producer",
        "strategy_version",
        "config_hash",
    }

    for name, schema in EVENT_SCHEMAS.json_schema_definitions().items():
        schema_required = set(schema.get("required", []))
        assert required.issubset(schema_required), name
