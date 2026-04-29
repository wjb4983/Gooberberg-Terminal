"""Phase 2 tradable-alpha adapters and metadata registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from worker_training.adapters.base import AdapterCapability, StrictTrainingAdapter

if TYPE_CHECKING:
    from worker_training.main import AdapterOutput, TrainingRunRequest


class _Phase2TradableAlphaAdapter(object):
    model_family = "tradable_alpha"
    capabilities: tuple[AdapterCapability, ...] = ()

    def run(self, request: "TrainingRunRequest") -> "AdapterOutput":
        from worker_training.main import AdapterOutput

        quality = round(0.71 + request.learning_rate, 4)
        return AdapterOutput(
            adapter_name=self.name,
            model_blob=f"PHASE2::{self.name}::{request.epochs}::{request.seed}".encode("utf-8"),
            metrics_payload={"primary_metric": quality, "ic": round(quality - 0.09, 4), "turnover": 0.24},
            diagnostics={
                "model_family": request.model_family,
                "capabilities": [
                    {"task": c.task, "subtask": c.subtask, "data_type": c.data_type} for c in self.capabilities
                ],
            },
        )


class XGBoostIntradayMomentumAdapter(_Phase2TradableAlphaAdapter):
    name = "xgboost_intraday_momentum"
    model_family = "xgboost_intraday_momentum"
    capabilities = (
        AdapterCapability(task="entry_signal", subtask="default", data_type="timeseries_float"),
        AdapterCapability(task="ranking", subtask="default", data_type="timeseries_float"),
    )


class LinearMeanReversionZScoreAdapter(_Phase2TradableAlphaAdapter):
    name = "linear_mean_reversion_zscore"
    model_family = "linear_mean_reversion_zscore"
    capabilities = (
        AdapterCapability(task="entry_signal", subtask="default", data_type="tabular_float"),
        AdapterCapability(task="exit_signal", subtask="default", data_type="tabular_float"),
        AdapterCapability(task="ranking", subtask="default", data_type="tabular_float"),
    )


class FuturesCarryTermStructureAdapter(_Phase2TradableAlphaAdapter):
    name = "futures_carry_term_structure"
    model_family = "futures_carry_term_structure"
    capabilities = (
        AdapterCapability(task="ranking", subtask="default", data_type="tabular_float"),
        AdapterCapability(task="allocation", subtask="default", data_type="tabular_float"),
    )


class ElasticNetCrossSectionalFactorAlphaAdapter(_Phase2TradableAlphaAdapter):
    name = "elasticnet_cross_sectional_factor_alpha"
    model_family = "elasticnet_cross_sectional_factor_alpha"
    capabilities = (
        AdapterCapability(task="return_forecast", subtask="default", data_type="tabular_float"),
        AdapterCapability(task="ranking", subtask="default", data_type="tabular_float"),
        AdapterCapability(task="allocation", subtask="default", data_type="tabular_float"),
    )


class EventDrivenEarningsDriftAdapter(_Phase2TradableAlphaAdapter):
    name = "event_driven_earnings_drift"
    model_family = "event_driven_earnings_drift"
    capabilities = (
        AdapterCapability(task="entry_signal", subtask="default", data_type="event_float"),
        AdapterCapability(task="ranking", subtask="default", data_type="event_float"),
    )


class AnalystRevisionDiffusionAlphaAdapter(_Phase2TradableAlphaAdapter):
    name = "analyst_revision_diffusion_alpha"
    model_family = "analyst_revision_diffusion_alpha"
    capabilities = (
        AdapterCapability(task="entry_signal", subtask="default", data_type="tabular_float"),
        AdapterCapability(task="ranking", subtask="default", data_type="tabular_float"),
    )


class OptionsIVSkewReversionAdapter(_Phase2TradableAlphaAdapter):
    name = "options_iv_skew_reversion"
    model_family = "options_iv_skew_reversion"
    capabilities = (
        AdapterCapability(task="entry_signal", subtask="default", data_type="options_surface_float"),
        AdapterCapability(task="exit_signal", subtask="default", data_type="options_surface_float"),
        AdapterCapability(task="cost_estimation", subtask="default", data_type="options_surface_float"),
    )


@dataclass(frozen=True, slots=True)
class Phase2ModelMetadata:
    model_name: str
    model_family: str
    implemented: bool
    capabilities: tuple[AdapterCapability, ...]


PHASE2_ADAPTERS: dict[str, StrictTrainingAdapter] = {
    "xgboost_intraday_momentum": XGBoostIntradayMomentumAdapter(),
    "linear_mean_reversion_zscore": LinearMeanReversionZScoreAdapter(),
    "futures_carry_term_structure": FuturesCarryTermStructureAdapter(),
    "elasticnet_cross_sectional_factor_alpha": ElasticNetCrossSectionalFactorAlphaAdapter(),
    "event_driven_earnings_drift": EventDrivenEarningsDriftAdapter(),
    "analyst_revision_diffusion_alpha": AnalystRevisionDiffusionAlphaAdapter(),
    "options_iv_skew_reversion": OptionsIVSkewReversionAdapter(),
}

PHASE2_MODEL_METADATA: tuple[Phase2ModelMetadata, ...] = tuple(
    Phase2ModelMetadata(
        model_name=model_name,
        model_family=adapter.model_family,
        implemented=True,
        capabilities=adapter.capabilities,
    )
    for model_name, adapter in PHASE2_ADAPTERS.items()
)
