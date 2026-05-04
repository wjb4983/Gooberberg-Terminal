from __future__ import annotations

from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, Request as FastAPIRequest

from app.api.dependencies import get_model_catalog_registry, get_market_data_service, get_model_config_service, get_training_run_service
from app.api.routers.training_runs import create_training_run
from app.domain.model_catalog import ModelCatalogRegistry
from app.schemas import (
    ExternalServicesStatusResponse,
    ModelLeaderboardEntry,
    ServiceConnectivityStatus,
    TrainingLaunchResponse,
    TrainingRunCreateRequest,
)
from app.domain.training_runs import TrainingRunService
from app.domain.model_configs import ModelConfigService
from app.domain.market_data import MarketDataService

router = APIRouter(prefix="/control-plane", tags=["control-plane"])


@router.post("/training/launch", response_model=TrainingLaunchResponse)
async def launch_training(
    payload: TrainingRunCreateRequest,
    request: FastAPIRequest,
    service: TrainingRunService = Depends(get_training_run_service),
    model_config_service: ModelConfigService = Depends(get_model_config_service),
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> TrainingLaunchResponse:
    run = await create_training_run(payload, request, service, model_config_service, market_data_service)
    return TrainingLaunchResponse(
        run=run,
        job_id=run.job_id,
        tracking={"job": f"/api/v1/jobs/{run.job_id}", "run": f"/api/v1/training-runs/{run.id}"},
    )


@router.get("/models/leaderboard", response_model=list[ModelLeaderboardEntry])
async def model_leaderboard(
    model_catalog_registry: ModelCatalogRegistry = Depends(get_model_catalog_registry),
) -> list[ModelLeaderboardEntry]:
    entries = sorted(model_catalog_registry.list_entries(), key=lambda item: item.metadata.model_name)
    return [
        ModelLeaderboardEntry(
            model_family=item.metadata.model_family,
            model_name=item.metadata.model_name,
            score=float(max(0, 100 - (index * 3))),
            rank=index + 1,
            metadata={"compute_intensity": item.metadata.compute_intensity.value},
        )
        for index, item in enumerate(entries)
    ]


def _probe_service(name: str, mode: str, endpoint: str | None) -> ServiceConnectivityStatus:
    if not endpoint:
        return ServiceConnectivityStatus(service=name, mode=mode, connected=False, status="not_connected", detail="service endpoint is not configured")
    request = Request(endpoint, method="GET")
    try:
        with urlopen(request, timeout=2.5) as response:  # noqa: S310
            code = getattr(response, "status", 200)
            return ServiceConnectivityStatus(service=name, mode=mode, connected=True, status="connected", detail="upstream service reachable", endpoint=endpoint, upstream_http_status=code, checked_at=datetime.now(UTC))
    except HTTPError as exc:
        return ServiceConnectivityStatus(service=name, mode=mode, connected=False, status="degraded", detail="upstream returned http error", endpoint=endpoint, upstream_http_status=exc.code, checked_at=datetime.now(UTC))
    except URLError:
        return ServiceConnectivityStatus(service=name, mode=mode, connected=False, status="not_connected", detail="failed to reach upstream endpoint", endpoint=endpoint, checked_at=datetime.now(UTC))


@router.get("/services/external-status", response_model=ExternalServicesStatusResponse)
async def get_external_services_status(request: FastAPIRequest) -> ExternalServicesStatusResponse:
    settings = request.app.state.settings
    paper_endpoint = getattr(settings, "paper_service_status_url", None)
    live_endpoint = getattr(settings, "live_service_status_url", None)
    paper = _probe_service("service-inference-paper", "paper", paper_endpoint)
    live = _probe_service("service-inference-live", "live", live_endpoint)
    return ExternalServicesStatusResponse(paper=paper, live=live)
