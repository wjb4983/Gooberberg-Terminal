from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.model_configs.compatibility import DatasetCompatibilityMetadata, DatasetRequirement


@dataclass(frozen=True)
class QualificationIssue:
    code: str
    message: str


@dataclass(frozen=True)
class DatasetQualificationResult:
    errors: tuple[QualificationIssue, ...] = ()
    warnings: tuple[QualificationIssue, ...] = ()


@dataclass(frozen=True)
class QualificationContext:
    task_type: str
    subtask_type: str
    model_family: str
    model_config: dict[str, Any]


_TASK_SUBTASK_REQUIREMENTS: dict[tuple[str, str], dict[str, Any]] = {
    ("time_series_momentum", "ranking"): {
        "required_fields": ("entity_id", "timestamp"),
        "minimum_history_steps": 60,
        "requires_multi_asset_universe": True,
    },
    ("time_series_momentum", "entry_signal"): {
        "required_fields": ("entity_id", "timestamp"),
        "minimum_history_steps": 30,
    },
    ("time_series_momentum", "exit_signal"): {
        "required_fields": ("entity_id", "timestamp"),
        "minimum_history_steps": 30,
    },
    ("cross_sectional", "ranking"): {
        "required_fields": ("entity_id", "timestamp"),
        "minimum_history_steps": 120,
        "requires_multi_asset_universe": True,
    },
    ("cross_sectional", "return_forecast"): {
        "required_fields": ("entity_id", "timestamp"),
        "minimum_history_steps": 90,
        "requires_multi_asset_universe": True,
    },
    ("cross_sectional", "allocation"): {
        "required_fields": ("entity_id", "timestamp"),
        "minimum_history_steps": 120,
        "requires_multi_asset_universe": True,
    },
    ("volatility", "vol_forecast"): {
        "required_fields": ("returns.log", "timestamp"),
        "minimum_history_steps": 120,
    },
    ("regime_switching", "regime_state"): {
        "required_fields": ("returns.log", "timestamp"),
        "minimum_history_steps": 180,
        "require_point_in_time_data": True,
    },
}


def qualify_dataset_for_training(
    *,
    context: QualificationContext,
    dataset_metadata: DatasetCompatibilityMetadata,
    dataset_requirement: DatasetRequirement,
    raw_dataset_metadata: dict[str, Any],
) -> DatasetQualificationResult:
    errors: list[QualificationIssue] = []
    warnings: list[QualificationIssue] = []

    task_key = (context.task_type, context.subtask_type)
    task_requirement = _TASK_SUBTASK_REQUIREMENTS.get(task_key, {})

    required_fields = set(dataset_requirement.required_fields)
    required_fields.update(task_requirement.get("required_fields", ()))
    missing_fields = sorted(field for field in required_fields if field not in dataset_metadata.available_fields)
    if missing_fields:
        errors.append(
            QualificationIssue(
                code="missing_fields",
                message=(
                    "dataset is missing required fields "
                    f"{missing_fields} for task={context.task_type}, subtask={context.subtask_type}, "
                    f"model_family={context.model_family}"
                ),
            )
        )

    minimum_history_steps = max(
        int(task_requirement.get("minimum_history_steps", 0)),
        _model_minimum_history_steps(context.model_family, context.model_config),
    )
    history_steps = _read_positive_int(raw_dataset_metadata.get("history_window_steps"))
    if minimum_history_steps > 0:
        if history_steps is None:
            warnings.append(
                QualificationIssue(
                    code="missing_history_window",
                    message=(
                        f"dataset metadata is missing history_window_steps; minimum required history is "
                        f"{minimum_history_steps} steps"
                    ),
                )
            )
        elif history_steps < minimum_history_steps:
            errors.append(
                QualificationIssue(
                    code="insufficient_history_window",
                    message=(
                        f"dataset history_window_steps={history_steps} is below minimum required "
                        f"history of {minimum_history_steps} steps"
                    ),
                )
            )

    require_pit = dataset_requirement.require_point_in_time_data or bool(
        task_requirement.get("require_point_in_time_data", False)
    )
    if require_pit and dataset_metadata.point_in_time_ready is not True:
        errors.append(
            QualificationIssue(
                code="point_in_time_required",
                message="dataset must be point-in-time ready for this training intent",
            )
        )

    if task_requirement.get("requires_multi_asset_universe"):
        universe_count = _read_positive_int(raw_dataset_metadata.get("asset_universe_size"))
        if universe_count is None:
            members = raw_dataset_metadata.get("universe_members")
            if isinstance(members, list):
                universe_count = len([member for member in members if isinstance(member, str) and member])
        if universe_count is None:
            warnings.append(
                QualificationIssue(
                    code="missing_asset_universe",
                    message="dataset metadata is missing asset universe details for a multi-asset task",
                )
            )
        elif universe_count < 2:
            errors.append(
                QualificationIssue(
                    code="insufficient_asset_universe",
                    message=f"task requires multi-asset universe but dataset has {universe_count} asset(s)",
                )
            )

    return DatasetQualificationResult(errors=tuple(errors), warnings=tuple(warnings))


def _model_minimum_history_steps(model_family: str, model_config: dict[str, Any]) -> int:
    if model_family == "torch_nn_timeseries":
        lookback = _read_positive_int(model_config.get("lookback_window")) or 0
        horizon = _read_positive_int(model_config.get("horizon_steps")) or 0
        return lookback + horizon
    if model_family == "hmm_regime_switching":
        return _read_positive_int(model_config.get("lookback_window")) or 120
    if model_family == "arima":
        p = _read_positive_int(model_config.get("p")) or 0
        d = _read_positive_int(model_config.get("d")) or 0
        q = _read_positive_int(model_config.get("q")) or 0
        return max(30, p + d + q + 10)
    return 0


def _read_positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    return None
