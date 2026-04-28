from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from app.domain.model_catalog.models import ComputeIntensity

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DatasetRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_fields: list[NonEmptyString] = Field(default_factory=list)
    required_frequency: NonEmptyString | None = None
    require_point_in_time_data: bool = False


class ModelDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_family: NonEmptyString
    model_name: NonEmptyString
    description: NonEmptyString
    required_data: list[NonEmptyString] = Field(min_length=1)
    dataset_requirement: DatasetRequirement = Field(default_factory=DatasetRequirement)
    optional_data: list[NonEmptyString] = Field(default_factory=list)
    tags: list[NonEmptyString] = Field(default_factory=list)
    leakage_risks: list[NonEmptyString] = Field(default_factory=list)
    failure_modes: list[NonEmptyString] = Field(default_factory=list)
    compute_intensity: ComputeIntensity = ComputeIntensity.MEDIUM
    output_schema: NonEmptyString
    references: list[NonEmptyString] = Field(default_factory=list)


def parse_model_definitions(payload: Any) -> tuple[ModelDefinition, ...]:
    if isinstance(payload, dict):
        raw_entries = [payload]
    elif isinstance(payload, list):
        raw_entries = payload
    else:
        raise ValueError("catalog payload must be an object or array of objects")

    definitions: list[ModelDefinition] = []
    for index, item in enumerate(raw_entries):
        if not isinstance(item, dict):
            raise ValueError(f"catalog item at index {index} must be an object")

        try:
            definitions.append(ModelDefinition.model_validate(item))
        except ValidationError as exc:
            raise ValueError(f"item index {index} failed schema validation: {exc}") from exc

    return tuple(definitions)
