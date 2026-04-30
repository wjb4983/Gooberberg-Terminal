from collections import defaultdict, deque
from datetime import datetime, timedelta
from math import cos, pi, sin

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_graph_service
from app.core.config import get_settings
from app.core.pipeline_observability import PipelineResponseMeta, observe_pipeline_stage
from app.domain.graph_domain import Service as GraphService
from app.schemas import (
    GraphLayoutProductsResponse,
    GraphNeighborhoodRequest,
    GraphNeighborhoodResponse,
    GraphNodePosition,
    GraphNodeType,
    GraphTimeSeriesTilesResponse,
    GraphTopologyResponse,
    TimeSeriesPoint,
    TimeSeriesTile,
)

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/topology", response_model=GraphTopologyResponse)
def get_graph_topology(service: GraphService = Depends(get_graph_service)) -> GraphTopologyResponse:
    settings = get_settings()
    fallback_reason = None if settings.graph_prod_topology_enabled else "prod_path_disabled"
    with observe_pipeline_stage(stage="graph", fingerprint_source={"route":"graph.topology","prod":settings.graph_prod_topology_enabled}, fallback_reason=fallback_reason) as fingerprint:
        response = service.get_topology()
    response.response_metadata = PipelineResponseMeta(version=settings.deterministic_pipeline_response_meta_version, deterministic=True, stage="graph", fingerprint=fingerprint, fallback_reason=fallback_reason)
    return response


@router.get("/layout-products", response_model=GraphLayoutProductsResponse)
def get_graph_layout_products(
    zoom: float = Query(0.7, ge=0.1, le=8.0),
    viewport_x: float = Query(0.0),
    viewport_y: float = Query(0.0),
    viewport_width: float = Query(1200.0, gt=0.0),
    viewport_height: float = Query(800.0, gt=0.0),
    service: GraphService = Depends(get_graph_service),
) -> GraphLayoutProductsResponse:
    topology = service.get_topology()
    is_summary = zoom < 1.25
    keep_every = 4 if is_summary else 1

    kept_nodes = [node for idx, node in enumerate(topology.nodes) if idx % keep_every == 0]
    center_x = viewport_x + (viewport_width / 2.0)
    center_y = viewport_y + (viewport_height / 2.0)
    radius = min(viewport_width, viewport_height) * 0.43

    positions: list[GraphNodePosition] = []
    total = max(len(kept_nodes), 1)
    for idx, node in enumerate(kept_nodes):
        theta = (2.0 * pi * idx) / total
        ring_wobble = 1.0 + (0.17 * sin(theta * 3.0))
        positions.append(
            GraphNodePosition(
                node_id=node.id,
                x=center_x + cos(theta) * radius * ring_wobble,
                y=center_y + sin(theta) * radius * ring_wobble,
            )
        )

    return GraphLayoutProductsResponse(
        data_label="summary/downsampled" if is_summary else "detailed window",
        zoom=zoom,
        viewport_x=viewport_x,
        viewport_y=viewport_y,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        nodes=positions,
    )


@router.get("/time-series-tiles", response_model=GraphTimeSeriesTilesResponse)
def get_graph_time_series_tiles(
    window_start: datetime | None = Query(default=None),
    window_end: datetime | None = Query(default=None),
    zoom: float = Query(0.7, ge=0.1, le=8.0),
) -> GraphTimeSeriesTilesResponse:
    now = datetime.utcnow()
    end_at = window_end or now
    start_at = window_start or (end_at - timedelta(hours=12))
    if start_at >= end_at:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="window_start must be before window_end")

    is_summary = zoom < 1.25
    points_per_series = 96 if is_summary else 420
    series_names = ["latency_ms", "edge_throughput", "cache_hit_rate"]

    duration = end_at - start_at
    step_seconds = duration.total_seconds() / max(points_per_series - 1, 1)

    tiles: list[TimeSeriesTile] = []
    for series_idx, series_key in enumerate(series_names):
        points: list[TimeSeriesPoint] = []
        baseline = 60.0 + (series_idx * 12.0)
        amplitude = 16.0 + (series_idx * 7.0)
        for point_idx in range(points_per_series):
            at = start_at + timedelta(seconds=step_seconds * point_idx)
            normalized = point_idx / max(points_per_series - 1, 1)
            wave = sin((2.0 * pi * normalized * (series_idx + 1)) + (0.9 * series_idx))
            value = baseline + (amplitude * wave)
            points.append(TimeSeriesPoint(timestamp=at.isoformat() + "Z", value=round(value, 4)))

        tiles.append(TimeSeriesTile(series_key=series_key, points=points))

    return GraphTimeSeriesTilesResponse(
        data_label="summary/downsampled" if is_summary else "detailed window",
        zoom=zoom,
        window_start=start_at.isoformat() + "Z",
        window_end=end_at.isoformat() + "Z",
        tiles=tiles,
    )


@router.post("/neighborhood", response_model=GraphNeighborhoodResponse)
def get_graph_neighborhood(
    payload: GraphNeighborhoodRequest,
    service: GraphService = Depends(get_graph_service),
) -> GraphNeighborhoodResponse:
    topology = service.get_topology()

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
        for neighbor in sorted(adjacency[node_id]):
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
    sorted_selected_ids = sorted(selected_ids)
    nodes = [by_id[node_id] for node_id in sorted_selected_ids]
    edges = [
        edge
        for edge in topology.edges
        if edge.source in selected_ids and edge.target in selected_ids
    ]
    edges.sort(key=lambda edge: (edge.source, edge.target, edge.label, edge.id))

    return GraphNeighborhoodResponse(seed_node_id=payload.seed_node_id, depth=payload.depth, nodes=nodes, edges=edges)
