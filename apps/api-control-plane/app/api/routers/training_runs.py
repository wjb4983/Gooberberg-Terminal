from datetime import UTC, date, datetime
import logging
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
    resolve_dataset_requirement,
    validate_model_dataset_compatibility,
)
from app.domain.model_configs.service import ModelConfigService
from app.domain.training_runs import Service as TrainingRunService
from app.domain.training_runs.dataset_qualification import QualificationContext, qualify_dataset_for_training
from app.domain.task_definitions import get_task_subtask_definition
from app.domain.training_runs.validation_profiles import resolve_validation_profile
from app.jobs.models import JobEnvelope, JobLifecycleEvent, JobStatus
from app.jobs.store import job_state_store, job_submission_store
from app.schemas import (
    MarketDataIngestionRequest,
    TrainingIntent,
    TrainingRunCreateRequest,
    TrainingRunResponse,
    TrainingRunValidationRequest,
    TrainingRunValidationResponse,
    TrainingTemplate,
    TrainingTemplateCreateRequest,
)
from app.schemas.run_constraints import attach_constraints_to_parameters

router = APIRouter(prefix="/training-runs", tags=["training-runs"])
logger = logging.getLogger(__name__)
_training_templates: dict[str, TrainingTemplate] = {}


@router.get("/templates", response_model=list[TrainingTemplate])
def list_training_templates() -> list[TrainingTemplate]:
    return sorted(_training_templates.values(), key=lambda item: item.created_at, reverse=True)


@router.post("/templates", response_model=TrainingTemplate, status_code=status.HTTP_201_CREATED)
def create_training_template(payload: TrainingTemplateCreateRequest) -> TrainingTemplate:
    template = TrainingTemplate(
        name=payload.name,
        task_type=payload.task_type,
        subtask_type=payload.subtask_type,
        validation_profile=payload.validation_profile,
        dataset_constraints=payload.dataset_constraints,
        parameter_preset=payload.parameter_preset,
    )
    _training_templates[str(template.id)] = template
    return template


def _resolve_required_window(dataset_metadata: dict[str, object]) -> tuple[date, date] | None:
    start_raw = dataset_metadata.get("start_date")
    end_raw = dataset_metadata.get("end_date")
    if not isinstance(start_raw, str) or not isinstance(end_raw, str):
        return None
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


