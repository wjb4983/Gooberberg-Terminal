from fastapi import APIRouter, Request

from app.schemas import PortfolioSnapshot

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/snapshot", response_model=PortfolioSnapshot)
async def get_portfolio_snapshot(request: Request) -> PortfolioSnapshot:
    return request.app.state.portfolio_cache.get_snapshot()
