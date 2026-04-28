import json
from pathlib import Path

import pytest

from app.schemas.task_catalog import TaskDefinition, parse_task_definitions


CATALOG_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "domain" / "task_catalog" / "catalog" / "default_tasks.json"
)


def test_task_definition_schema_validates_catalog_fixture_samples() -> None:
    payload = json.loads(CATALOG_FIXTURE_PATH.read_text(encoding="utf-8"))

    definitions = parse_task_definitions(payload)

    assert definitions
    assert all(isinstance(definition, TaskDefinition) for definition in definitions)
    assert all(definition.compatibility_references for definition in definitions)


def test_task_definition_schema_rejects_missing_required_field() -> None:
    payload = {
        "task_type": "demo",
        "description": "x",
        "compatibility_references": ["dataset.demo"],
    }

    with pytest.raises(ValueError, match=r"subtask_type"):
        parse_task_definitions(payload)