def _build_validation_response(
    payload: TrainingRunValidationRequest,
    *,
    request: Request,
    model_config_service: ModelConfigService,
    market_data_service: MarketDataService,
) -> TrainingRunValidationResponse:
    warnings: list[str] = []
    errors: list[str] = []
    warning_details: list[dict[str, str]] = []
    error_details: list[dict[str, str]] = []
    compatible = True
    model_spec = None
    qualification_result = None

    model_config = model_config_service.get(payload.model_config_id)
    if model_config is None:
        errors.append("model config not found")
        error_details.append({"code": "model_config_not_found", "message": "model config not found"})
        compatible = False

    dataset_id = payload.dataset_id.strip()
    if dataset_id != payload.dataset_id:
        warnings.append("dataset_id was normalized by trimming surrounding whitespace")
        warning_details.append({"code": "dataset_id_normalized", "message": "dataset_id was normalized by trimming surrounding whitespace"})

    dataset = market_data_service.lookup_dataset(dataset_id)
    if dataset is None:
        errors.append("dataset not found; ingest data and retry")
        error_details.append({"code": "dataset_not_found", "message": "dataset not found; ingest data and retry"})
        compatible = False

    if model_config is not None and dataset is not None:
        model_spec = request.app.state.model_registry.require(str(model_config["model_family"]))
        dataset_profile = resolve_dataset_compatibility(dataset.metadata, dataset.timeframe)
        compatibility_errors = validate_model_dataset_compatibility(
            model_spec=model_spec,
            dataset_metadata=dataset_profile,
        )
        if compatibility_errors:
            compatible = False
            for error in compatibility_errors:
                errors.append(f"compatibility: {error}")
                error_details.append({"code": "compatibility_error", "message": error})

        model_config_payload = model_config.get("config")
        qualification_result = qualify_dataset_for_training(
            context=QualificationContext(
                task_type=payload.task_type.value,
                subtask_type=payload.subtask_type.value,
                model_family=str(model_config["model_family"]),
                model_config=model_config_payload if isinstance(model_config_payload, dict) else {},
            ),
            dataset_metadata=dataset_profile,
            dataset_requirement=resolve_dataset_requirement(model_spec),
            raw_dataset_metadata=dataset.metadata,
        )
        if qualification_result.errors:
            compatible = False
            for issue in qualification_result.errors:
                errors.append(f"qualification[{issue.code}]: {issue.message}")
                error_details.append({"code": f"qualification_{issue.code}", "message": issue.message})
        for issue in qualification_result.warnings:
            warnings.append(f"qualification[{issue.code}]: {issue.message}")
            warning_details.append({"code": f"qualification_{issue.code}", "message": issue.message})

    normalized_payload = TrainingRunCreateRequest(
        task_type=payload.task_type,
        subtask_type=payload.subtask_type,
        model_config_id=payload.model_config_id,
        dataset_id=dataset_id,
        parameters=attach_constraints_to_parameters(
            parameters=payload.parameters,
            constraints=payload.constraints,
        ),
        constraints=payload.constraints,
    )
    model_family = str(model_config["model_family"]) if model_config is not None else "unknown"
    validation_profile = resolve_validation_profile(
        task_type=normalized_payload.task_type.value,
        subtask_type=normalized_payload.subtask_type.value,
        requested_profile=payload.validation_profile,
    )
    task_definition = get_task_subtask_definition(
        task_type=normalized_payload.task_type,
        subtask_type=normalized_payload.subtask_type,
    )
    metric_bundle = list(task_definition.default_metric_bundle)
    training_intent = TrainingIntent(
        task_type=normalized_payload.task_type,
        subtask_type=normalized_payload.subtask_type,
        model_family=model_family,
        model_config_id=normalized_payload.model_config_id,
        dataset_id=normalized_payload.dataset_id,
        parameter_set_id=None,
        validation_profile=validation_profile,
        override_parameters=dict(normalized_payload.parameters),
    )
    dataset_qualification_report = {
        "status": "passed" if qualification_result is not None and qualification_result.errors == () else "failed",
        "errors": [{"code": issue.code, "message": issue.message} for issue in (qualification_result.errors if qualification_result else ())],
        "warnings": [{"code": issue.code, "message": issue.message} for issue in (qualification_result.warnings if qualification_result else ())],
    } if model_config is not None and dataset is not None else {"status": "not_evaluated", "errors": [], "warnings": []}

    selected_adapter_capability = {
        "model_family": model_family,
        "supported_data_kinds": list(getattr(model_spec, "supported_data_kinds", ())) if model_config is not None else [],
        "required_index": getattr(model_spec, "required_index", None) if model_config is not None else None,
        "target_type": getattr(model_spec, "target_type", None) if model_config is not None else None,
    }

    return TrainingRunValidationResponse(
        normalized_payload=normalized_payload,
        training_intent=training_intent,
        resolved_task_head=task_definition.target_schema,
        resolved_validation_profile=validation_profile,
        dataset_qualification_report=dataset_qualification_report,
        selected_adapter_capability=selected_adapter_capability,
        expected_artifacts=["trained_model", "training_metrics", "run_metadata"],
        metric_bundle=metric_bundle,
        warnings=warnings,
        errors=errors,
        warning_details=warning_details,
        error_details=error_details,
        compatible=compatible,
        valid=len(errors) == 0,
    )


