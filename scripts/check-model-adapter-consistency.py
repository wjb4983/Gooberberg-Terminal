#!/usr/bin/env python3
"""Check consistency between catalog implementation status and adapter coverage."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG_DIR = REPO_ROOT / "config" / "models" / "catalog"
DEFAULT_ADAPTER_DIR = REPO_ROOT / "services" / "service-data" / "src" / "service_data" / "market_data" / "providers"


def _load_catalog_model_ids(catalog_dir: Path) -> tuple[set[str], list[str]]:
    implemented_model_ids: set[str] = set()
    all_model_ids: set[str] = set()
    errors: list[str] = []

    for file_path in sorted(catalog_dir.glob("phase[1-3].yaml")):
        try:
            payload = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{file_path}: invalid YAML: {exc}")
            continue

        if not isinstance(payload, list):
            errors.append(f"{file_path}: expected top-level list of models")
            continue

        for entry in payload:
            if not isinstance(entry, dict):
                continue
            model_id = entry.get("id")
            if not isinstance(model_id, str):
                continue
            all_model_ids.add(model_id)
            if entry.get("implementation_status") == "implemented":
                implemented_model_ids.add(model_id)

    return implemented_model_ids, sorted(all_model_ids), errors


def _discover_adapter_ids(adapter_dir: Path) -> set[str]:
    adapter_ids: set[str] = set()
    for adapter_path in sorted(adapter_dir.glob("*_adapter.py")):
        adapter_ids.add(adapter_path.stem[: -len("_adapter")])
    return adapter_ids


def check_consistency(catalog_implemented_ids: set[str], catalog_all_ids: set[str], adapter_ids: set[str]) -> list[str]:
    errors: list[str] = []

    missing_adapter_ids = sorted(catalog_implemented_ids - adapter_ids)
    for model_id in missing_adapter_ids:
        errors.append(
            "catalog model marked implemented is missing adapter: "
            f"model_id='{model_id}'"
        )

    missing_catalog_ids = sorted(adapter_ids - catalog_all_ids)
    for model_id in missing_catalog_ids:
        errors.append(
            "adapter exists without catalog entry: "
            f"model_id='{model_id}'"
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-dir", type=Path, default=DEFAULT_CATALOG_DIR)
    parser.add_argument("--adapter-dir", type=Path, default=DEFAULT_ADAPTER_DIR)
    args = parser.parse_args()

    catalog_implemented_ids, catalog_all_ids_list, load_errors = _load_catalog_model_ids(args.catalog_dir)
    adapter_ids = _discover_adapter_ids(args.adapter_dir)
    errors = [*load_errors, *check_consistency(catalog_implemented_ids, set(catalog_all_ids_list), adapter_ids)]

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "OK: model adapter consistency checks passed "
        f"(implemented={len(catalog_implemented_ids)}, adapters={len(adapter_ids)})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
