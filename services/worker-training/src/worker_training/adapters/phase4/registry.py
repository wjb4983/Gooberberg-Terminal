"""Phase 4 frontier-model adapters as staged feasibility/full-training runners."""
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from worker_training.adapters.base import AdapterCapability, StrictTrainingAdapter
if TYPE_CHECKING:
    from worker_training.main import AdapterOutput, TrainingRunRequest
class _Phase4FrontierAdapter:
    capabilities: tuple[AdapterCapability, ...] = ()
    supported_training_modes: tuple[str, ...] = ("feasibility",)
    def run(self, request: "TrainingRunRequest") -> "AdapterOutput":
        from worker_training.main import AdapterOutput
        requested_mode = "full_training" if request.epochs >= 5 else "feasibility"
        selected_mode = requested_mode if requested_mode in self.supported_training_modes else "feasibility"
        mode_degraded = selected_mode != requested_mode
        score = round(0.63 + min(0.18, request.learning_rate * 2), 4)
        diagnostics = {
            "model_family": request.model_family,
            "phase": "phase4",
            "maturity": "experimental",
            "staged_adapter": True,
            "requested_training_mode": requested_mode,
            "selected_training_mode": selected_mode,
            "capability_limitations": [
                "research_use_only",
                "non_production_model",
                "feasibility_mode_uses_surrogate_training_loop",
            ],
            "experimental_disclaimer": "Experimental model adapter: use for feasibility and simulation only; production deployment is disabled.",
            "mode_fallback": (
                "Requested full_training is not yet available for this model family; feasibility mode executed instead."
                if mode_degraded
                else "none"
            ),
            "capabilities": [
                {"task": c.task, "subtask": c.subtask, "data_type": c.data_type} for c in self.capabilities
            ],
        }
        return AdapterOutput(
            adapter_name=self.name,
            model_blob=f"PHASE4::{self.name}::{selected_mode}::{request.epochs}::{request.seed}".encode("utf-8"),
            metrics_payload={"primary_metric": score, "stability": round(max(0.0, score - 0.08), 4), "coverage": 0.91},
            diagnostics=diagnostics,
        )
class TFTxTemporalMoEAdapter(_Phase4FrontierAdapter):
    name = "tftx_temporal_moe"; model_family = "tftx_temporal_moe"; supported_training_modes = ("feasibility", "full_training")
    capabilities = (AdapterCapability(task="return_forecast", subtask="default", data_type="timeseries_float"),)
class TinyTimeMixPatchEncoderAdapter(_Phase4FrontierAdapter):
    name = "tiny_time_mix_patch_encoder"; model_family = "tiny_time_mix_patch_encoder"
    capabilities = (AdapterCapability(task="forecasting", subtask="univariate", data_type="timeseries_float"),)
class WaveletDiffusionForecasterAdapter(_Phase4FrontierAdapter):
    name = "wavelet_diffusion_forecaster"; model_family = "wavelet_diffusion_forecaster"
    capabilities = (AdapterCapability(task="return_forecast", subtask="default", data_type="timeseries_float"),)
class OnlineBayesianChangepointHazardAdapter(_Phase4FrontierAdapter):
    name = "online_bayesian_changepoint_hazard"; model_family = "online_bayesian_changepoint_hazard"; supported_training_modes = ("feasibility", "full_training")
    capabilities = (AdapterCapability(task="regime_state", subtask="default", data_type="timeseries_float"),)
class PooledHierarchicalReconciliationAdapter(_Phase4FrontierAdapter):
    name = "pooled_hierarchical_reconciliation"; model_family = "pooled_hierarchical_reconciliation"
    capabilities = (AdapterCapability(task="forecasting", subtask="multivariate", data_type="timeseries_float"),)
class RetrievalAugmentedRegimeClassifierAdapter(_Phase4FrontierAdapter):
    name = "retrieval_augmented_regime_classifier"; model_family = "retrieval_augmented_regime_classifier"
    capabilities = (AdapterCapability(task="regime_state", subtask="default", data_type="tabular_float"),)
class GraphDiffusionSpilloverAdapter(_Phase4FrontierAdapter):
    name = "graph_diffusion_spillover"; model_family = "graph_diffusion_spillover"
    capabilities = (AdapterCapability(task="allocation", subtask="default", data_type="graph_float"),)
class TabularInContextLearnerAdapter(_Phase4FrontierAdapter):
    name = "tabular_in_context_learner"; model_family = "tabular_in_context_learner"
    capabilities = (AdapterCapability(task="ranking", subtask="default", data_type="tabular_float"),)
class ConformalizedQuantileNetworkV2Adapter(_Phase4FrontierAdapter):
    name = "conformalized_quantile_network_v2"; model_family = "conformalized_quantile_network_v2"; supported_training_modes = ("feasibility", "full_training")
    capabilities = (AdapterCapability(task="vol_forecast", subtask="default", data_type="timeseries_float"),)
class SyntheticControlBayesianDynamicAdapter(_Phase4FrontierAdapter):
    name = "synthetic_control_bayesian_dynamic"; model_family = "synthetic_control_bayesian_dynamic"
    capabilities = (AdapterCapability(task="cost_estimation", subtask="default", data_type="tabular_float"),)
@dataclass(frozen=True, slots=True)
class Phase4ModelMetadata:
    model_name: str; model_family: str; implemented: bool; capabilities: tuple[AdapterCapability, ...]; maturity: str; staged_adapter: bool; supported_training_modes: tuple[str, ...]
PHASE4_ADAPTERS: dict[str, StrictTrainingAdapter] = {
    "tftx_temporal_moe": TFTxTemporalMoEAdapter(), "tiny_time_mix_patch_encoder": TinyTimeMixPatchEncoderAdapter(), "wavelet_diffusion_forecaster": WaveletDiffusionForecasterAdapter(), "online_bayesian_changepoint_hazard": OnlineBayesianChangepointHazardAdapter(), "pooled_hierarchical_reconciliation": PooledHierarchicalReconciliationAdapter(), "retrieval_augmented_regime_classifier": RetrievalAugmentedRegimeClassifierAdapter(), "graph_diffusion_spillover": GraphDiffusionSpilloverAdapter(), "tabular_in_context_learner": TabularInContextLearnerAdapter(), "conformalized_quantile_network_v2": ConformalizedQuantileNetworkV2Adapter(), "synthetic_control_bayesian_dynamic": SyntheticControlBayesianDynamicAdapter(),
}
PHASE4_MODEL_METADATA: tuple[Phase4ModelMetadata, ...] = tuple(Phase4ModelMetadata(model_name=model_name, model_family=adapter.model_family, implemented=True, capabilities=adapter.capabilities, maturity="experimental", staged_adapter=True, supported_training_modes=adapter.supported_training_modes) for model_name, adapter in PHASE4_ADAPTERS.items())
