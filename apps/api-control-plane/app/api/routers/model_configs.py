from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from app.api.dependencies import get_model_config_service
from app.api.error_mapping import execute_model_config_service_call
from app.domain.model_configs import ModelConfigService
from app.schemas import ModelConfigCreateRequest, ModelConfigResponse, ModelConfigUpdateRequest

router = APIRouter(prefix="/model-configs", tags=["model-configs"])


def _to_model_config_response(*, route_context: str, payload: dict[str, object]) -> ModelConfigResponse:
    try:
        return ModelConfigResponse.model_validate(payload)
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{route_context}: persisted model config payload is malformed",
        ) from error


@router.post("", response_model=ModelConfigResponse, status_code=status.HTTP_201_CREATED)
def create_model_config(
    payload: ModelConfigCreateRequest,
    service: ModelConfigService = Depends(get_model_config_service),
) -> ModelConfigResponse:
    created = execute_model_config_service_call(
        route_context="POST /api/v1/model-configs",
        model_family=str(payload.model_family),
        operation=lambda: service.create(payload.model_family, payload.config),
    )
    return _to_model_config_response(route_context="POST /api/v1/model-configs", payload=created)


@router.get("", response_model=list[ModelConfigResponse])
def list_model_configs(service: ModelConfigService = Depends(get_model_config_service)) -> list[ModelConfigResponse]:
    return [
        _to_model_config_response(route_context="GET /api/v1/model-configs", payload=item)
        for item in service.list_all()
    ]


@router.get("/{model_config_id}", response_model=ModelConfigResponse)
def get_model_config(
    model_config_id: UUID,
    service: ModelConfigService = Depends(get_model_config_service),
) -> ModelConfigResponse:
    item = service.get(model_config_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model config not found")
    return _to_model_config_response(
        route_context=f"GET /api/v1/model-configs/{model_config_id}",
        payload=item,
    )


@router.put("/{model_config_id}", response_model=ModelConfigResponse)
def update_model_config(
    model_config_id: UUID,
    payload: ModelConfigUpdateRequest,
    service: ModelConfigService = Depends(get_model_config_service),
) -> ModelConfigResponse:
    existing = service.get(model_config_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model config not found")

    model_family = str(existing["model_family"])
    item = execute_model_config_service_call(
        route_context=f"PUT /api/v1/model-configs/{model_config_id}",
        model_family=model_family,
        operation=lambda: service.update(model_config_id, payload.config),
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model config not found")
    return _to_model_config_response(
        route_context=f"PUT /api/v1/model-configs/{model_config_id}",
        payload=item,
    )
