import json
from pathlib import Path
from typing import Any

from app.domain.model_catalog.models import ModelMetadata


def load_model_metadata_from_directory(directory: Path) -> tuple[ModelMetadata, ...]:
    entries: list[ModelMetadata] = []
    for path in sorted(directory.glob("*")):
        if path.suffix.lower() not in {".json", ".yaml", ".yml"}:
            continue
        entries.extend(_load_metadata_file(path))
    return tuple(entries)


def _load_metadata_file(path: Path) -> tuple[ModelMetadata, ...]:
    payload = _parse_file(path)
    raw_entries = payload if isinstance(payload, list) else [payload]
    normalized: list[ModelMetadata] = []

    for item in raw_entries:
        if not isinstance(item, dict):
            raise ValueError(f"catalog item must be an object in {path}")
        model_family = _require_str(item, "model_family", path)
        model_name = _require_str(item, "model_name", path)
        description = _require_str(item, "description", path)
        raw_tags = item.get("tags", [])
        if not isinstance(raw_tags, list) or not all(isinstance(tag, str) for tag in raw_tags):
            raise ValueError(f"tags must be an array of strings in {path}")

        normalized.append(
            ModelMetadata(
                model_family=model_family,
                model_name=model_name,
                description=description,
                tags=tuple(raw_tags),
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


def _require_str(payload: dict[str, Any], key: str, path: Path) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string in {path}")
    return value
