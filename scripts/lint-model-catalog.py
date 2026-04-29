#!/usr/bin/env python3
"""Validate model catalog YAML entries for basic integrity checks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

REQUIRED_FIELDS = ("id", "slug", "model_family", "model_name", "description", "warnings", "references")
PLACEHOLDER_TOKENS = ("TODO", "TBD", "REPLACE_ME", "<placeholder>", "placeholder", "{{", "}}", "${")


def _contains_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(token.lower() in lowered for token in PLACEHOLDER_TOKENS)


def _entry_label(file_path: Path, model_id: str) -> str:
    return f"{file_path}: model id '{model_id}'"


def lint_catalog_file(file_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        payload = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"{file_path}: invalid YAML: {exc}"]

    if not isinstance(payload, list):
        return [f"{file_path}: expected top-level list of models"]

    seen_ids: set[str] = set()
    seen_slugs: set[str] = set()

    for idx, entry in enumerate(payload):
        if not isinstance(entry, dict):
            errors.append(f"{file_path}: entry index {idx} must be a mapping")
            continue

        model_id = str(entry.get("id", f"<missing id at index {idx}>"))
        label = _entry_label(file_path, model_id)

        for field in REQUIRED_FIELDS:
            if field not in entry:
                errors.append(f"{label}: missing required field '{field}'")

        model_slug = entry.get("slug")
        if isinstance(model_slug, str):
            if model_slug in seen_slugs:
                errors.append(f"{label}: duplicate slug '{model_slug}'")
            seen_slugs.add(model_slug)

        if isinstance(model_id, str):
            if model_id in seen_ids:
                errors.append(f"{label}: duplicate id '{model_id}'")
            seen_ids.add(model_id)

        warnings = entry.get("warnings")
        if "warnings" in entry and (not isinstance(warnings, list) or len(warnings) == 0):
            errors.append(f"{label}: warnings must be a non-empty list")

        references = entry.get("references")
        if isinstance(references, list):
            for ref in references:
                if isinstance(ref, str) and _contains_placeholder(ref):
                    errors.append(f"{label}: unresolved reference placeholder '{ref}'")

    return errors


def lint_catalog_directory(catalog_dir: Path) -> list[str]:
    errors: list[str] = []
    for file_path in sorted(catalog_dir.glob("*.yaml")):
        errors.extend(lint_catalog_file(file_path))
    if not list(catalog_dir.glob("*.yaml")):
        errors.append(f"{catalog_dir}: no catalog yaml files found")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint model catalog yaml files")
    parser.add_argument(
        "catalog_dir",
        nargs="?",
        default=Path(__file__).resolve().parents[1] / "config" / "models" / "catalog",
        type=Path,
        help="Directory containing model catalog YAML files",
    )
    args = parser.parse_args()

    errors = lint_catalog_directory(args.catalog_dir)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"OK: validated model catalog in {args.catalog_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
