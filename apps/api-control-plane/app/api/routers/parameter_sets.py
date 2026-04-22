from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_parameter_set_service
from app.domain.parameter_sets import Service as ParameterSetService
from app.schemas import (
    ParameterSetCloneRequest,
    ParameterSetCreateRequest,
    ParameterSetResponse,
)

router = APIRouter(prefix="/parameter-sets", tags=["parameter-sets"])


@router.get("", response_model=list[ParameterSetResponse])
def list_parameter_sets(
    service: ParameterSetService = Depends(get_parameter_set_service),
) -> list[ParameterSetResponse]:
    return [ParameterSetResponse.model_validate(item) for item in service.list_all()]


@router.get("/{set_id}", response_model=ParameterSetResponse)
def get_parameter_set(
    set_id: UUID,
    service: ParameterSetService = Depends(get_parameter_set_service),
) -> ParameterSetResponse:
    item = service.get(set_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="parameter set not found")
    return ParameterSetResponse.model_validate(item)


@router.post("", response_model=ParameterSetResponse, status_code=status.HTTP_201_CREATED)
def create_parameter_set(
    payload: ParameterSetCreateRequest,
    service: ParameterSetService = Depends(get_parameter_set_service),
) -> ParameterSetResponse:
    created = service.create(payload.model_dump(mode="json"))
    return ParameterSetResponse.model_validate(created)


@router.post("/{set_id}/clone", response_model=ParameterSetResponse, status_code=status.HTTP_201_CREATED)
def clone_parameter_set(
    set_id: UUID,
    payload: ParameterSetCloneRequest,
    service: ParameterSetService = Depends(get_parameter_set_service),
) -> ParameterSetResponse:
    source = service.get(set_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="parameter set not found")

    now = datetime.now(UTC)
    next_payload: dict[str, object] = {
        "id": str(uuid4()),
        "model_config_id": str(source["model_config_id"]),
        "name": payload.name or f"{source['name']} (clone)",
        "parameters": payload.parameters if payload.parameters is not None else source["parameters"],
        "version_tag": payload.version_tag or f"{source['version_tag']}.clone.{now.strftime('%Y%m%d%H%M%S')}",
        "parent_set_id": str(source["id"]),
        "provenance_metadata": payload.provenance_metadata if payload.provenance_metadata is not None else source["provenance_metadata"],
        "created_at": now,
    }
    created = service.clone(next_payload)
    return ParameterSetResponse.model_validate(created)


@router.get("/{set_id}/versions", response_model=list[ParameterSetResponse])
def get_parameter_set_version_history(
    set_id: UUID,
    service: ParameterSetService = Depends(get_parameter_set_service),
) -> list[ParameterSetResponse]:
    item = service.get(set_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="parameter set not found")
    return [ParameterSetResponse.model_validate(version) for version in service.version_history(set_id)]
