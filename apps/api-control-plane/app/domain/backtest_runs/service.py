import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from app.domain.backtest_runs.repository import Repository




LEAKAGE_FAIL_CODES = {"fail", "error"}


class LeakageDetectedError(ValueError):
    def __init__(self, summary: dict[str, Any]) -> None:
        super().__init__("backtest leakage checks failed")
        self.summary = summary


def run_leakage_checks(payload: dict[str, Any]) -> dict[str, Any]:
    parameters = payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {}
    checks: list[dict[str, str]] = []

    def record(name: str, status: str, detail: str) -> None:
        checks.append({"name": name, "status": status, "detail": detail})

    lookahead_enabled = bool(parameters.get("allow_lookahead", False))
    if lookahead_enabled:
        record("look_ahead", "fail", "parameters.allow_lookahead must be false")
    else:
        record("look_ahead", "pass", "look-ahead disabled")

    point_in_time = parameters.get("point_in_time_constituents")
    if point_in_time is False:
        record("survivorship_bias", "fail", "point_in_time_constituents must be true")
    elif point_in_time is True:
        record("survivorship_bias", "pass", "point-in-time universe configured")
    else:
        record("survivorship_bias", "warn", "point_in_time_constituents not supplied")

    event_ts = parameters.get("event_timestamp_field")
    asof_ts = parameters.get("asof_timestamp_field")
    if isinstance(event_ts, str) and isinstance(asof_ts, str) and event_ts == asof_ts:
        record("timestamp_alignment", "pass", "event and as-of timestamps aligned")
    else:
        record("timestamp_alignment", "fail", "event_timestamp_field and asof_timestamp_field must match")

    target_in_features = bool(parameters.get("target_in_features", False))
    if target_in_features:
        record("target_leakage", "fail", "target labels detected in feature inputs")
    else:
        record("target_leakage", "pass", "no target leakage markers detected")

    has_failure = any(item["status"] in LEAKAGE_FAIL_CODES for item in checks)
    return {
        "status": "fail" if has_failure else "pass",
        "is_valid": not has_failure,
        "checked_at": datetime.utcnow().isoformat() + "Z",
        "checks": checks,
    }


def assert_leakage_checks(summary: dict[str, Any]) -> None:
    if summary.get("is_valid") is not True:
        raise LeakageDetectedError(summary)

class Service:
    OVERSIZED_THRESHOLD = 2500

    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    def create(self, payload: dict[str, object]) -> dict[str, object]:
        return self._repository.add(payload)

    def list_all(self) -> list[dict[str, object]]:
        return self._repository.list_all()

    def get(self, item_id: UUID) -> dict[str, object] | None:
        return self._repository.get(item_id)

    def estimate_run_size(self, payload: dict[str, object]) -> dict[str, object]:
        parameters = payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {}
        symbols = parameters.get("symbols") if isinstance(parameters, dict) else None
        symbol_count = len(symbols) if isinstance(symbols, list) and symbols else int(parameters.get("symbol_count", 1) if isinstance(parameters, dict) else 1)
        symbol_count = max(symbol_count, 1)

        window_start = payload.get("window_start")
        window_end = payload.get("window_end")
        if isinstance(window_start, datetime) and isinstance(window_end, datetime):
            date_span_days = max((window_end.date() - window_start.date()).days, 1)
        else:
            date_span_days = 1

        estimated_units = symbol_count * date_span_days
        requires_confirmation = estimated_units >= self.OVERSIZED_THRESHOLD

        token = self._build_confirmation_token(payload, estimated_units) if requires_confirmation else None
        return {
            "symbol_count": symbol_count,
            "date_span_days": date_span_days,
            "estimated_units": estimated_units,
            "oversized_threshold": self.OVERSIZED_THRESHOLD,
            "requires_confirmation": requires_confirmation,
            "confirmation_token": token,
            "heuristic": "symbol_count x date_span_days",
        }

    def _build_confirmation_token(self, payload: dict[str, object], estimated_units: int) -> str:
        basis = {
            "strategy_key": payload.get("strategy_key"),
            "model_config_id": str(payload.get("model_config_id") or ""),
            "window_start": getattr(payload.get("window_start"), "isoformat", lambda: str(payload.get("window_start")))(),
            "window_end": getattr(payload.get("window_end"), "isoformat", lambda: str(payload.get("window_end")))(),
            "parameters": payload.get("parameters", {}),
            "estimated_units": estimated_units,
        }
        digest = hashlib.sha256(json.dumps(basis, sort_keys=True, default=str).encode("utf-8")).hexdigest()
        return digest[:20]

    def validate_confirmation_token(self, payload: dict[str, object], token: str | None) -> bool:
        estimate = self.estimate_run_size(payload)
        if not estimate["requires_confirmation"]:
            return True
        return bool(token) and token == estimate["confirmation_token"]
