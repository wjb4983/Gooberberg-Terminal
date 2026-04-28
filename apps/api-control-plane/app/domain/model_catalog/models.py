from dataclasses import dataclass, field
from enum import StrEnum


class ComputeIntensity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ModelMetadata:
    model_family: str
    model_name: str
    description: str
    required_data: tuple[str, ...]
    optional_data: tuple[str, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    leakage_risks: tuple[str, ...] = field(default_factory=tuple)
    failure_modes: tuple[str, ...] = field(default_factory=tuple)
    compute_intensity: ComputeIntensity = ComputeIntensity.MEDIUM
    output_schema: str = ""
    references: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ValidatorAdapterRef:
    model_family: str


@dataclass(frozen=True)
class ModelCatalogEntry:
    metadata: ModelMetadata
    validator_adapter: ValidatorAdapterRef
