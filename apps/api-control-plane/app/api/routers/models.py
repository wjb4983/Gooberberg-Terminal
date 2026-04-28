import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_model_catalog_registry, get_model_registry
from app.api.routers.ws import manager as ws_manager
from app.domain.model_catalog import ModelCatalogRegistry
from app.domain.model_registry import ModelRegistry
from app.schemas import (
    ModelDeployment,
    ModelCatalogItem,
    ModelDeploymentActionResponse,
    ModelDeploymentCreateRequest,
    ModelDeploymentEvent,
    ModelDeploymentStatus,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/models/deployments", tags=["models"])

_deployments: dict[UUID, ModelDeployment] = {}


@router.get("/families", response_model=list[str])
async def list_model_families(model_registry: ModelRegistry = Depends(get_model_registry)) -> list[str]:
    return list(model_registry.list_families())


async def _broadcast_model_event(
    deployment: ModelDeployment,
    event_type: str,
    detail: str,
    previous_status: ModelDeploymentStatus | None,
) -> None:
    event = ModelDeploymentEvent(
        deployment_id=deployment.id,
        model_name=deployment.model_name,
        model_version=deployment.model_version,
        artifact_ref=deployment.artifact_ref,
        status=deployment.status,
        previous_status=previous_status,
        event_type=event_type,
        detail=detail,
        updated_at=deployment.updated_at,
    )

    payload = event.model_dump(mode="json")
    await ws_manager.publish_topic(topic="models", payload=payload)
    await ws_manager.publish_topic(
        topic="logs",
        payload={
            "timestamp": deployment.updated_at.isoformat(),
            "service": "api-control-plane",
            "level": "info",
            "trace_id": str(deployment.id),
            "message": detail,
            "category": "models",
            "fields": {
                "deployment_id": str(deployment.id),
                "status": deployment.status.value,
                "model_name": deployment.model_name,
                "model_version": deployment.model_version,
            },
        },
    )




@router.get("/catalog", response_model=list[ModelCatalogItem])
async def list_model_catalog(
    model_catalog_registry: ModelCatalogRegistry = Depends(get_model_catalog_registry),
) -> list[ModelCatalogItem]:
    return [
        ModelCatalogItem(
            model_family=item.metadata.model_family,
            model_name=item.metadata.model_name,
            description=item.metadata.description,
            tags=list(item.metadata.tags),
            validator_adapter=item.validator_adapter.model_family,
        )
        for item in model_catalog_registry.list_entries()
    ]


@router.get("/catalog/{model_family}", response_model=ModelCatalogItem)
async def get_model_catalog_item(
    model_family: str,
    model_catalog_registry: ModelCatalogRegistry = Depends(get_model_catalog_registry),
) -> ModelCatalogItem:
    item = model_catalog_registry.get(model_family)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model catalog entry not found")

    return ModelCatalogItem(
        model_family=item.metadata.model_family,
        model_name=item.metadata.model_name,
        description=item.metadata.description,
        tags=list(item.metadata.tags),
        validator_adapter=item.validator_adapter.model_family,
    )


@router.get("", response_model=list[ModelDeployment])
async def list_model_deployments() -> list[ModelDeployment]:
    return sorted(_deployments.values(), key=lambda item: item.created_at, reverse=True)


@router.post(
    "",
    response_model=ModelDeployment,
    status_code=status.HTTP_201_CREATED,
)
async def create_model_deployment(payload: ModelDeploymentCreateRequest) -> ModelDeployment:
    timestamp = datetime.now(UTC)
    deployment = ModelDeployment(
        id=uuid4(),
        model_name=payload.model_name,
        model_version=payload.model_version,
        artifact_ref=payload.artifact_ref,
        status=ModelDeploymentStatus.DEPLOYING,
        created_at=timestamp,
        updated_at=timestamp,
    )
    _deployments[deployment.id] = deployment
    await _broadcast_model_event(
        deployment,
        event_type="created",
        detail="model deployment created and queued for activation",
        previous_status=None,
    )
    return deployment


@router.post("/{deployment_id}/activate", response_model=ModelDeploymentActionResponse)
async def activate_model_deployment(deployment_id: UUID) -> ModelDeploymentActionResponse:
    deployment = _deployments.get(deployment_id)
    if deployment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model deployment not found")

    if deployment.status == ModelDeploymentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="model deployment is already active",
        )

    previous_status = deployment.status
    deployment.status = ModelDeploymentStatus.ACTIVE
    deployment.updated_at = datetime.now(UTC)

    detail = "model deployment activated"
    await _broadcast_model_event(
        deployment,
        event_type="status_changed",
        detail=detail,
        previous_status=previous_status,
    )
    return ModelDeploymentActionResponse(deployment=deployment, detail=detail)


@router.post("/{deployment_id}/deactivate", response_model=ModelDeploymentActionResponse)
async def deactivate_model_deployment(deployment_id: UUID) -> ModelDeploymentActionResponse:
    deployment = _deployments.get(deployment_id)
    if deployment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model deployment not found")

    if deployment.status == ModelDeploymentStatus.INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="model deployment is already inactive",
        )

    previous_status = deployment.status
    deployment.status = ModelDeploymentStatus.INACTIVE
    deployment.updated_at = datetime.now(UTC)

    detail = "model deployment deactivated"
    await _broadcast_model_event(
        deployment,
        event_type="status_changed",
        detail=detail,
        previous_status=previous_status,
    )
    return ModelDeploymentActionResponse(deployment=deployment, detail=detail)
