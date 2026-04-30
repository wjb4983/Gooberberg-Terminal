from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "scripts" / "check-training-model-metadata-consistency.py"

spec = importlib.util.spec_from_file_location("training_metadata_checker", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class _Capability:
    def __init__(self, task: str, subtask: str) -> None:
        self.task = task
        self.subtask = subtask


class _Metadata:
    def __init__(self, model_name: str, implemented: bool, capabilities: tuple[_Capability, ...]) -> None:
        self.model_name = model_name
        self.implemented = implemented
        self.capabilities = capabilities


def test_checker_reports_missing_adapter_and_missing_contract_tests() -> None:
    metadata = [
        _Metadata("good_model", True, (_Capability("forecasting", "univariate"),)),
        _Metadata("missing_adapter", True, (_Capability("forecasting", "univariate"),)),
    ]
    adapters = {"good_model": object()}
    test_functions = set()

    errors = module.check_consistency(metadata=metadata, adapters=adapters, test_functions=test_functions)

    assert "missing adapter: model_id='missing_adapter'" in errors
    assert (
        "missing contract-test coverage: "
        "model_id='good_model', expected_test='test_adapter_contract_suite_and_matrix_output'"
    ) in errors


def test_checker_reports_missing_task_subtask_declarations() -> None:
    metadata = [
        _Metadata("empty_caps", True, ()),
        _Metadata("missing_subtask", True, (_Capability("forecasting", ""),)),
    ]
    adapters = {"empty_caps": object(), "missing_subtask": object()}
    test_functions = {"test_adapter_contract_suite_and_matrix_output"}

    errors = module.check_consistency(metadata=metadata, adapters=adapters, test_functions=test_functions)

    assert "missing task/subtask declarations: model_id='empty_caps'" in errors
    assert "missing task/subtask declarations: model_id='missing_subtask'" in errors
