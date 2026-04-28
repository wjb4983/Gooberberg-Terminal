import json
from pathlib import Path
from typing import Any

from app.domain.model_catalog.models import ComputeIntensity, ModelMetadata


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
    raw_entries = payload if isinstance(payload, list) else [payload]
    normalized: list[ModelMetadata] = []

    for index, item in enumerate(raw_entries):
        if not isinstance(item, dict):
            raise ValueError(f"catalog item at index {index} must be an object in {path}")

        model_family = _require_str(item, "model_family", path, index)
        model_name = _require_str(item, "model_name", path, index)
        description = _require_str(item, "description", path, index)
        required_data = _require_str_array(item, "required_data", path, index, required=True)
        optional_data = _require_str_array(item, "optional_data", path, index)
        tags = _require_str_array(item, "tags", path, index)
        leakage_risks = _require_str_array(item, "leakage_risks", path, index)
        failure_modes = _require_str_array(item, "failure_modes", path, index)
        output_schema = _require_str(item, "output_schema", path, index)
        references = _require_str_array(item, "references", path, index)

        raw_intensity = item.get("compute_intensity", ComputeIntensity.MEDIUM.value)
        try:
            compute_intensity = ComputeIntensity(raw_intensity)
        except ValueError as exc:
            raise ValueError(
                f"compute_intensity must be one of {[value.value for value in ComputeIntensity]} "
                f"in {path} (item index {index})"
            ) from exc

        normalized.append(
            ModelMetadata(
                model_family=model_family,
                model_name=model_name,
                description=description,
                required_data=tuple(required_data),
                optional_data=tuple(optional_data),
                tags=tuple(tags),
                leakage_risks=tuple(leakage_risks),
                failure_modes=tuple(failure_modes),
                compute_intensity=compute_intensity,
                output_schema=output_schema,
                references=tuple(references),
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


def _require_str(payload: dict[str, Any], key: str, path: Path, index: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string in {path} (item index {index})")
    return value


def _require_str_array(
    payload: dict[str, Any],
    key: str,
    path: Path,
    index: int,
    *,
    required: bool = False,
) -> list[str]:
    value = payload.get(key)
    if value is None:
        if required:
            raise ValueError(f"{key} is required in {path} (item index {index})")
        return []

    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(
            f"{key} must be an array of non-empty strings in {path} (item index {index})"
        )
    return value
