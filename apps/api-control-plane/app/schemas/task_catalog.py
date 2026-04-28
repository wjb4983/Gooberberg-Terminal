from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class TaskDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_type: NonEmptyString
    subtask_type: NonEmptyString
    description: NonEmptyString
    compatibility_references: list[NonEmptyString] = Field(default_factory=list)
    references: list[NonEmptyString] = Field(default_factory=list)


def parse_task_definitions(payload: Any) -> tuple[TaskDefinition, ...]:
    if isinstance(payload, dict):
        raw_entries = [payload]
    elif isinstance(payload, list):
        raw_entries = payload
    else:
        raise ValueError("catalog payload must be an object or array of objects")

    definitions: list[TaskDefinition] = []
    for index, item in enumerate(raw_entries):
        if not isinstance(item, dict):
            raise ValueError(f"catalog item at index {index} must be an object")

        try:
            definitions.append(TaskDefinition.model_validate(item))
        except ValidationError as exc:
            raise ValueError(f"item index {index} failed schema validation: {exc}") from exc

    return tuple(definitions)
