from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.domain.model_registry import ModelSpec


@dataclass(frozen=True)
class DatasetCompatibilityMetadata:
    data_kind: str | None
    index_type: str | None
    target_type: str | None
    available_fields: frozenset[str]
    frequency: str | None
    point_in_time_ready: bool | None


@dataclass(frozen=True)
class DatasetRequirement:
    required_fields: tuple[str, ...] = ()
    required_frequency: str | None = None
    require_point_in_time_data: bool = False


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
    available_fields = _as_string_set(
        metadata.get("fields") or metadata.get("available_fields") or metadata.get("columns")
    )
    frequency = _as_string(metadata.get("frequency")) or _as_string(timeframe)
    point_in_time_ready = _as_bool(
        metadata.get("point_in_time_ready")
        if "point_in_time_ready" in metadata
        else metadata.get("pit_ready")
    )

    return DatasetCompatibilityMetadata(
        data_kind=data_kind,
        index_type=index_type,
        target_type=target_type,
        available_fields=available_fields,
        frequency=frequency,
        point_in_time_ready=point_in_time_ready,
    )


def validate_model_dataset_compatibility(
    *,
    model_spec: ModelSpec,
    dataset_metadata: DatasetCompatibilityMetadata,
) -> list[str]:
    errors: list[str] = []
    requirement = _resolve_dataset_requirement(model_spec)

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

    if requirement.required_fields:
        missing_fields = tuple(
            field
            for field in requirement.required_fields
            if field not in dataset_metadata.available_fields
        )
        if missing_fields:
            if dataset_metadata.available_fields:
                errors.append(
                    f"model_family={model_spec.model_family} requires dataset fields {list(missing_fields)}, but dataset fields are {sorted(dataset_metadata.available_fields)}"
                )
            else:
                errors.append(
                    f"model_family={model_spec.model_family} requires dataset fields {list(missing_fields)}; set metadata.fields"
                )

    if requirement.required_frequency is not None:
        if dataset_metadata.frequency is None:
            errors.append(
                f"model_family={model_spec.model_family} requires frequency={requirement.required_frequency}; set metadata.frequency"
            )
        elif dataset_metadata.frequency != requirement.required_frequency:
            errors.append(
                f"model_family={model_spec.model_family} requires frequency={requirement.required_frequency}, but dataset has frequency={dataset_metadata.frequency}"
            )

    if requirement.require_point_in_time_data and dataset_metadata.point_in_time_ready is not True:
        errors.append(
            f"model_family={model_spec.model_family} requires point_in_time_ready=true; set metadata.point_in_time_ready"
        )

    return errors


def _as_string(value: Any) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    return None


def _as_string_set(value: Any) -> frozenset[str]:
    if not isinstance(value, list):
        return frozenset()
    normalized: set[str] = set()
    for item in value:
        parsed = _as_string(item)
        if parsed is not None:
            normalized.add(parsed)
    return frozenset(normalized)


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _resolve_dataset_requirement(model_spec: ModelSpec) -> DatasetRequirement:
    raw = getattr(model_spec, "dataset_requirement", None)
    if isinstance(raw, DatasetRequirement):
        return raw
    if isinstance(raw, Mapping):
        required_fields = tuple(
            normalized
            for item in raw.get("required_fields", ())
            if (normalized := _as_string(item)) is not None
        )
        return DatasetRequirement(
            required_fields=required_fields,
            required_frequency=_as_string(raw.get("required_frequency")),
            require_point_in_time_data=bool(raw.get("require_point_in_time_data", False)),
        )
    return DatasetRequirement()
