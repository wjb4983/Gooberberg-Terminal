from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.model_configs.compatibility import DatasetRequirement
from app.domain.model_registry import ModelSpec


class ArimaConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    task_type: Literal["forecasting"]
    data_type: Literal["time_series_univariate"]
    p: int = Field(ge=0, le=10)
    d: int = Field(ge=0, le=2)
    q: int = Field(ge=0, le=10)
    seasonal_period: int = Field(default=0, ge=0, le=365)
    seasonal_p: int = Field(default=0, ge=0, le=5)
    seasonal_d: int = Field(default=0, ge=0, le=1)
    seasonal_q: int = Field(default=0, ge=0, le=5)
    trend: Literal["none", "constant", "linear", "constant_linear"] = "constant"

    @model_validator(mode="after")
    def validate_arima_constraints(self) -> "ArimaConfig":
        if self.p == 0 and self.d == 0 and self.q == 0:
            raise ValueError("at least one of p, d, q must be non-zero")
        if self.d + self.seasonal_d > 2:
            raise ValueError("d + seasonal_d must be less than or equal to 2")
        has_seasonal_order = any((self.seasonal_p, self.seasonal_d, self.seasonal_q))
        if self.seasonal_period == 0 and has_seasonal_order:
            raise ValueError("seasonal_period must be > 0 when seasonal order terms are used")
        if self.seasonal_period > 0 and self.seasonal_period < 2:
            raise ValueError("seasonal_period must be 0 or at least 2")
        return self


class ArimaModelSpec(ModelSpec):
    model_family = "arima"
    supported_data_kinds = ("time_series",)
    required_index = "datetime"
    target_type = "regression"
    dataset_requirement = DatasetRequirement(
        required_fields=("ohlcv.close",),
        required_frequency="1d",
        require_point_in_time_data=True,
    )

    def validate_config(self, config: Mapping[str, Any]) -> Mapping[str, Any]:
        parsed = ArimaConfig.model_validate(config)
        return parsed.model_dump(mode="python")
