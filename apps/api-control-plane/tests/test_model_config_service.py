from enum import Enum
from typing import Any

from app.domain.model_configs.service import ModelConfigService
from app.domain.model_configs.specs import HmmRegimeSwitchingModelSpec
from app.domain.model_registry import ModelRegistry


class _InMemoryModelConfigRepository:
    def __init__(self) -> None:
        self._next_id = 1

    def save(self, item: dict[str, object]) -> dict[str, object]:
        saved = dict(item)
        saved.setdefault("id", f"cfg-{self._next_id}")
        self._next_id += 1
        return saved

    def list_all(self) -> list[dict[str, object]]:
        return []

    def get(self, item_id) -> dict[str, object] | None:  # pragma: no cover - unused in these tests
        return None

    def update(self, item_id, item: dict[str, object]) -> dict[str, object] | None:  # pragma: no cover - unused
        return None


class LegacyModelFamily(Enum):
    HMM_REGIME_SWITCHING = "hmm_regime_switching"


def _build_service() -> ModelConfigService:
    registry = ModelRegistry()
    registry.register(HmmRegimeSwitchingModelSpec())
    return ModelConfigService(_InMemoryModelConfigRepository(), registry)


def _valid_hmm_payload() -> dict[str, Any]:
    return {
        "n_states": 3,
        "lookback_window": 252,
        "covariance_type": "diag",
        "convergence_tol": 0.001,
        "max_iterations": 200,
    }


def test_create_model_config_accepts_enum_member_model_family() -> None:
    service = _build_service()

    created = service.create(LegacyModelFamily.HMM_REGIME_SWITCHING, _valid_hmm_payload())  # type: ignore[arg-type]

    assert created["model_family"] == "hmm_regime_switching"
    assert created["config"]["n_states"] == 3


def test_create_model_config_accepts_enum_repr_style_model_family_string() -> None:
    service = _build_service()

    created = service.create("ModelFamily.HMM_REGIME_SWITCHING", _valid_hmm_payload())

    assert created["model_family"] == "hmm_regime_switching"
    assert created["config"]["lookback_window"] == 252
