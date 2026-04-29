from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_checker_module():
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "check-model-adapter-consistency.py"
    spec = importlib.util.spec_from_file_location("check_model_adapter_consistency", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_checker_reports_implemented_models_missing_adapters() -> None:
    module = _load_checker_module()

    errors = module.check_consistency(
        catalog_implemented_ids={"phase1-001", "phase1-002"},
        catalog_all_ids={"phase1-001", "phase1-002"},
        adapter_ids={"phase1-001"},
    )

    assert "model_id='phase1-002'" in errors[0]


def test_checker_reports_adapters_missing_catalog_entries() -> None:
    module = _load_checker_module()

    errors = module.check_consistency(
        catalog_implemented_ids={"phase1-001"},
        catalog_all_ids={"phase1-001"},
        adapter_ids={"phase1-001", "phase1-999"},
    )

    assert any("adapter exists without catalog entry" in err for err in errors)
    assert any("model_id='phase1-999'" in err for err in errors)


def test_checker_passes_when_sets_match() -> None:
    module = _load_checker_module()

    errors = module.check_consistency(
        catalog_implemented_ids={"phase1-001", "phase1-002"},
        catalog_all_ids={"phase1-001", "phase1-002"},
        adapter_ids={"phase1-001", "phase1-002"},
    )

    assert errors == []
