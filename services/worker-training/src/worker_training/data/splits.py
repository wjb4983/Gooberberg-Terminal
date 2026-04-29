"""Deterministic dataset split helpers for training materialization."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
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