@router.post("/compatibility", response_model=TrainingRunValidationResponse)
def validate_training_run_compatibility(
    payload: TrainingRunValidationRequest,
    request: Request,
    model_config_service: ModelConfigService = Depends(get_model_config_service),
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> TrainingRunValidationResponse:
    return _build_validation_response(
        payload,
        request=request,
        model_config_service=model_config_service,
        market_data_service=market_data_service,
    )


@router.post("/preflight", response_model=TrainingRunValidationResponse)
def preflight_training_run(
    payload: TrainingRunValidationRequest,
    request: Request,
    model_config_service: ModelConfigService = Depends(get_model_config_service),
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> TrainingRunValidationResponse:
    return _build_validation_response(
        payload,
        request=request,
        model_config_service=model_config_service,
        market_data_service=market_data_service,
    )


@router.post("/templates/{template_id}/apply", response_model=TrainingRunValidationResponse)
def apply_training_template(
    template_id: UUID,
    payload: TrainingRunValidationRequest,
    request: Request,
    model_config_service: ModelConfigService = Depends(get_model_config_service),
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> TrainingRunValidationResponse:
    template = _training_templates.get(str(template_id))
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="template not found")
    merged = TrainingRunValidationRequest(
        task_type=template.task_type,
        subtask_type=template.subtask_type,
        model_config_id=payload.model_config_id,
        dataset_id=payload.dataset_id,
        validation_profile=template.validation_profile,
        parameters={**template.parameter_preset.parameters, **payload.parameters},
        constraints=payload.constraints,
    )
    return _build_validation_response(
        merged,
        request=request,
        model_config_service=model_config_service,
        market_data_service=market_data_service,
    )


@router.post("", response_model=TrainingRunResponse, status_code=status.HTTP_201_CREATED)
async def create_training_run(
    payload: TrainingRunCreateRequest,
    request: Request,
    service: TrainingRunService = Depends(get_training_run_service),
    model_config_service: ModelConfigService = Depends(get_model_config_service),
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> TrainingRunResponse:
    """Create a training run, emit initial lifecycle events, and enqueue worker execution."""
    validation = _build_validation_response(
        TrainingRunValidationRequest(**payload.model_dump(mode="python")),
        request=request,
        model_config_service=model_config_service,
        market_data_service=market_data_service,
    )
    if not validation.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "training run preflight failed",
                "errors": validation.errors,
            },
        )
    normalized_payload = validation.normalized_payload
    training_intent = validation.training_intent
    logger.info("normalized training intent", extra={"training_intent": training_intent.model_dump(mode="json")})
    assert normalized_payload.dataset_id

    model_config = model_config_service.get(normalized_payload.model_config_id)
    assert model_config is not None
    dataset = market_data_service.lookup_dataset(normalized_payload.dataset_id)
    assert dataset is not None

    run_id = uuid4()
    job_id = uuid4()
    accepted_at = datetime.now(UTC)
    trace_id = request_id_ctx_var.get() or str(uuid4())
    symbols = _resolve_dataset_symbols(dataset.symbol, dataset.metadata)
    resolutions = _resolve_dataset_resolutions(dataset.timeframe, dataset.metadata)
    attached_parameters = normalized_payload.parameters

    serialized_dataset_spec = dataset.metadata.get("dataset_spec")
    if isinstance(serialized_dataset_spec, str) and serialized_dataset_spec:
        dataset_spec_hash = sha256(serialized_dataset_spec.encode("utf-8")).hexdigest()
    else:
        dataset_spec_hash = sha256(normalized_payload.dataset_id.encode("utf-8")).hexdigest()

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
    run_metadata["training_intent"] = training_intent.model_dump(mode="json")
    attached_parameters["run_metadata"] = run_metadata
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
            "model_config_id": str(normalized_payload.model_config_id),
            "dataset_id": normalized_payload.dataset_id,
            "dataset_spec_hash": dataset_spec_hash,
            "dataset_manifest_version": dataset_manifest_version,
            "resolved_symbol_count": resolved_symbol_count,
            "resolved_member_count": resolved_member_count,
            "model_config_version_tag": model_config_version_tag,
            "task_type": normalized_payload.task_type.value,
            "subtask_type": normalized_payload.subtask_type.value,
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
        payload={"run_id": str(run_id), **normalized_payload.model_dump(mode="json")},
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

    required_window = _resolve_required_window(dataset.metadata)
    missing_chunks = (
        _build_missing_chunks(
            market_data_service,
            symbols=symbols,
            resolutions=resolutions,
            required_start=required_window[0],
            required_end=required_window[1],
        )
        if required_window is not None
        else []
    )

    if missing_chunks:
        assert required_window is not None
        required_start, required_end = required_window
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
