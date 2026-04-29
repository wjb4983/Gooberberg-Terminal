from worker_training.task_heads import TASK_HEAD_REGISTRY


HEAD_CASES = [
    ("ranking", "default", "relevance_score", "ranked_scores"),
    ("entry_signal", "default", "entry_probability", "entry_decision"),
    ("exit_signal", "default", "exit_probability", "exit_decision"),
    ("regime_state", "default", "state_label", "regime_distribution"),
    ("return_forecast", "default", "forward_return", "return_distribution"),
    ("vol_forecast", "default", "forward_volatility", "volatility_distribution"),
    ("allocation", "default", "weight", "portfolio_weights"),
    ("cost_estimation", "default", "expected_cost", "cost_estimate"),
]


def test_task_heads_target_schema_and_prediction_output() -> None:
    for task, subtask, target_kind, prediction_kind in HEAD_CASES:
        head = TASK_HEAD_REGISTRY.resolve(task, subtask)
        schema = head.build_target_schema()
        prediction = head.format_prediction({"primary_metric": 0.91, "raw": 1.23})

        assert schema["task"] == task
        assert schema["subtask"] == subtask
        assert schema["target_kind"] == target_kind
        assert schema["required_fields"] == ["entity_id", "timestamp", "target"]

        assert prediction["schema_version"] == "prediction-output/v1"
        assert prediction["task"] == task
        assert prediction["subtask"] == subtask
        assert prediction["prediction_kind"] == prediction_kind
        assert prediction["primary_metric"] == 0.91
        assert prediction["values"]["raw"] == 1.23
