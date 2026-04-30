from worker_training.adapters.phase3 import PHASE3_MODEL_METADATA
from worker_training.main import ADAPTERS, ADAPTER_REGISTRY, TrainingRunRequest
from worker_training.task_heads import TASK_HEAD_REGISTRY


def test_all_implemented_phase3_models_have_runnable_adapters() -> None:
    implemented = [m for m in PHASE3_MODEL_METADATA if m.implemented]
    adapter_names = set(ADAPTERS)

    assert implemented
    assert {m.model_name for m in implemented}.issubset(adapter_names)


def test_phase3_adapter_capabilities_resolve_task_heads() -> None:
    for metadata in PHASE3_MODEL_METADATA:
        if not metadata.implemented:
            continue

        for capability in metadata.capabilities:
            request = TrainingRunRequest.model_validate(
                {
                    "model_name": metadata.model_name,
                    "model_family": metadata.model_family,
                    "task": capability.task,
                    "subtask": capability.subtask,
                    "data_type": capability.data_type,
                }
            )
            adapter = ADAPTER_REGISTRY.resolve(request)
            head = TASK_HEAD_REGISTRY.resolve(capability.task, capability.subtask)

            assert adapter.name == metadata.model_name
            assert head.task == capability.task
            assert head.subtask == capability.subtask


def test_phase3_model_metadata_declares_capabilities() -> None:
    for metadata in PHASE3_MODEL_METADATA:
        assert metadata.capabilities
        for capability in metadata.capabilities:
            assert capability.task
            assert capability.subtask
            assert capability.data_type
