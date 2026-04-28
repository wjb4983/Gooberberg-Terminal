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


@pytest.mark.parametrize(
    ("params", "expected_error"),
    [
        pytest.param(
            [
                {
                    "name": "lookback",
                    "description": "Lookback window",
                    "type": "integer",
                    "default": 20,
                    "bounds": {"min_value": 5, "max_value": 200},
                }
            ],
            None,
            id="numeric-range-valid",
        ),
        pytest.param(
            [
                {
                    "name": "lookback",
                    "description": "Lookback window",
                    "type": "integer",
                    "default": 2,
                    "bounds": {"min_value": 5, "max_value": 200},
                }
            ],
            "below minimum bound",
            id="numeric-range-default-outside-bounds",
        ),
        pytest.param(
            [
                {
                    "name": "vol_target",
                    "description": "Volatility target",
                    "type": "number",
                    "default": 0.1,
                    "bounds": {"min_value": 0.0, "max_value": 1.0},
                    "advanced": True,
                    "conditional_flag": "enable_risk_targeting",
                }
            ],
            None,
            id="advanced-conditional-flag-valid",
        ),
        pytest.param(
            [
                {
                    "name": "regime",
                    "description": "Regime selector",
                    "type": "enum",
                    "default": "trend",
                    "allowed_values": ["trend", "mean_reversion"],
                }
            ],
            None,
            id="enum-valid",
        ),
        pytest.param(
            [
                {
                    "name": "regime",
                    "description": "Regime selector",
                    "type": "enum",
                    "default": "carry",
                    "allowed_values": ["trend", "mean_reversion"],
                }
            ],
            "allowed_values",
            id="enum-default-not-allowed",
        ),
    ],
)
def test_model_definition_schema_parameter_validation_matrix(
    params: list[dict[str, object]],
    expected_error: str | None,
) -> None:
    payload = {
        "model_family": "demo",
        "model_name": "Demo",
        "description": "x",
        "required_data": ["ohlcv.close"],
        "output_schema": "schema.v1",
        "params": params,
    }

    if expected_error is None:
        definition = parse_model_definitions(payload)[0]
        assert len(definition.params) == len(params)
        return

    with pytest.raises(ValueError, match=expected_error):
        parse_model_definitions(payload)
