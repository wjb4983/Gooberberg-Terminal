from worker_training.evaluation.engine import build_metric_bundle


def test_metric_bundle_selects_defaults_and_output_type_metrics() -> None:
    bundle = build_metric_bundle(
        task="forecasting",
        subtask="univariate",
        output_type="point_forecast",
        metrics_payload={"primary_metric": 0.9, "rmse": 0.12, "mape": 3.1, "aic": 123.0},
    )

    assert bundle["schema_version"] == "metric-bundle/v1"
    metric_names = [item["name"] for item in bundle["metrics"]]
    assert metric_names[:5] == ["primary_metric", "rmse", "mae", "mape", "smape"]
    assert bundle["metrics"][0]["role"] == "default"
    assert bundle["metrics"][0]["value_type"] == "number"


def test_metric_bundle_normalizes_types() -> None:
    bundle = build_metric_bundle(
        task="ranking",
        subtask="default",
        output_type="ranked_scores",
        metrics_payload={"primary_metric": True, "notes": "ok", "extra": {"a": 1}},
    )
    by_name = {item["name"]: item for item in bundle["metrics"]}
    assert by_name["primary_metric"]["value_type"] == "boolean"
    assert by_name["notes"]["value_type"] == "string"
    assert by_name["extra"]["value_type"] == "json"
