from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, conint


class GraphNodeType(StrEnum):
    STRATEGY = "strategy"
    MODEL = "model"
    DATA_SOURCE = "data_source"
    RISK_RULE = "risk_rule"
    EXECUTION_ADAPTER = "execution_adapter"
    JOB = "job"


class GraphNode(BaseModel):
    id: str
    type: GraphNodeType
    label: str
    group: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str | None = None


class GraphTopologyResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class GraphNeighborhoodRequest(BaseModel):
    seed_node_id: str = Field(min_length=1)
    depth: conint(ge=1, le=6) = 1
    include_node_types: list[GraphNodeType] = Field(default_factory=list)


class GraphNeighborhoodResponse(BaseModel):
    seed_node_id: str
    depth: int
    nodes: list[GraphNode]
    edges: list[GraphEdge]
