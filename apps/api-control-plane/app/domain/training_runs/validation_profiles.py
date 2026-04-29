from __future__ import annotations

from enum import StrEnum

from app.domain.task_definitions import get_task_subtask_definition


class ValidationProfile(StrEnum):
    WALK_FORWARD = "walk_forward"
    ROLLING_SPLIT = "rolling_split"
    PURGED_K_FOLD = "purged_k_fold"
    EMBARGO = "embargo"


DEFAULT_VALIDATION_PROFILES: dict[tuple[str, str], ValidationProfile] = {
    ("time_series_momentum", "ranking"): ValidationProfile.WALK_FORWARD,
    ("time_series_momentum", "entry_signal"): ValidationProfile.ROLLING_SPLIT,
    ("time_series_momentum", "exit_signal"): ValidationProfile.ROLLING_SPLIT,
    ("cross_sectional", "ranking"): ValidationProfile.PURGED_K_FOLD,
    ("cross_sectional", "return_forecast"): ValidationProfile.PURGED_K_FOLD,
    ("cross_sectional", "allocation"): ValidationProfile.PURGED_K_FOLD,
    ("volatility", "vol_forecast"): ValidationProfile.ROLLING_SPLIT,
    ("regime_switching", "regime_state"): ValidationProfile.EMBARGO,
    ("regime_switching", "entry_signal"): ValidationProfile.EMBARGO,
    ("regime_switching", "exit_signal"): ValidationProfile.EMBARGO,
}


def resolve_validation_profile(*, task_type: str, subtask_type: str, requested_profile: ValidationProfile | None) -> ValidationProfile:
    if requested_profile is not None:
        return requested_profile

    definition = get_task_subtask_definition(task_type=task_type, subtask_type=subtask_type)
    return DEFAULT_VALIDATION_PROFILES[(definition.task_type, definition.subtask_type)]
