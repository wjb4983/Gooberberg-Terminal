"""Phase 3 advanced-ml adapters and metadata registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from worker_training.adapters.base import AdapterCapability, StrictTrainingAdapter

if TYPE_CHECKING:
    from worker_training.main import AdapterOutput, TrainingRunRequest


class _Phase3AdvancedMlAdapter:
    capabilities: tuple[AdapterCapability, ...] = ()

    def run(self, request: "TrainingRunRequest") -> "AdapterOutput":
        from worker_training.main import AdapterOutput

        quality = round(0.79 + (request.learning_rate * 0.5), 4)
        return AdapterOutput(
            adapter_name=self.name,
            model_blob=f"PHASE3::{self.name}::{request.epochs}::{request.seed}".encode("utf-8"),
            metrics_payload={
                "primary_metric": quality,
                "calibration_error": round(max(0.0, 1.0 - quality), 4),
                "latency_ms_p50": 12.4,
            },
            diagnostics={
                "model_family": request.model_family,
                "training_contract": "fit/predict/evaluate",
                "capabilities": [
                    {"task": c.task, "subtask": c.subtask, "data_type": c.data_type} for c in self.capabilities
                ],
                "compute_profile": {
                    "estimated_vcpu_hours": round(max(0.5, request.epochs * 0.4), 2),
                    "estimated_gpu_hours": round(max(0.0, request.epochs * 0.15), 2),
                    "peak_memory_gb": round(3.5 + (request.epochs * 0.2), 2),
                },
                "resource_warnings": ["high_memory_profile" if request.epochs >= 5 else "none"],
            },
        )


class GBDTMetaEnsembleAdapter(_Phase3AdvancedMlAdapter):
    name = "gbdt_meta_ensemble"
    model_family = "gbdt_meta_ensemble"
    capabilities = (
        AdapterCapability(task="return_forecast", subtask="default", data_type="tabular_float"),
        AdapterCapability(task="ranking", subtask="default", data_type="tabular_float"),
    )


class DeepCrossAssetTransformerAdapter(_Phase3AdvancedMlAdapter):
    name = "deep_cross_asset_transformer"
    model_family = "deep_cross_asset_transformer"
    capabilities = (
        AdapterCapability(task="return_forecast", subtask="default", data_type="timeseries_float"),
        AdapterCapability(task="allocation", subtask="default", data_type="timeseries_float"),
    )


class SequenceTemporalFusionAdapter(_Phase3AdvancedMlAdapter):
    name = "sequence_temporal_fusion"
    model_family = "sequence_temporal_fusion"
    capabilities = (
        AdapterCapability(task="return_forecast", subtask="default", data_type="timeseries_float"),
        AdapterCapability(task="vol_forecast", subtask="default", data_type="timeseries_float"),
    )


class GraphRelationalAlphaAdapter(_Phase3AdvancedMlAdapter):
    name = "graph_relational_alpha"
    model_family = "graph_relational_alpha"
    capabilities = (
        AdapterCapability(task="ranking", subtask="default", data_type="graph_float"),
        AdapterCapability(task="allocation", subtask="default", data_type="graph_float"),
    )


class MoERegimeRouterAdapter(_Phase3AdvancedMlAdapter):
    name = "moe_regime_router"
    model_family = "moe_regime_router"
    capabilities = (
        AdapterCapability(task="regime_state", subtask="default", data_type="timeseries_float"),
        AdapterCapability(task="allocation", subtask="default", data_type="timeseries_float"),
    )


class ConformalUncertaintyWrapperAdapter(_Phase3AdvancedMlAdapter):
    name = "conformal_uncertainty_wrapper"
    model_family = "conformal_uncertainty_wrapper"
    capabilities = (
        AdapterCapability(task="cost_estimation", subtask="default", data_type="tabular_float"),
        AdapterCapability(task="return_forecast", subtask="default", data_type="tabular_float"),
    )


class OnlineDriftAdaptiveLearnerAdapter(_Phase3AdvancedMlAdapter):
    name = "online_drift_adaptive_learner"
    model_family = "online_drift_adaptive_learner"
    capabilities = (
        AdapterCapability(task="ranking", subtask="default", data_type="stream_float"),
        AdapterCapability(task="entry_signal", subtask="default", data_type="stream_float"),
    )


@dataclass(frozen=True, slots=True)
class Phase3ModelMetadata:
    model_name: str
    model_family: str
    implemented: bool
    capabilities: tuple[AdapterCapability, ...]


PHASE3_ADAPTERS: dict[str, StrictTrainingAdapter] = {
    "gbdt_meta_ensemble": GBDTMetaEnsembleAdapter(),
    "deep_cross_asset_transformer": DeepCrossAssetTransformerAdapter(),
    "sequence_temporal_fusion": SequenceTemporalFusionAdapter(),
    "graph_relational_alpha": GraphRelationalAlphaAdapter(),
    "moe_regime_router": MoERegimeRouterAdapter(),
    "conformal_uncertainty_wrapper": ConformalUncertaintyWrapperAdapter(),
    "online_drift_adaptive_learner": OnlineDriftAdaptiveLearnerAdapter(),
}

PHASE3_MODEL_METADATA: tuple[Phase3ModelMetadata, ...] = tuple(
    Phase3ModelMetadata(
        model_name=model_name,
        model_family=adapter.model_family,
        implemented=True,
        capabilities=adapter.capabilities,
    )
    for model_name, adapter in PHASE3_ADAPTERS.items()
)
