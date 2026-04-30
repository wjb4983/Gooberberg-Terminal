from worker_training.data.splits import (
    PurgedKFold,
    WalkForwardSplitter,
    enforce_feature_timing,
    leakage_diagnostics,
    persist_fold_metrics,
)


def _rows() -> list[dict[str, object]]:
    return [
        {
            "entity_id": f"e{i}",
            "decision_ts": i,
            "effective_from_ts": i,
            "known_at_ts": i,
            "label": float(i % 3),
            "feature": float(i),
            "feature_shifted": float(i) + 0.1,
        }
        for i in range(12)
    ]


def test_walk_forward_expanding_and_rolling() -> None:
    rows = _rows()
    expanding = WalkForwardSplitter(train_size=4, test_size=2, step_size=2, expanding=True).split(rows)
    rolling = WalkForwardSplitter(train_size=4, test_size=2, step_size=2, expanding=False).split(rows)

    assert expanding[0].train_start == 0
    assert expanding[0].train_end == 3
    assert expanding[0].test_start == 4
    assert rolling[1].train_start == 2


def test_purged_kfold_respects_purge_and_embargo() -> None:
    folds = PurgedKFold(n_splits=3, purge_horizon=1, embargo_period=1).split(_rows())
    assert len(folds) == 3
    for fold in folds:
        test_ts = {int(row["decision_ts"]) for row in fold.test}
        for train_row in fold.train:
            assert int(train_row["decision_ts"]) not in test_ts


def test_feature_timing_blocks_future_known_rows() -> None:
    rows = _rows()
    rows[3]["known_at_ts"] = 99
    filtered = enforce_feature_timing(rows)
    assert len(filtered) == len(rows) - 1


def test_leakage_diagnostics_and_fold_metrics() -> None:
    rows = _rows()
    diagnostics = leakage_diagnostics(rows)
    assert "future_value_correlation" in diagnostics
    assert "label_overlap_report" in diagnostics

    metrics = persist_fold_metrics(
        [
            {"fold": 0, "weight": 10, "metrics": {"rmse": 0.4, "mae": 0.2}},
            {"fold": 1, "weight": 5, "metrics": {"rmse": 0.6, "mae": 0.3}},
        ]
    )
    assert metrics["weighted_summary"]["rmse"] > 0
    assert "rmse" in metrics["confidence_intervals"]
