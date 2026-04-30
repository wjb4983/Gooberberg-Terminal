from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.persistence.models import BacktestRunRow, ParameterSweepRunRow, RunArtifactRow, TestingRunRow, TrainingRunRow

router = APIRouter(prefix="/runs", tags=["runs"])

LINEAGE_SCHEMA_VERSION = "v1"


def _find_run(request: Request, run_id: UUID):
    with request.app.state.database.session_factory() as session:
        models = (TrainingRunRow, BacktestRunRow, TestingRunRow, ParameterSweepRunRow)
        for model in models:
            row = session.get(model, str(run_id))
            if row is not None:
                return row, model.__tablename__
    return None, None


@router.get("/{run_id}/lineage")
async def get_run_lineage(run_id: UUID, request: Request) -> dict[str, object]:
    run_row, run_table = _find_run(request, run_id)
    if run_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    canonical_lineage = {
        "lineage_version": run_row.lineage_version,
        "lineage_status": run_row.lineage_status,
        "lineage_error_code": run_row.lineage_error_code,
        "dataset_fingerprint": run_row.dataset_fingerprint,
        "code_hash": run_row.code_hash,
        "config_digest": run_row.config_digest,
        "seed": run_row.seed,
    }
    return {"run_id": str(run_id), "run_type": run_table, "schema_version": LINEAGE_SCHEMA_VERSION, "lineage": canonical_lineage}


@router.get("/{run_id}/artifacts")
async def get_run_artifacts(run_id: UUID, request: Request) -> dict[str, object]:
    run_row, run_table = _find_run(request, run_id)
    if run_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    with request.app.state.database.session_factory() as session:
        artifact_rows = session.execute(
            select(RunArtifactRow).where(RunArtifactRow.run_id == str(run_id)).order_by(RunArtifactRow.created_at.asc())
        ).scalars()
        entries = [
            {
                "id": row.id,
                "artifact_role": row.artifact_role,
                "artifact_ref": row.artifact_ref,
                "artifact_uri": row.artifact_uri,
                "created_at": row.created_at.isoformat(),
            }
            for row in artifact_rows
        ]
        integrity = [
            {
                "artifact_id": row.id,
                "checksum": row.checksum,
                "sha256": row.sha256,
                "signature": row.signature,
                "size_bytes": row.size_bytes,
            }
            for row in session.execute(
                select(RunArtifactRow).where(RunArtifactRow.run_id == str(run_id)).order_by(RunArtifactRow.created_at.asc())
            ).scalars()
        ]
    return {"run_id": str(run_id), "run_type": run_table, "manifest_entries": entries, "integrity_metadata": integrity}


@router.get("/{run_id}/replay")
async def get_run_replay_bundle(run_id: UUID, request: Request) -> dict[str, object]:
    run_row, run_table = _find_run(request, run_id)
    if run_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    dataset_reference = getattr(run_row, "dataset_id", None) or getattr(run_row, "data_snapshot_id", None)
    normalized_config = getattr(run_row, "parameters", None) or getattr(run_row, "resolved_config", None) or {}
    seed = run_row.seed
    prerequisites_missing: list[str] = []
    if not dataset_reference:
        prerequisites_missing.append("dataset_reference")
    if not run_row.code_hash:
        prerequisites_missing.append("code_hash")
    if not run_row.config_digest:
        prerequisites_missing.append("config_digest")
    if seed is None:
        prerequisites_missing.append("seed")
    integrity_attestations = {
        "lineage_status": run_row.lineage_status,
        "lineage_version": run_row.lineage_version,
        "artifact_count": len(request.app.state.job_event_repository.list_artifact_summaries(UUID(run_row.job_id))),
    }
    return {
        "run_id": str(run_id),
        "run_type": run_table,
        "replay_bundle": {
            "dataset_reference": dataset_reference,
            "code_hash": run_row.code_hash,
            "normalized_config": normalized_config,
            "seed": seed,
        },
        "integrity_attestations": integrity_attestations,
        "missing_prerequisites": prerequisites_missing,
    }
