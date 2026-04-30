from app.core.config import get_settings
from app.core.pipeline_observability import PipelineResponseMeta, observe_pipeline_stage
from fastapi import APIRouter, Request

from app.schemas import PortfolioSnapshot

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/snapshot", response_model=PortfolioSnapshot)
async def get_portfolio_snapshot(request: Request) -> PortfolioSnapshot:
    settings = get_settings()
    fallback_reason = None if settings.portfolio_prod_snapshot_enabled else "prod_path_disabled"
    with observe_pipeline_stage(stage="portfolio", fingerprint_source={"route":"portfolio.snapshot","prod":settings.portfolio_prod_snapshot_enabled}, fallback_reason=fallback_reason) as fingerprint:
        snapshot = request.app.state.portfolio_cache.get_snapshot()
    snapshot.response_metadata = PipelineResponseMeta(version=settings.deterministic_pipeline_response_meta_version, deterministic=True, stage="portfolio", fingerprint=fingerprint, fallback_reason=fallback_reason)
    return snapshot
