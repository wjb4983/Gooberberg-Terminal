from app.domain.model_configs.compatibility import DatasetRequirement, resolve_dataset_compatibility
from app.domain.training_runs.dataset_qualification import QualificationContext, qualify_dataset_for_training


def test_qualification_reports_missing_fields_and_history_window() -> None:
    context = QualificationContext(
        task_type="cross_sectional",
        subtask_type="ranking",
        model_family="torch_nn_timeseries",
        model_config={"lookback_window": 100, "horizon_steps": 5},
    )
    dataset_profile = resolve_dataset_compatibility(
        {
            "data_kind": "time_series",
            "index_type": "datetime",
            "target_type": "regression",
            "fields": ["timestamp", "ohlcv.close"],
            "frequency": "1d",
            "point_in_time_ready": True,
        }
    )

    result = qualify_dataset_for_training(
        context=context,
        dataset_metadata=dataset_profile,
        dataset_requirement=DatasetRequirement(required_fields=("entity_id",)),
        raw_dataset_metadata={"history_window_steps": 50, "asset_universe_size": 10},
    )

    assert any(issue.code == "missing_fields" for issue in result.errors)
    assert any(issue.code == "insufficient_history_window" for issue in result.errors)


def test_qualification_enforces_point_in_time_and_multi_asset_universe() -> None:
    context = QualificationContext(
        task_type="cross_sectional",
        subtask_type="allocation",
        model_family="arima",
        model_config={"p": 1, "d": 1, "q": 0},
    )
    dataset_profile = resolve_dataset_compatibility(
        {
            "data_kind": "time_series",
            "index_type": "datetime",
            "target_type": "regression",
            "fields": ["entity_id", "timestamp", "ohlcv.close"],
            "frequency": "1d",
            "point_in_time_ready": False,
        }
    )

    result = qualify_dataset_for_training(
        context=context,
        dataset_metadata=dataset_profile,
        dataset_requirement=DatasetRequirement(require_point_in_time_data=True),
        raw_dataset_metadata={"history_window_steps": 200, "asset_universe_size": 1},
    )

    assert any(issue.code == "point_in_time_required" for issue in result.errors)
    assert any(issue.code == "insufficient_asset_universe" for issue in result.errors)


def test_qualification_warns_when_history_and_universe_metadata_are_missing() -> None:
    context = QualificationContext(
        task_type="cross_sectional",
        subtask_type="return_forecast",
        model_family="hmm_regime_switching",
        model_config={},
    )
    dataset_profile = resolve_dataset_compatibility(
        {
            "data_kind": "time_series",
            "index_type": "datetime",
            "target_type": "classification",
            "fields": ["entity_id", "timestamp", "returns.log"],
            "frequency": "1d",
            "point_in_time_ready": True,
        }
    )

    result = qualify_dataset_for_training(
        context=context,
        dataset_metadata=dataset_profile,
        dataset_requirement=DatasetRequirement(),
        raw_dataset_metadata={},
    )

    assert result.errors == ()
    assert any(issue.code == "missing_history_window" for issue in result.warnings)
    assert any(issue.code == "missing_asset_universe" for issue in result.warnings)
