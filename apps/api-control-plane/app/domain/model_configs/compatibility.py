from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.domain.model_registry import ModelSpec


@dataclass(frozen=True)
class DatasetCompatibilityMetadata:
    data_kind: str | None
    index_type: str | None
    target_type: str | None


def resolve_dataset_compatibility(
    metadata: Mapping[str, Any], timeframe: str | None = None
) -> DatasetCompatibilityMetadata:
    data_kind = _as_string(metadata.get("data_kind"))
    index_type = _as_string(metadata.get("index_type"))
    target_type = _as_string(metadata.get("target_type"))

    if data_kind is None and timeframe:
        data_kind = "time_series"
    if index_type is None and data_kind == "time_series":
        index_type = "datetime"

    return DatasetCompatibilityMetadata(
        data_kind=data_kind, index_type=index_type, target_type=target_type
    )


def validate_model_dataset_compatibility(
    *,
    model_spec: ModelSpec,
    dataset_metadata: DatasetCompatibilityMetadata,
) -> list[str]:
    errors: list[str] = []

    if dataset_metadata.data_kind is None:
        errors.append(
            "dataset metadata is missing data_kind; set metadata.data_kind (for example: time_series, tabular, or image)"
        )
    elif dataset_metadata.data_kind not in model_spec.supported_data_kinds:
        supported = ", ".join(model_spec.supported_data_kinds)
        errors.append(
            f"model_family={model_spec.model_family} supports data_kind in [{supported}], but dataset has data_kind={dataset_metadata.data_kind}"
        )

    if model_spec.required_index is not None:
        if dataset_metadata.index_type is None:
            errors.append(
                f"model_family={model_spec.model_family} requires index_type={model_spec.required_index}; set metadata.index_type"
            )
        elif dataset_metadata.index_type != model_spec.required_index:
            errors.append(
                f"model_family={model_spec.model_family} requires index_type={model_spec.required_index}, but dataset has index_type={dataset_metadata.index_type}"
            )

    if model_spec.target_type is not None and dataset_metadata.target_type is not None:
        if dataset_metadata.target_type != model_spec.target_type:
            errors.append(
                f"model_family={model_spec.model_family} requires target_type={model_spec.target_type}, but dataset has target_type={dataset_metadata.target_type}"
            )

    return errors


def _as_string(value: Any) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    return None
