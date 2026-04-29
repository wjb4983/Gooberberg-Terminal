"""Task-head registry keyed by task/subtask pairs."""

from __future__ import annotations

from dataclasses import dataclass

from worker_training.task_heads.base import StandardTaskHead, TaskHead


@dataclass(frozen=True, slots=True)
class TaskHeadRegistry:
    _heads: dict[tuple[str, str], TaskHead]

    def resolve(self, task: str, subtask: str) -> TaskHead:
        return self._heads.get((task, subtask), self._heads[("forecasting", "univariate")])


HEADS: tuple[StandardTaskHead, ...] = (
    StandardTaskHead("ranking", "default", "relevance_score", "ranked_scores"),
    StandardTaskHead("entry_signal", "default", "entry_probability", "entry_decision"),
    StandardTaskHead("exit_signal", "default", "exit_probability", "exit_decision"),
    StandardTaskHead("regime_state", "default", "state_label", "regime_distribution"),
    StandardTaskHead("return_forecast", "default", "forward_return", "return_distribution"),
    StandardTaskHead("vol_forecast", "default", "forward_volatility", "volatility_distribution"),
    StandardTaskHead("allocation", "default", "weight", "portfolio_weights"),
    StandardTaskHead("cost_estimation", "default", "expected_cost", "cost_estimate"),
    StandardTaskHead("forecasting", "univariate", "target_value", "point_forecast"),
)

TASK_HEAD_REGISTRY = TaskHeadRegistry(_heads={(head.task, head.subtask): head for head in HEADS})
