import json
from pathlib import Path

import pytest

from app.schemas.model_catalog import ModelDefinition, parse_model_definitions


CATALOG_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "domain" / "model_catalog" / "catalog" / "default_models.json"
)


def test_model_definition_schema_validates_catalog_fixture_samples() -> None:
    payload = json.loads(CATALOG_FIXTURE_PATH.read_text(encoding="utf-8"))

    definitions = parse_model_definitions(payload)

    assert definitions
    assert all(isinstance(definition, ModelDefinition) for definition in definitions)
    assert all(definition.required_data for definition in definitions)


def test_model_definition_schema_rejects_empty_required_data() -> None:
    payload = {
        "model_family": "demo",
        "model_name": "Demo",
        "description": "x",
        "required_data": [],
        "output_schema": "schema.v1",
    }

    with pytest.raises(ValueError, match=r"required_data"):
        parse_model_definitions(payload)


def test_model_definition_schema_supports_dataset_requirement() -> None:
    payload = {
        "model_family": "demo",
        "model_name": "Demo",
        "description": "x",
        "required_data": ["ohlcv.close"],
        "dataset_requirement": {
            "required_fields": ["ohlcv.close", "timestamp"],
            "required_frequency": "1d",
            "require_point_in_time_data": True,
        },
        "output_schema": "schema.v1",
    }

    definition = parse_model_definitions(payload)[0]

    assert definition.dataset_requirement.required_fields == ["ohlcv.close", "timestamp"]
    assert definition.dataset_requirement.required_frequency == "1d"
    assert definition.dataset_requirement.require_point_in_time_data is True
