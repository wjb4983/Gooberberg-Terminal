from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.model_configs.compatibility import DatasetRequirement
from app.domain.model_registry import ModelSpec


class TorchNnTimeseriesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_type: Literal["forecasting"]
    data_type: Literal["time_series"]
    architecture: Literal["lstm", "gru", "tcn", "transformer_encoder"]
    lookback_window: int = Field(ge=8, le=10000)
    horizon_steps: int = Field(ge=1, le=512)
    hidden_size: int = Field(ge=8, le=4096)
    num_layers: int = Field(default=2, ge=1, le=24)
    num_attention_heads: int = Field(default=1, ge=1, le=32)
    dropout: float = Field(default=0.1, ge=0.0, lt=1.0)
    learning_rate: float = Field(default=1e-3, gt=0.0, le=1.0)
    batch_size: int = Field(default=64, ge=1, le=8192)
    loss_function: Literal["mse", "mae", "huber"] = "mse"

    @model_validator(mode="after")
    def validate_architecture_constraints(self) -> "TorchNnTimeseriesConfig":
        if self.architecture != "transformer_encoder" and self.num_attention_heads != 1:
            raise ValueError(
                "num_attention_heads must be 1 unless architecture=transformer_encoder"
            )
        if (
            self.architecture == "transformer_encoder"
            and self.hidden_size % self.num_attention_heads != 0
        ):
            raise ValueError(
                "hidden_size must be divisible by num_attention_heads for transformer_encoder"
            )
        return self


class TorchNnTimeseriesModelSpec(ModelSpec):
    model_family = "torch_nn_timeseries"
    supported_data_kinds = ("time_series",)
    required_index = "datetime"
    target_type = "regression"
    dataset_requirement = DatasetRequirement(
        required_fields=("ohlcv.close", "entity_id", "timestamp"),
        required_frequency="1d",
        require_point_in_time_data=True,
    )

    def validate_config(self, config: Mapping[str, Any]) -> Mapping[str, Any]:
        parsed = TorchNnTimeseriesConfig.model_validate(config)
        return parsed.model_dump(mode="python")
