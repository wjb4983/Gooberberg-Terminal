from collections import defaultdict, deque

from fastapi import APIRouter, HTTPException, status

from app.graph.mock_provider import get_mock_topology
from app.schemas import GraphNeighborhoodRequest, GraphNeighborhoodResponse, GraphNodeType, GraphTopologyResponse

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/topology", response_model=GraphTopologyResponse)
def get_graph_topology() -> GraphTopologyResponse:
    return get_mock_topology()


@router.post("/neighborhood", response_model=GraphNeighborhoodResponse)
def get_graph_neighborhood(payload: GraphNeighborhoodRequest) -> GraphNeighborhoodResponse:
    topology = get_mock_topology()

    by_id = {node.id: node for node in topology.nodes}
    if payload.seed_node_id not in by_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="seed node not found")

    allowed_types: set[GraphNodeType] | None = set(payload.include_node_types) if payload.include_node_types else None

    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in topology.edges:
        adjacency[edge.source].add(edge.target)
        adjacency[edge.target].add(edge.source)

    visited: set[str] = {payload.seed_node_id}
    distances: dict[str, int] = {payload.seed_node_id: 0}
    queue: deque[str] = deque([payload.seed_node_id])

    while queue:
        node_id = queue.popleft()
        current_depth = distances[node_id]
        if current_depth >= payload.depth:
            continue
        for neighbor in adjacency[node_id]:
            if neighbor in visited:
                continue
            visited.add(neighbor)
            distances[neighbor] = current_depth + 1
            queue.append(neighbor)

    selected_ids = {
        node_id
        for node_id in visited
        if allowed_types is None or by_id[node_id].type in allowed_types or node_id == payload.seed_node_id
    }

    nodes = [by_id[node_id] for node_id in selected_ids]
    edges = [edge for edge in topology.edges if edge.source in selected_ids and edge.target in selected_ids]

    return GraphNeighborhoodResponse(
        seed_node_id=payload.seed_node_id,
        depth=payload.depth,
        nodes=nodes,
        edges=edges,
    )
