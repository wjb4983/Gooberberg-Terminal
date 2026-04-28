import json
from pathlib import Path
from typing import Any

from app.domain.model_catalog.models import ModelMetadata
from app.schemas.model_catalog import parse_model_definitions


def load_model_metadata_from_directory(directory: Path) -> tuple[ModelMetadata, ...]:
    entries: list[ModelMetadata] = []
    seen_families: dict[str, Path] = {}
    for path in sorted(directory.glob("*")):
        if path.suffix.lower() not in {".json", ".yaml", ".yml"}:
            continue

        for entry in _load_metadata_file(path):
            original_path = seen_families.get(entry.model_family)
            if original_path is not None:
                raise ValueError(
                    f"duplicate model_family '{entry.model_family}' found in {path}; first declared in {original_path}"
                )
            seen_families[entry.model_family] = path
            entries.append(entry)

    return tuple(entries)


def _load_metadata_file(path: Path) -> tuple[ModelMetadata, ...]:
    payload = _parse_file(path)

    try:
        definitions = parse_model_definitions(payload)
    except ValueError as exc:
        raise ValueError(f"{exc} in {path}") from exc

    normalized: list[ModelMetadata] = []
    for definition in definitions:
        normalized.append(
            ModelMetadata(
                model_family=definition.model_family,
                model_name=definition.model_name,
                description=definition.description,
                required_data=tuple(definition.required_data),
                optional_data=tuple(definition.optional_data),
                tags=tuple(definition.tags),
                leakage_risks=tuple(definition.leakage_risks),
                failure_modes=tuple(definition.failure_modes),
                compute_intensity=definition.compute_intensity,
                output_schema=definition.output_schema,
                references=tuple(definition.references),
            )
        )

    return tuple(normalized)


def _parse_file(path: Path) -> Any:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(raw)

    try:
        import yaml  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"YAML file {path} was provided but PyYAML is not installed; use JSON or install PyYAML"
        ) from exc

    return yaml.safe_load(raw)
