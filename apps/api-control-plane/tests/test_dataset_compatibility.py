from collections.abc import Mapping
from typing import Any

from app.domain.model_configs.compatibility import (
    DatasetRequirement,
    resolve_dataset_compatibility,
    validate_model_dataset_compatibility,
)


class _StubModelSpec:
    model_family = "demo"
    supported_data_kinds = ("time_series",)
    required_index = "datetime"
    target_type = "regression"
    dataset_requirement = DatasetRequirement(
        required_fields=("ohlcv.close", "timestamp"),
        required_frequency="1d",
        require_point_in_time_data=True,
    )

    def validate_config(self, config: Mapping[str, Any]) -> Mapping[str, Any]:
        return config


def test_validate_model_dataset_compatibility_accepts_ready_dataset() -> None:
    dataset = resolve_dataset_compatibility(
        {
            "data_kind": "time_series",
            "index_type": "datetime",
            "target_type": "regression",
            "fields": ["ohlcv.close", "timestamp", "volume"],
            "frequency": "1d",
            "point_in_time_ready": True,
        }
    )

    errors = validate_model_dataset_compatibility(model_spec=_StubModelSpec(), dataset_metadata=dataset)

    assert errors == []


def test_validate_model_dataset_compatibility_flags_required_field_frequency_and_pit() -> None:
    dataset = resolve_dataset_compatibility(
        {
            "data_kind": "time_series",
            "index_type": "datetime",
            "target_type": "regression",
            "fields": ["ohlcv.close"],
            "frequency": "1h",
            "point_in_time_ready": False,
        }
    )

    errors = validate_model_dataset_compatibility(model_spec=_StubModelSpec(), dataset_metadata=dataset)

    assert any("requires dataset fields" in error for error in errors)
    assert any("requires frequency=1d" in error for error in errors)
    assert any("requires point_in_time_ready=true" in error for error in errors)


def test_validate_model_dataset_compatibility_requires_field_metadata_when_missing() -> None:
    dataset = resolve_dataset_compatibility(
        {
            "data_kind": "time_series",
            "index_type": "datetime",
            "target_type": "regression",
            "frequency": "1d",
            "point_in_time_ready": True,
        }
    )

    errors = validate_model_dataset_compatibility(model_spec=_StubModelSpec(), dataset_metadata=dataset)

    assert any("set metadata.fields" in error for error in errors)
