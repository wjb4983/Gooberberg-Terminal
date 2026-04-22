import hashlib
import json
from datetime import datetime
from uuid import UUID

from app.domain.backtest_runs.repository import Repository


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
