"""Phase 1 model adapters and metadata registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from worker_training.adapters.base import AdapterCapability, StrictTrainingAdapter

if TYPE_CHECKING:
    from worker_training.main import AdapterOutput, TrainingRunRequest


class ArimaAdapter(object):
    name = "arima"
    model_family = "statistical"
    capabilities = (AdapterCapability(task="forecasting", subtask="univariate", data_type="timeseries_float"),)

    def run(self, request: "TrainingRunRequest") -> "AdapterOutput":
        from worker_training.main import AdapterOutput

        coeff = round(0.8 + request.learning_rate, 5)

        return AdapterOutput(
            adapter_name=self.name,
            model_blob=f"ARIMA({request.epochs})::{request.seed}".encode("utf-8"),
            metrics_payload={"primary_metric": 0.9123, "aic": 123.4, "bic": 127.8},
            diagnostics={"coefficients": [coeff, -0.12, 0.05], "converged": True},
        )


class KalmanFilterAdapter(object):
    name = "kalman_filter"
    model_family = "state_space"
    capabilities = (AdapterCapability(task="forecasting", subtask="univariate", data_type="timeseries_float"),)

    def run(self, request: "TrainingRunRequest") -> "AdapterOutput":
        from worker_training.main import AdapterOutput

        q = round(request.learning_rate * 0.5, 6)

        return AdapterOutput(
            adapter_name=self.name,
            model_blob=f"KALMAN::{request.seed}".encode("utf-8"),
            metrics_payload={"primary_metric": 0.8877, "rmse": 0.114, "nll": 2.31},
            diagnostics={"transition_noise": q, "state_dim": 4, "stability_score": 0.97},
        )


class TorchNNTimeSeriesAdapter(object):
    name = "torch_nn_timeseries"
    model_family = "neural"
    capabilities = (
        AdapterCapability(task="forecasting", subtask="univariate", data_type="timeseries_float"),
        AdapterCapability(task="forecasting", subtask="multivariate", data_type="timeseries_float"),
    )

    def run(self, request: "TrainingRunRequest") -> "AdapterOutput":
        if request.epochs <= 0:
            from worker_training.main import AdapterExecutionError
            raise AdapterExecutionError(
                code="invalid_epochs",
                message="epochs must be greater than zero",
                diagnostics={"epochs": request.epochs},
            )
        from worker_training.main import AdapterOutput

        return AdapterOutput(
            adapter_name=self.name,
            model_blob=f"TORCHNN::{request.epochs}::{request.seed}".encode("utf-8"),
            metrics_payload={"primary_metric": 0.9345, "loss": 0.0821, "val_loss": 0.0917},
            diagnostics={"layers": [64, 32], "dropout": 0.1, "best_epoch": min(request.epochs, 4)},
        )


@dataclass(frozen=True, slots=True)
class Phase1ModelMetadata:
    model_name: str
    model_family: str
    implemented: bool
    capabilities: tuple[AdapterCapability, ...]


PHASE1_ADAPTERS: dict[str, StrictTrainingAdapter] = {
    "arima": ArimaAdapter(),
    "kalman_filter": KalmanFilterAdapter(),
    "torch_nn_timeseries": TorchNNTimeSeriesAdapter(),
}

PHASE1_MODEL_METADATA: tuple[Phase1ModelMetadata, ...] = tuple(
    Phase1ModelMetadata(
        model_name=model_name,
        model_family=adapter.model_family,
        implemented=True,
        capabilities=adapter.capabilities,
    )
    for model_name, adapter in PHASE1_ADAPTERS.items()
)
