from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelMetadata:
    model_family: str
    model_name: str
    description: str
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ValidatorAdapterRef:
    model_family: str


@dataclass(frozen=True)
class ModelCatalogEntry:
    metadata: ModelMetadata
    validator_adapter: ValidatorAdapterRef

