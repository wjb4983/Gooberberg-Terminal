from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from statistics import mean
from typing import Any


@dataclass(frozen=True, slots=True)
class SweepConfig:
    dip_thresholds: tuple[float, ...]
    confirmation_windows: tuple[int, ...]
    rebound_timeouts: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class StrategyParams:
    dip_threshold: float
    confirmation_window: int
    rebound_timeout: int


@dataclass(frozen=True, slots=True)
class VariantResult:
    variant_id: str
    model_type: str
    params: StrategyParams
    score: float
    metrics: dict[str, float]


def compute_intraday_features(rows: list[dict[str, Any]], params: StrategyParams) -> list[dict[str, float | bool]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if str(row.get("symbol", "")).upper() != "NVDA":
            continue
        session = str(row.get("session") or row.get("date") or "")
        if not session:
            continue
        grouped.setdefault(session, []).append(row)

    features: list[dict[str, float | bool]] = []
    for session, session_rows in grouped.items():
        ordered = sorted(session_rows, key=lambda r: int(r.get("minute", 0)))
        open_px = float(ordered[0].get("open", ordered[0].get("close", 0.0)))
        closes = [float(r.get("close", open_px)) for r in ordered]
        low_px = min(closes)
        dip_depth = max(0.0, (open_px - low_px) / open_px) if open_px else 0.0

        confirm_count = min(params.confirmation_window, len(closes))
        opening_return = ((closes[confirm_count - 1] - open_px) / open_px) if open_px and confirm_count else 0.0

        recovered = False
        recovery_minute = float(params.rebound_timeout)
        for idx, close in enumerate(closes[: params.rebound_timeout]):
            if close >= open_px:
                recovered = True
                recovery_minute = float(idx + 1)
                break

        likelihood = _estimate_recovery_likelihood(
            opening_return=opening_return,
            dip_depth=dip_depth,
            recovered=recovered,
            timeout=params.rebound_timeout,
            recovery_minute=recovery_minute,
        )
        features.append(
            {
                "opening_return": opening_return,
                "dip_depth": dip_depth,
                "recovered": recovered,
                "recovery_minute": recovery_minute,
                "recovery_likelihood": likelihood,
                "is_dip_event": dip_depth >= params.dip_threshold,
            }
        )
    return features


def _estimate_recovery_likelihood(*, opening_return: float, dip_depth: float, recovered: bool, timeout: int, recovery_minute: float) -> float:
    base = 0.5 - (1.2 * dip_depth) + (0.8 * opening_return)
    if recovered:
        base += 0.3 + max(0.0, (timeout - recovery_minute) / max(timeout, 1)) * 0.2
    return max(0.0, min(1.0, base))


def train_rules_baseline(features: list[dict[str, float | bool]]) -> dict[str, float]:
    dip_events = [f for f in features if bool(f["is_dip_event"])]
    if not dip_events:
        return {"recovery_rate": 0.0, "avg_recovery_minute": 0.0, "score": 0.0}
    recovery_rate = sum(1 for f in dip_events if bool(f["recovered"])) / len(dip_events)
    recovery_times = [float(f["recovery_minute"]) for f in dip_events if bool(f["recovered"])]
    avg_recovery_minute = mean(recovery_times) if recovery_times else 0.0
    score = (0.75 * recovery_rate) + (0.25 * (1.0 / (1.0 + avg_recovery_minute)))
    return {"recovery_rate": recovery_rate, "avg_recovery_minute": avg_recovery_minute, "score": score}


def train_ml_baseline(features: list[dict[str, float | bool]]) -> dict[str, float]:
    dip_events = [f for f in features if bool(f["is_dip_event"])]
    if not dip_events:
        return {"auc_like": 0.0, "brier_like": 1.0, "score": 0.0}

    labels = [1.0 if bool(f["recovered"]) else 0.0 for f in dip_events]
    probs = [float(f["recovery_likelihood"]) for f in dip_events]
    correct = sum(1.0 for p, y in zip(probs, labels, strict=True) if (p >= 0.5) == (y == 1.0)) / len(labels)
    brier = sum((p - y) ** 2 for p, y in zip(probs, labels, strict=True)) / len(labels)
    score = (0.7 * correct) + (0.3 * (1.0 - brier))
    return {"auc_like": correct, "brier_like": brier, "score": score}


def run_variant_sweep(rows: list[dict[str, Any]], sweep: SweepConfig) -> list[VariantResult]:
    results: list[VariantResult] = []
    for dip_threshold, confirm, timeout in product(
        sweep.dip_thresholds,
        sweep.confirmation_windows,
        sweep.rebound_timeouts,
    ):
        params = StrategyParams(dip_threshold=dip_threshold, confirmation_window=confirm, rebound_timeout=timeout)
        features = compute_intraday_features(rows, params)
        rules_metrics = train_rules_baseline(features)
        ml_metrics = train_ml_baseline(features)
        key = f"dip{dip_threshold:.3f}-c{confirm}-t{timeout}"
        results.append(VariantResult(variant_id=f"rules-{key}", model_type="rules", params=params, score=rules_metrics["score"], metrics=rules_metrics))
        results.append(VariantResult(variant_id=f"ml-{key}", model_type="ml", params=params, score=ml_metrics["score"], metrics=ml_metrics))
    return sorted(results, key=lambda r: r.score, reverse=True)
