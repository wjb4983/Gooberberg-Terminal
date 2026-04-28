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
