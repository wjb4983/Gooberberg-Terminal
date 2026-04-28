from app.domain.model_catalog.models import ModelCatalogEntry, ModelMetadata, ValidatorAdapterRef
from app.domain.model_registry import ModelRegistry


def bind_validator_adapters(
    metadata_entries: tuple[ModelMetadata, ...],
    model_registry: ModelRegistry,
) -> tuple[ModelCatalogEntry, ...]:
    translated: list[ModelCatalogEntry] = []
    for metadata in metadata_entries:
        model_registry.require(metadata.model_family)
        translated.append(
            ModelCatalogEntry(
                metadata=metadata,
                validator_adapter=ValidatorAdapterRef(model_family=metadata.model_family),
            )
        )
    return tuple(translated)
