"""Data materialization for qualified datasets and split manifests."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
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

TOP_TIER0_SCHEMA_CONTRACTS: dict[str, dict[str, Any]] = {
    "dataset.ohlcv.adjusted": {
        "schema_version": 1,
        "required_columns": ["symbol", "timestamp", "open", "high", "low", "close", "volume"],
        "dtypes": {"symbol": "str", "timestamp": "datetime", "open": "float", "high": "float", "low": "float", "close": "float", "volume": "float"},
        "null_rate_thresholds": {"symbol": 0.0, "timestamp": 0.0, "open": 0.0, "high": 0.0, "low": 0.0, "close": 0.0, "volume": 0.0},
    },
    "ohlcv.close": {"schema_version": 1, "required_columns": ["symbol", "timestamp", "close"], "dtypes": {"symbol": "str", "timestamp": "datetime", "close": "float"}, "null_rate_thresholds": {"symbol": 0.0, "timestamp": 0.0, "close": 0.0}},
    "ohlcv.volume": {"schema_version": 1, "required_columns": ["symbol", "timestamp", "volume"], "dtypes": {"symbol": "str", "timestamp": "datetime", "volume": "float"}, "null_rate_thresholds": {"symbol": 0.0, "timestamp": 0.0, "volume": 0.0}},
    "dataset.returns.windowed": {"schema_version": 1, "required_columns": ["symbol", "timestamp", "return"], "dtypes": {"symbol": "str", "timestamp": "datetime", "return": "float"}, "null_rate_thresholds": {"symbol": 0.0, "timestamp": 0.0, "return": 0.0}},
    "returns.log": {"schema_version": 1, "required_columns": ["symbol", "timestamp", "log_return"], "dtypes": {"symbol": "str", "timestamp": "datetime", "log_return": "float"}, "null_rate_thresholds": {"symbol": 0.0, "timestamp": 0.0, "log_return": 0.0}},
}


def _write_validation_report(dataset_name: str, violations: list[str], rows: list[dict[str, Any]]) -> None:
    report_dir = Path("validation_reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    payload = {"dataset_name": dataset_name, "violations": violations, "row_count": len(rows)}
    report_path = report_dir / f"{dataset_name.replace('.', '_')}_violations.json"
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _validate_top_tier0_contract(intent: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    dataset_name = str(intent.get("dataset_name") or intent.get("dataset_ref") or "")
    contract = TOP_TIER0_SCHEMA_CONTRACTS.get(dataset_name)
    if not contract:
        return
    violations: list[str] = []
    required_columns = contract["required_columns"]
    dtypes = contract["dtypes"]
    null_thresholds = contract["null_rate_thresholds"]
    for col in required_columns:
        if any(col not in row for row in rows):
            violations.append(f"missing required column: {col}")
    for col, expected in dtypes.items():
        observed = [type(row.get(col)).__name__ for row in rows if col in row and row.get(col) is not None]
        if observed and any((x != expected and not (expected == "float" and x in {"int", "float"})) for x in observed):
            violations.append(f"dtype mismatch column={col} expected={expected} observed={sorted(set(observed))}")
    for col, threshold in null_thresholds.items():
        nulls = sum(1 for row in rows if row.get(col) is None)
        rate = (nulls / len(rows)) if rows else 0.0
        if rate > threshold:
            violations.append(f"null-rate breach column={col} rate={rate:.4f} threshold={threshold:.4f}")
    for symbol in {str(row.get('symbol')) for row in rows if row.get("symbol") is not None}:
        ts_values = [row.get("timestamp") for row in rows if str(row.get("symbol")) == symbol and row.get("timestamp") is not None]
        if ts_values != sorted(ts_values):
            violations.append(f"timestamp monotonicity breach symbol={symbol}")
    if violations:
        _write_validation_report(dataset_name, violations, rows)
        raise ValueError(f"schema contract break for {dataset_name}: {'; '.join(violations)}")


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
    _validate_top_tier0_contract(intent, rows)
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
