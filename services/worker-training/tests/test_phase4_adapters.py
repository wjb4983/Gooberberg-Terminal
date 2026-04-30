from worker_training.adapters.phase4 import PHASE4_MODEL_METADATA
from worker_training.main import ADAPTERS, ADAPTER_REGISTRY, TrainingRunRequest
from worker_training.task_heads import TASK_HEAD_REGISTRY


def test_all_phase4_models_have_staged_adapters() -> None:
    adapter_names = set(ADAPTERS)
    assert PHASE4_MODEL_METADATA
    assert {m.model_name for m in PHASE4_MODEL_METADATA}.issubset(adapter_names)
    assert all(m.staged_adapter for m in PHASE4_MODEL_METADATA)


def test_phase4_adapter_capabilities_are_pipeline_compatible() -> None:
    for metadata in PHASE4_MODEL_METADATA:
        for capability in metadata.capabilities:
            request = TrainingRunRequest.model_validate(
                {
                    "model_name": metadata.model_name,
                    "model_family": metadata.model_family,
                    "task": capability.task,
                    "subtask": capability.subtask,
                    "data_type": capability.data_type,
                    "epochs": 7,
                }
            )
            adapter = ADAPTER_REGISTRY.resolve(request)
            TASK_HEAD_REGISTRY.resolve(capability.task, capability.subtask)
            output = adapter.run(request)

            assert adapter.name == metadata.model_name
            assert output.diagnostics["staged_adapter"] is True
            assert "experimental" in output.diagnostics["experimental_disclaimer"].lower()
            assert output.diagnostics["capability_limitations"]


def test_phase4_full_training_fallback_is_explicit() -> None:
    fallback_model = next(m for m in PHASE4_MODEL_METADATA if "full_training" not in m.supported_training_modes)
    request = TrainingRunRequest.model_validate(
        {
            "model_name": fallback_model.model_name,
            "model_family": fallback_model.model_family,
            "task": fallback_model.capabilities[0].task,
            "subtask": fallback_model.capabilities[0].subtask,
            "data_type": fallback_model.capabilities[0].data_type,
            "epochs": 10,
        }
    )
    output = ADAPTER_REGISTRY.resolve(request).run(request)

    assert output.diagnostics["requested_training_mode"] == "full_training"
    assert output.diagnostics["selected_training_mode"] == "feasibility"
    assert output.diagnostics["mode_fallback"] != "none"
