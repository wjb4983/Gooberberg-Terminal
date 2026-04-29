from worker_training.main import ADAPTER_REGISTRY, AdapterExecutionError, TrainingRunRequest


def test_registry_resolves_adapter_by_model_family() -> None:
    request = TrainingRunRequest.model_validate(
        {
            "model_name": "ignored",
            "model_family": "statistical",
            "task": "forecasting",
            "subtask": "univariate",
            "data_type": "timeseries_float",
        }
    )

    adapter = ADAPTER_REGISTRY.resolve(request)

    assert adapter.name == "arima"


def test_registry_fails_fast_for_unsupported_capability() -> None:
    request = TrainingRunRequest.model_validate(
        {
            "model_name": "ignored",
            "model_family": "state_space",
            "task": "classification",
            "subtask": "multiclass",
            "data_type": "tabular_float",
        }
    )

    try:
        ADAPTER_REGISTRY.resolve(request)
        assert False, "expected unsupported capability failure"
    except AdapterExecutionError as exc:
        assert exc.code == "unsupported_capability"
        assert "state_space" in str(exc)
        assert "classification" in str(exc)
