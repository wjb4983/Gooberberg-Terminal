from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.model_registry import ModelSpec


class HmmRegimeSwitchingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n_states: int = Field(ge=2, le=12)
    lookback_window: int = Field(ge=10, le=10000)
    covariance_type: Literal["diag", "full"] = "diag"
    convergence_tol: float = Field(default=1e-3, gt=0.0, le=1.0)
    max_iterations: int = Field(default=200, ge=10, le=10000)


class HmmRegimeSwitchingModelSpec(ModelSpec):
    model_family = "hmm_regime_switching"

    def validate_config(self, config: Mapping[str, Any]) -> Mapping[str, Any]:
        parsed = HmmRegimeSwitchingConfig.model_validate(config)
        return parsed.model_dump(mode="python")
