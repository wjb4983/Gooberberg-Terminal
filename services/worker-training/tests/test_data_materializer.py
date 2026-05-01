from pathlib import Path

import pytest

from worker_training.data.materializer import materialize_dataset_bundle
from worker_training.data.splits import SplitConfig, split_qualified_rows


def _sample_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for entity_idx in range(12):
        for t in range(2):
            rows.append({"entity_id": f"asset-{entity_idx}", "timestamp": t})
    return rows


def test_split_determinism() -> None:
    intent = {"model_family": "baseline", "qualified_dataset_rows": _sample_rows()}
    first = materialize_dataset_bundle(intent, seed=77)
    second = materialize_dataset_bundle(intent, seed=77)

    assert first.split_manifest == second.split_manifest


def test_leakage_guard_keeps_entities_isolated() -> None:
    rows = _sample_rows()
    split = split_qualified_rows(rows, SplitConfig(seed=2, leakage_guard_key="entity_id"))

    train_entities = {row["entity_id"] for row in split.train}
    val_entities = {row["entity_id"] for row in split.val}
    test_entities = {row["entity_id"] for row in split.test}

    assert train_entities.isdisjoint(val_entities)
    assert train_entities.isdisjoint(test_entities)
    assert val_entities.isdisjoint(test_entities)


def test_tier0_contract_break_writes_validation_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    intent = {
        "model_family": "baseline",
        "dataset_name": "ohlcv.close",
        "qualified_dataset_rows": [{"symbol": "AAPL", "timestamp": None, "close": 1.0}],
    }
    with pytest.raises(ValueError, match="schema contract break"):
        materialize_dataset_bundle(intent, seed=1)
    report = tmp_path / "validation_reports" / "ohlcv_close_violations.json"
    assert report.exists()
