from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)

from app.domain.model_catalog.models import ComputeIntensity

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DatasetRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_fields: list[NonEmptyString] = Field(default_factory=list)
    required_frequency: NonEmptyString | None = None
    require_point_in_time_data: bool = False


class NumericRangeBounds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_value: float | None = None
    max_value: float | None = None
    min_inclusive: bool = True
    max_inclusive: bool = True

    @model_validator(mode="after")
    def validate_bounds(self) -> "NumericRangeBounds":
        if self.min_value is not None and self.max_value is not None and self.min_value > self.max_value:
            raise ValueError("min_value cannot be greater than max_value")
        return self


class ParameterDefinitionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: NonEmptyString
    description: NonEmptyString
    advanced: bool = False
    conditional_flag: NonEmptyString | None = None


class NumericParameterDefinition(ParameterDefinitionBase):
    type: Literal["integer", "number"]
    default: int | float
    bounds: NumericRangeBounds | None = None

    @model_validator(mode="after")
    def validate_default_within_bounds(self) -> "NumericParameterDefinition":
        if self.type == "integer" and not isinstance(self.default, int):
            raise ValueError("default must be an integer when type is integer")
        if self.bounds is None:
            return self

        if self.bounds.min_value is not None:
            if self.bounds.min_inclusive and self.default < self.bounds.min_value:
                raise ValueError("default is below minimum bound")
            if not self.bounds.min_inclusive and self.default <= self.bounds.min_value:
                raise ValueError("default must be greater than minimum bound")
        if self.bounds.max_value is not None:
            if self.bounds.max_inclusive and self.default > self.bounds.max_value:
                raise ValueError("default is above maximum bound")
            if not self.bounds.max_inclusive and self.default >= self.bounds.max_value:
                raise ValueError("default must be less than maximum bound")
        return self


class EnumParameterDefinition(ParameterDefinitionBase):
    type: Literal["enum"]
    default: NonEmptyString
    allowed_values: list[NonEmptyString] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_default(self) -> "EnumParameterDefinition":
        if self.default not in self.allowed_values:
            raise ValueError("default must be one of allowed_values")
        return self


ParameterDefinition = Annotated[
    NumericParameterDefinition | EnumParameterDefinition,
    Field(discriminator="type"),
]


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
    params: list[ParameterDefinition] = Field(default_factory=list)


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
