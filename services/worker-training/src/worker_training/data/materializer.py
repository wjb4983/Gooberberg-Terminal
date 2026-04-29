"""Data materialization for qualified datasets and split manifests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from worker_training.data.splits import SplitConfig, split_qualified_rows, rows_checksum


DEFAULT_VALIDATION_PROFILES: dict[str, dict[str, Any]] = {
    "baseline": {"train_ratio": 0.7, "val_ratio": 0.15, "test_ratio": 0.15, "leakage_guard_key": "entity_id"},
    "alpha": {"train_ratio": 0.65, "val_ratio": 0.2, "test_ratio": 0.15, "leakage_guard_key": "entity_id"},
    "ml": {"train_ratio": 0.8, "val_ratio": 0.1, "test_ratio": 0.1, "leakage_guard_key": "entity_id"},
}


@dataclass(frozen=True, slots=True)
class MaterializedDatasetBundle:
    family: str
    validation_profile: str
    split_manifest: dict[str, Any]


def materialize_dataset_bundle(intent: dict[str, Any], *, seed: int) -> MaterializedDatasetBundle:
    family = str(intent.get("model_family") or "baseline")
    normalized_family = family if family in DEFAULT_VALIDATION_PROFILES else "ml"
    profile_name = str(intent.get("validation_profile") or normalized_family)

    profile_payload = DEFAULT_VALIDATION_PROFILES.get(profile_name, DEFAULT_VALIDATION_PROFILES[normalized_family])
    config = SplitConfig(
        train_ratio=float(profile_payload["train_ratio"]),
        val_ratio=float(profile_payload["val_ratio"]),
        test_ratio=float(profile_payload["test_ratio"]),
        seed=seed,
        leakage_guard_key=str(profile_payload["leakage_guard_key"]),
    )

    qualified_rows = intent.get("qualified_dataset_rows")
    rows = [r for r in qualified_rows if isinstance(r, dict)] if isinstance(qualified_rows, list) else []
    if not rows:
        rows = [
            {"entity_id": f"{intent.get('dataset_ref', 'dataset')}::{idx}", "position": idx}
            for idx in range(10)
        ]

    splits = split_qualified_rows(rows, config)
    manifest = {
        "profile": profile_name,
        "seed": seed,
        "leakage_guard_key": config.leakage_guard_key,
        "counts": {"train": len(splits.train), "val": len(splits.val), "test": len(splits.test)},
        "checksums": {
            "train": rows_checksum(splits.train),
            "val": rows_checksum(splits.val),
            "test": rows_checksum(splits.test),
        },
    }
    return MaterializedDatasetBundle(family=family, validation_profile=profile_name, split_manifest=manifest)
