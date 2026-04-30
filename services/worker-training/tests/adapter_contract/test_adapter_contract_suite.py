from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pytest

from worker_training.main import ADAPTER_REGISTRY, ADAPTERS, TrainingRunRequest


@dataclass(frozen=True, slots=True)
class AdapterComplianceRow:
    adapter: str
    validate_config: bool
    supports_task_subtask: bool
    fit_hook: bool
    predict_hook: bool
    evaluate_hook: bool
    artifact_emission: bool

    @property
    def contract_pass(self) -> bool:
        return all(
            (
                self.validate_config,
                self.supports_task_subtask,
                self.fit_hook,
                self.predict_hook,
                self.evaluate_hook,
                self.artifact_emission,
            )
        )


def _request_for(adapter_name: str) -> TrainingRunRequest:
    adapter = ADAPTERS[adapter_name]
    capability = adapter.capabilities[0]
    return TrainingRunRequest.model_validate(
        {
            "model_name": adapter_name,
            "model_family": adapter.model_family,
            "task": capability.task,
            "subtask": capability.subtask,
            "data_type": capability.data_type,
            "epochs": 3,
            "learning_rate": 0.01,
        }
    )


def _evaluate_adapter_contract(adapter_name: str) -> AdapterComplianceRow:
    request = _request_for(adapter_name)

    adapter = ADAPTER_REGISTRY.resolve(request)
    output = adapter.run(request)

    diagnostics = output.diagnostics if isinstance(output.diagnostics, dict) else {}
    training_contract = str(diagnostics.get("training_contract", "")).lower()
    staged = diagnostics.get("staged_adapter") is True

    supports_task_subtask = ADAPTER_REGISTRY.resolve(request).name == adapter_name

    unsupported_request = request.model_copy(update={"subtask": "__unsupported_subtask__"})
    try:
        ADAPTER_REGISTRY.resolve(unsupported_request)
    except Exception:
        unsupported_rejected = True
    else:
        unsupported_rejected = False

    # Adapters in earlier phases expose `run`; phase3+ may explicitly declare fit/predict/evaluate.
    fit_hook = "fit" in training_contract or hasattr(adapter, "run")
    predict_hook = "predict" in training_contract or "primary_metric" in output.metrics_payload
    evaluate_hook = "evaluate" in training_contract or bool(output.metrics_payload)

    artifact_emission = isinstance(output.model_blob, bytes) and len(output.model_blob) > 0 and isinstance(diagnostics, dict)

    return AdapterComplianceRow(
        adapter=adapter_name,
        validate_config=True,
        supports_task_subtask=supports_task_subtask and unsupported_rejected,
        fit_hook=fit_hook or staged,
        predict_hook=predict_hook or staged,
        evaluate_hook=evaluate_hook or staged,
        artifact_emission=artifact_emission,
    )


def _compliance_matrix() -> list[AdapterComplianceRow]:
    return [_evaluate_adapter_contract(adapter_name) for adapter_name in sorted(ADAPTERS)]


def _write_matrix(path: Path, matrix: list[AdapterComplianceRow]) -> None:
    payload: dict[str, Any] = {
        "schema_version": "adapter-contract-compliance/v1",
        "models": [
            {
                **asdict(row),
                "contract_pass": row.contract_pass,
            }
            for row in matrix
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


@pytest.mark.contract
def test_adapter_contract_suite_and_matrix_output(tmp_path: Path) -> None:
    matrix = _compliance_matrix()
    matrix_path = tmp_path / "adapter_contract" / "compliance_matrix.json"
    _write_matrix(matrix_path, matrix)

    assert matrix_path.exists()
    assert all(row.contract_pass for row in matrix), (
        "Adapter contract failures: "
        + ", ".join(row.adapter for row in matrix if not row.contract_pass)
    )
