from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.model_configs.compatibility import DatasetRequirement
from app.domain.model_registry import ModelSpec


class KalmanFilterConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_type: Literal["filtering", "nowcasting"]
    data_type: Literal["state_space_timeseries"]
    transition_structure: Literal["identity", "constant_velocity", "custom"] = "constant_velocity"
    state_dimension: int = Field(ge=1, le=256)
    observation_dimension: int = Field(ge=1, le=256)
    process_noise: float = Field(gt=0.0, le=10.0)
    measurement_noise: float = Field(gt=0.0, le=10.0)
    initial_covariance_scale: float = Field(default=1.0, gt=0.0, le=100.0)

    @model_validator(mode="after")
    def validate_dimension_constraints(self) -> "KalmanFilterConfig":
        if self.observation_dimension > self.state_dimension:
            raise ValueError("observation_dimension must be less than or equal to state_dimension")
        if (
            self.transition_structure == "identity"
            and self.observation_dimension != self.state_dimension
        ):
            raise ValueError(
                "identity transition requires observation_dimension == state_dimension"
            )
        return self


class KalmanFilterModelSpec(ModelSpec):
    model_family = "kalman_filter"
    supported_data_kinds = ("time_series",)
    required_index = "datetime"
    target_type = "regression"
    dataset_requirement = DatasetRequirement(
        required_fields=("observations.state_signal",),
        required_frequency="1d",
        require_point_in_time_data=True,
    )

    def validate_config(self, config: Mapping[str, Any]) -> Mapping[str, Any]:
        parsed = KalmanFilterConfig.model_validate(config)
        return parsed.model_dump(mode="python")
