"""Deterministic and time-aware dataset split helpers for training materialization."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import sqrt
from random import Random
from typing import Any


@dataclass(frozen=True, slots=True)
class SplitConfig:
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    seed: int = 7
    leakage_guard_key: str = "entity_id"


@dataclass(frozen=True, slots=True)
class DatasetSplit:
    train: tuple[dict[str, Any], ...]
    val: tuple[dict[str, Any], ...]
    test: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class WalkForwardWindow:
    train_start: int
    train_end: int
    test_start: int
    test_end: int


@dataclass(frozen=True, slots=True)
class WalkForwardSplitter:
    """Build expanding or rolling walk-forward windows."""

    train_size: int
    test_size: int
    step_size: int = 1
    expanding: bool = True

    def split(self, rows: list[dict[str, Any]], *, ts_key: str = "decision_ts") -> tuple[WalkForwardWindow, ...]:
        ordered = sorted(rows, key=lambda r: _read_int_ts(r, ts_key))
        if not ordered:
            return ()

        windows: list[WalkForwardWindow] = []
        train_anchor = _read_int_ts(ordered[0], ts_key)
        cursor = self.train_size
        while cursor + self.test_size <= len(ordered):
            train_slice = ordered[:cursor] if self.expanding else ordered[max(0, cursor - self.train_size) : cursor]
            test_slice = ordered[cursor : cursor + self.test_size]
            windows.append(
                WalkForwardWindow(
                    train_start=train_anchor if self.expanding else _read_int_ts(train_slice[0], ts_key),
                    train_end=_read_int_ts(train_slice[-1], ts_key),
                    test_start=_read_int_ts(test_slice[0], ts_key),
                    test_end=_read_int_ts(test_slice[-1], ts_key),
                )
            )
            cursor += self.step_size

        return tuple(windows)


@dataclass(frozen=True, slots=True)
class PurgedKFold:
    n_splits: int
    purge_horizon: int = 0
    embargo_period: int = 0

    def split(self, rows: list[dict[str, Any]], *, ts_key: str = "decision_ts") -> tuple[DatasetSplit, ...]:
        ordered = sorted(rows, key=lambda r: _read_int_ts(r, ts_key))
        n = len(ordered)
        if self.n_splits < 2:
            raise ValueError("n_splits must be >= 2")
        fold_size = max(1, n // self.n_splits)

        folds: list[DatasetSplit] = []
        for fold_idx in range(self.n_splits):
            start = fold_idx * fold_size
            end = n if fold_idx == self.n_splits - 1 else min(n, start + fold_size)
            test = ordered[start:end]
            if not test:
                continue
            test_start_ts = _read_int_ts(test[0], ts_key)
            test_end_ts = _read_int_ts(test[-1], ts_key)

            train: list[dict[str, Any]] = []
            for row in ordered:
                row_ts = _read_int_ts(row, ts_key)
                inside_test = test_start_ts <= row_ts <= test_end_ts
                purge_hit = (test_start_ts - self.purge_horizon) <= row_ts <= (test_end_ts + self.purge_horizon)
                embargo_hit = test_end_ts < row_ts <= (test_end_ts + self.embargo_period)
                if inside_test or purge_hit or embargo_hit:
                    continue
                train.append(row)
            folds.append(DatasetSplit(train=tuple(train), val=(), test=tuple(test)))
        return tuple(folds)


def enforce_feature_timing(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    """Require temporal metadata and filter rows with future-known features."""
    valid: list[dict[str, Any]] = []
    for row in rows:
        effective_from = row.get("effective_from_ts")
        known_at = row.get("known_at_ts")
        decision_ts = row.get("decision_ts")
        if effective_from is None or known_at is None:
            raise ValueError("feature metadata must include effective_from_ts and known_at_ts")
        if decision_ts is None:
            raise ValueError("row missing decision_ts")
        if _read_int_value(known_at) > _read_int_value(decision_ts):
            continue
        valid.append(row)
    return tuple(valid)


def leakage_diagnostics(rows: list[dict[str, Any]], *, label_key: str = "label") -> dict[str, Any]:
    if not rows:
        return {"future_value_correlation": 0.0, "shifted_feature_invariance": 0.0, "label_overlap_report": []}

    future_corr = _future_value_correlation(rows, label_key=label_key)
    shift_invariance = _shifted_feature_invariance(rows, label_key=label_key)

    overlap: list[dict[str, Any]] = []
    for fold in PurgedKFold(n_splits=3).split(rows):
        train_labels = {item.get(label_key) for item in fold.train}
        test_labels = {item.get(label_key) for item in fold.test}
        intersection = train_labels.intersection(test_labels)
        overlap.append({"overlap_count": len(intersection), "train_count": len(train_labels), "test_count": len(test_labels)})

    return {
        "future_value_correlation": future_corr,
        "shifted_feature_invariance": shift_invariance,
        "label_overlap_report": overlap,
    }


def persist_fold_metrics(metrics_by_fold: list[dict[str, Any]]) -> dict[str, Any]:
    total_weight = 0.0
    weighted_sum: dict[str, float] = {}
    for fold in metrics_by_fold:
        weight = float(fold.get("weight", 1.0))
        total_weight += weight
        for name, value in fold.get("metrics", {}).items():
            weighted_sum[name] = weighted_sum.get(name, 0.0) + float(value) * weight

    weighted_summary = {name: (value / total_weight if total_weight else 0.0) for name, value in weighted_sum.items()}
    ci = {
        name: _approx_confidence_interval([float(f.get("metrics", {}).get(name, 0.0)) for f in metrics_by_fold])
        for name in weighted_summary
    }
    return {
        "schema_version": "fold-metrics/v1",
        "folds": metrics_by_fold,
        "weighted_summary": weighted_summary,
        "confidence_intervals": ci,
    }


def _validate_ratios(cfg: SplitConfig) -> None:
    total = cfg.train_ratio + cfg.val_ratio + cfg.test_ratio
    if abs(total - 1.0) > 1e-9:
        raise ValueError("split ratios must sum to 1.0")


def split_qualified_rows(rows: list[dict[str, Any]], cfg: SplitConfig) -> DatasetSplit:
    """Split rows deterministically and guard against entity leakage across splits."""
    _validate_ratios(cfg)

    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        raw_key = row.get(cfg.leakage_guard_key)
        if raw_key is None:
            raise ValueError(f"missing leakage guard key: {cfg.leakage_guard_key}")
        groups.setdefault(str(raw_key), []).append(row)

    entities = list(groups)
    Random(cfg.seed).shuffle(entities)
    n = len(entities)
    train_n = int(n * cfg.train_ratio)
    val_n = int(n * cfg.val_ratio)

    train_entities = set(entities[:train_n])
    val_entities = set(entities[train_n : train_n + val_n])
    test_entities = set(entities[train_n + val_n :])

    train = tuple(item for entity in train_entities for item in groups[entity])
    val = tuple(item for entity in val_entities for item in groups[entity])
    test = tuple(item for entity in test_entities for item in groups[entity])
    return DatasetSplit(train=train, val=val, test=test)


def rows_checksum(rows: tuple[dict[str, Any], ...]) -> str:
    digest = sha256()
    for row in rows:
        digest.update(repr(sorted(row.items())).encode("utf-8"))
    return digest.hexdigest()


def _future_value_correlation(rows: list[dict[str, Any]], *, label_key: str) -> float:
    ordered = sorted(rows, key=lambda r: _read_int_ts(r, "decision_ts"))
    labels = [float(r.get(label_key, 0.0)) for r in ordered]
    future = labels[1:]
    current = labels[:-1]
    return _pearson(current, future) if current and future else 0.0


def _shifted_feature_invariance(rows: list[dict[str, Any]], *, label_key: str) -> float:
    ordered = sorted(rows, key=lambda r: _read_int_ts(r, "decision_ts"))
    labels = [float(r.get(label_key, 0.0)) for r in ordered]
    shifted = [float(r.get("feature_shifted", r.get("feature", 0.0))) for r in ordered]
    return abs(_pearson(labels, shifted))


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or not xs:
        return 0.0
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=False))
    den_x = sqrt(sum((x - mx) ** 2 for x in xs))
    den_y = sqrt(sum((y - my) ** 2 for y in ys))
    if den_x == 0.0 or den_y == 0.0:
        return 0.0
    return num / (den_x * den_y)


def _approx_confidence_interval(values: list[float]) -> dict[str, float]:
    if not values:
        return {"lower": 0.0, "upper": 0.0}
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    margin = 1.96 * sqrt(variance / max(1, len(values)))
    return {"lower": mean - margin, "upper": mean + margin}


def _read_int_ts(row: dict[str, Any], key: str) -> int:
    value = row.get(key)
    if value is None:
        raise ValueError(f"row missing {key}")
    return _read_int_value(value)


def _read_int_value(value: Any) -> int:
    return int(value)
