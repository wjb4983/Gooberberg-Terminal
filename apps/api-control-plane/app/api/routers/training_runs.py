from datetime import UTC, date, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import (
    get_market_data_service,
    get_model_config_service,
    get_training_run_service,
)
from app.api.routers.jobs import _broadcast_job_event
from app.core.logging import request_id_ctx_var
from app.domain.market_data import Service as MarketDataService
from app.domain.model_configs.compatibility import (
    resolve_dataset_compatibility,
    validate_model_dataset_compatibility,
)
from app.domain.model_configs.service import ModelConfigService
from app.domain.training_runs import Service as TrainingRunService
from app.jobs.models import JobEnvelope, JobLifecycleEvent, JobStatus
from app.jobs.store import job_state_store, job_submission_store
from app.schemas import MarketDataIngestionRequest, TrainingRunCreateRequest, TrainingRunResponse
from app.schemas.run_constraints import attach_constraints_to_parameters

router = APIRouter(prefix="/training-runs", tags=["training-runs"])


def _resolve_required_window(dataset_metadata: dict[str, object]) -> tuple[date, date]:
    start_raw = dataset_metadata.get("start_date")
    end_raw = dataset_metadata.get("end_date")
    if not isinstance(start_raw, str) or not isinstance(end_raw, str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="dataset metadata is missing required start_date/end_date",
        )
    try:
        return date.fromisoformat(start_raw), date.fromisoformat(end_raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="dataset metadata has invalid start_date/end_date format",
        ) from exc


def _resolve_dataset_symbols(dataset_symbol: str, dataset_metadata: dict[str, object]) -> list[str]:
    symbols = dataset_metadata.get("symbols")
    if isinstance(symbols, list):
        normalized = [item for item in symbols if isinstance(item, str) and item]
        if normalized:
            return normalized
    return [dataset_symbol]


def _resolve_dataset_resolutions(dataset_timeframe: str, dataset_metadata: dict[str, object]) -> list[str]:
    resolutions = dataset_metadata.get("resolutions")
    if isinstance(resolutions, list):
        normalized = [item for item in resolutions if isinstance(item, str) and item]
        if normalized:
            return normalized
    return [dataset_timeframe]


def _resolve_member_count(dataset_metadata: dict[str, object], fallback_count: int) -> int:
    raw_members = dataset_metadata.get("universe_members")
    if isinstance(raw_members, list):
        member_count = len([item for item in raw_members if isinstance(item, str) and item])
        if member_count > 0:
            return member_count
    return fallback_count


def _build_missing_chunks(
    market_data_service: MarketDataService,
    *,
    symbols: list[str],
    resolutions: list[str],
    required_start: date,
    required_end: date,
) -> list[tuple[str, str]]:
    missing_chunks: list[tuple[str, str]] = []
    for symbol in symbols:
        for resolution in resolutions:
            coverage = market_data_service.get_cache_coverage(symbol=symbol, timeframe=resolution)
            if (
                coverage.available_start is None
                or coverage.available_end is None
                or coverage.available_start > required_start
                or coverage.available_end < required_end
            ):
                missing_chunks.append((symbol, resolution))
    return missing_chunks


