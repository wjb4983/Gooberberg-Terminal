from uuid import UUID

from fastapi import APIRouter, status

from app.schemas import JobCreateRequest, JobResponse, JobStatusResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_job(job_request: JobCreateRequest) -> JobResponse:
    return JobResponse(
        job_type=job_request.job_type,
        payload=job_request.payload,
        status="accepted",
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: UUID) -> JobStatusResponse:
    return JobStatusResponse(
        id=job_id,
        status="pending",
        detail="placeholder: fetch from persistent job store not implemented",
    )
