from __future__ import annotations

from random import Random
from typing import Any

REQUIRED_METADATA_FIELDS: tuple[str, ...] = (
    "hypothesis_id",
    "dataset_snapshot_id",
    "code_commit_hash",
    "parameter_set_id",
    "random_seed",
    "cost_model_version",
)


def run_metadata_template(*, as_json_schema: bool = False) -> dict[str, Any]:
    """Return a lightweight run metadata payload template stored with every run."""
    if as_json_schema:
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": list(REQUIRED_METADATA_FIELDS),
            "properties": {key: {"type": "string"} for key in REQUIRED_METADATA_FIELDS if key != "random_seed"}
            | {"random_seed": {"type": "integer"}},
            "additionalProperties": True,
        }
    return {
        "hypothesis_id": "hyp-<id>",
        "dataset_snapshot_id": "ds-<snapshot-id>",
        "code_commit_hash": "<git-sha>",
        "parameter_set_id": "ps-<id>",
        "random_seed": 0,
        "cost_model_version": "v1",
    }


def missing_required_metadata(metadata: dict[str, Any] | None) -> list[str]:
    payload = metadata or {}
    missing: list[str] = []
    for field in REQUIRED_METADATA_FIELDS:
        value = payload.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    return missing


def can_label_final_candidate(metadata: dict[str, Any] | None) -> bool:
    return not missing_required_metadata(metadata)


def weekly_audit_sample(run_ids: list[str], *, sample_size: int = 5, seed: int | None = None) -> list[str]:
    if sample_size <= 0 or not run_ids:
        return []
    if len(run_ids) <= sample_size:
        return list(run_ids)
    rng = Random(seed)
    return rng.sample(run_ids, sample_size)