@router.post("", response_model=TrainingRunResponse, status_code=status.HTTP_201_CREATED)
async def create_training_run(
    payload: TrainingRunCreateRequest,
    request: Request,
    service: TrainingRunService = Depends(get_training_run_service),
    model_config_service: ModelConfigService = Depends(get_model_config_service),
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> TrainingRunResponse:
    model_config = model_config_service.get(payload.model_config_id)
    if model_config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model config not found")

    dataset = market_data_service.lookup_dataset(payload.dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="dataset not found; ingest data and retry",
        )

    model_spec = request.app.state.model_registry.require(str(model_config["model_family"]))
    dataset_profile = resolve_dataset_compatibility(dataset.metadata, dataset.timeframe)
    compatibility_errors = validate_model_dataset_compatibility(
        model_spec=model_spec, dataset_metadata=dataset_profile
    )
    if compatibility_errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "model config is incompatible with dataset",
                "errors": compatibility_errors,
            },
        )

    run_id = uuid4()
    job_id = uuid4()
    accepted_at = datetime.now(UTC)
    trace_id = request_id_ctx_var.get() or str(uuid4())
    symbols = _resolve_dataset_symbols(dataset.symbol, dataset.metadata)
    resolutions = _resolve_dataset_resolutions(dataset.timeframe, dataset.metadata)
    attached_parameters = attach_constraints_to_parameters(
        parameters=payload.parameters,
        constraints=payload.constraints,
    )

    serialized_dataset_spec = dataset.metadata.get("dataset_spec")
    if isinstance(serialized_dataset_spec, str) and serialized_dataset_spec:
        dataset_spec_hash = sha256(serialized_dataset_spec.encode("utf-8")).hexdigest()
    else:
        dataset_spec_hash = sha256(payload.dataset_id.encode("utf-8")).hexdigest()

    dataset_manifest_version_raw = dataset.metadata.get("manifest_version")
    dataset_manifest_version = (
        str(dataset_manifest_version_raw) if isinstance(dataset_manifest_version_raw, str) else "v1"
    )
    model_config_payload = model_config.get("config")
    model_config_data = model_config_payload if isinstance(model_config_payload, dict) else {}
    model_config_version_raw = model_config_data.get("version_tag")
    model_config_version_tag = str(model_config_version_raw) if isinstance(model_config_version_raw, str) else "unknown"
    run_metadata_payload = attached_parameters.get("run_metadata")
    run_metadata = run_metadata_payload if isinstance(run_metadata_payload, dict) else {}
    constraint_profile_version_raw = run_metadata.get("constraint_profile_version")
    constraint_profile_version = (
        str(constraint_profile_version_raw) if isinstance(constraint_profile_version_raw, str) else "v1"
    )
    resolved_symbol_count = len(symbols)
    resolved_member_count = _resolve_member_count(dataset.metadata, resolved_symbol_count)

    created = service.create(
        {
            "id": str(run_id),
            "job_id": str(job_id),
            "model_config_id": str(payload.model_config_id),
            "dataset_id": payload.dataset_id,
            "dataset_spec_hash": dataset_spec_hash,
            "dataset_manifest_version": dataset_manifest_version,
            "resolved_symbol_count": resolved_symbol_count,
            "resolved_member_count": resolved_member_count,
            "model_config_version_tag": model_config_version_tag,
            "task_type": payload.task_type.value,
            "subtask_type": payload.subtask_type.value,
            "constraint_profile_version": constraint_profile_version,
            "parameters": attached_parameters,
            "status": "queued",
            "created_at": accepted_at,
        }
    )

    envelope = JobEnvelope(
        job_id=job_id,
        trace_id=trace_id,
        job_type="training",
        run_id=run_id,
        run_type="training",
        payload={"run_id": str(run_id), **payload.model_dump(mode="json")},
        queued_at=accepted_at,
    )
    queued_event = JobLifecycleEvent(
        job_id=job_id,
        trace_id=trace_id,
        status=JobStatus.QUEUED,
        detail="training run accepted by api-control-plane",
        run_id=run_id,
        run_type="training",
        progress_pct=0.0,
        message="queued",
        updated_at=accepted_at,
    )
    job_state_store.upsert(queued_event)
    job_submission_store.upsert(envelope)
    request.app.state.job_event_repository.persist_event(queued_event)
    await _broadcast_job_event(queued_event)

    required_start, required_end = _resolve_required_window(dataset.metadata)
    missing_chunks = _build_missing_chunks(
        market_data_service,
        symbols=symbols,
        resolutions=resolutions,
        required_start=required_start,
        required_end=required_end,
    )

    if missing_chunks:
        by_resolution: dict[str, set[str]] = {}
        for symbol, resolution in missing_chunks:
            by_resolution.setdefault(resolution, set()).add(symbol)

        for resolution, missing_symbols in by_resolution.items():
            market_data_service.request_ingestion(
                MarketDataIngestionRequest(
                    provider=str(dataset.metadata.get("provider") or "massive"),
                    asset_class=str(dataset.metadata.get("asset_class") or "stocks"),
                    universe_members=sorted(missing_symbols),
                    resolutions=[resolution],
                    feature_recipe_version=str(dataset.metadata.get("feature_recipe_version") or "v1"),
                    label_recipe_version=str(dataset.metadata.get("label_recipe_version") or "v1"),
                    start_date=required_start,
                    end_date=required_end,
                )
            )

        service.update_status(run_id, "waiting_for_data")
        created["status"] = "waiting_for_data"
        waiting_event = JobLifecycleEvent(
            job_id=job_id,
            trace_id=trace_id,
            status=JobStatus.WAITING_FOR_DATA,
            detail="waiting for market data ingestion",
            run_id=run_id,
            run_type="training",
            progress_pct=1.0,
            message="waiting_for_data",
            updated_at=datetime.now(UTC),
        )
        job_state_store.upsert(waiting_event)
        request.app.state.job_event_repository.persist_event(waiting_event)
        await _broadcast_job_event(waiting_event)

    await request.app.state.job_queue.enqueue(envelope)
    return TrainingRunResponse.model_validate(created)


@router.get("", response_model=list[TrainingRunResponse])
def list_training_runs(
    service: TrainingRunService = Depends(get_training_run_service),
) -> list[TrainingRunResponse]:
    return [TrainingRunResponse.model_validate(item) for item in service.list_all()]


@router.get("/{run_id}", response_model=TrainingRunResponse)
def get_training_run(
    run_id: UUID, service: TrainingRunService = Depends(get_training_run_service)
) -> TrainingRunResponse:
    run = service.get(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="training run not found")
    return TrainingRunResponse.model_validate(run)
