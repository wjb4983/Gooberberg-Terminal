"""Metric selection and normalization for training evaluations."""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
from typing import Any


@dataclass(frozen=True, slots=True)
class MetricSpec:
    name: str
    role: str = "optional"


DEFAULT_METRICS: dict[tuple[str, str], tuple[MetricSpec, ...]] = {
    ("forecasting", "univariate"): (MetricSpec("primary_metric", role="default"), MetricSpec("rmse"), MetricSpec("mae")),
    ("ranking", "default"): (MetricSpec("primary_metric", role="default"), MetricSpec("ndcg"), MetricSpec("map")),
}

OUTPUT_TYPE_METRICS: dict[str, tuple[MetricSpec, ...]] = {
    "point_forecast": (MetricSpec("mape"), MetricSpec("smape")),
    "return_distribution": (MetricSpec("pinball_loss"),),
    "ranked_scores": (MetricSpec("auc"),),
}


def build_metric_bundle(
    *,
    task: str,
    subtask: str,
    output_type: str,
    metrics_payload: dict[str, Any],
) -> dict[str, Any]:
    """Build consistently named/typed metric bundle for artifact and event payloads."""

    metric_specs = list(DEFAULT_METRICS.get((task, subtask), (MetricSpec("primary_metric", role="default"),)))
    metric_specs.extend(OUTPUT_TYPE_METRICS.get(output_type, ()))

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for spec in metric_specs:
        if spec.name in seen:
            continue
        seen.add(spec.name)
        raw_value = metrics_payload.get(spec.name)
        selected.append(
            {
                "name": spec.name,
                "value": _coerce_metric_value(raw_value),
                "value_type": _infer_value_type(raw_value),
                "role": spec.role,
            }
        )

    for key, value in metrics_payload.items():
        if key in seen:
            continue
        selected.append(
            {
                "name": key,
                "value": _coerce_metric_value(value),
                "value_type": _infer_value_type(value),
                "role": "optional",
            }
        )

    return {
        "schema_version": "metric-bundle/v1",
        "task": task,
        "subtask": subtask,
        "output_type": output_type,
        "metrics": selected,
    }


def _infer_value_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, Real):
        return "number"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    return "json"


def _coerce_metric_value(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, Real):
        return float(value)
    return value
