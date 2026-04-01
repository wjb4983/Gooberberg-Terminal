from fastapi import APIRouter

from app.graph.mock_provider import get_mock_topology
from app.schemas import GraphTopologyResponse

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/topology", response_model=GraphTopologyResponse)
def get_graph_topology() -> GraphTopologyResponse:
    return get_mock_topology()
